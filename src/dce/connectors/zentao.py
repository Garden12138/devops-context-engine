import hashlib
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pydantic import SecretStr

from dce.common.errors import DceError, ErrorCode
from dce.connectors.gitlab import key
from dce.connectors.http import Reader


class ZenTao:
    prefix = "/api.php/v1"

    def __init__(self, reader: Reader) -> None:
        self.reader = reader

    def create_token(self, account: str, password: SecretStr) -> SecretStr:
        data = self.reader.decode(
            self.reader.zentao_token(account, password.get_secret_value()), dict
        )
        if not isinstance(data.get("token"), str) or not data["token"].strip():
            raise DceError(ErrorCode.AUTH_FAILED, "ZenTao did not return an authentication token.")
        return SecretStr(data["token"])

    def bug(self, bug: str) -> dict[str, Any]:
        data = self.reader.json(f"{self.prefix}/bugs/{key(bug)}", kind="zentao")
        if "id" not in data:
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Bug ID is missing.")
        return dict(data)

    def resource(self, kind: str, resource_id: str) -> dict[str, Any]:
        if kind not in {"projects", "products"}:
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Unsupported ZenTao resource.")
        data = self.reader.json(f"{self.prefix}/{kind}/{key(resource_id)}", kind="zentao")
        if "id" not in data:
            raise DceError(ErrorCode.API_INCOMPATIBLE, "ZenTao resource ID is missing.")
        return dict(data)

    def resources(
        self,
        kind: str,
        parent: str | None = None,
        *,
        max_pages: int = 1000,
        parent_kind: str = "projects",
    ) -> Iterator[dict[str, Any]]:
        if kind not in {"projects", "products", "bugs"}:
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Unsupported ZenTao resource.")
        path = f"{self.prefix}/{kind}"
        if parent is not None:
            if parent_kind not in {"projects", "products"}:
                raise DceError(ErrorCode.INVALID_PAYLOAD, "Unsupported ZenTao parent scope.")
            path = f"{self.prefix}/{parent_kind}/{key(parent)}/{kind}"
        for page in range(1, max_pages + 1):
            data = self.reader.json(
                path, kind="zentao", params={"page": page, "limit": self.reader.settings.page_size}
            )
            items = data.get(kind)
            if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
                raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected ZenTao collection.")
            yield from items
            if len(items) < self.reader.settings.page_size:
                return
            self.reader.sleep(0.01)
        raise DceError(ErrorCode.INVALID_PAYLOAD, "ZenTao pagination limit exceeded.")

    def modules(self, product: str, module_type: str = "bug") -> list[dict[str, Any]]:
        """v1 /modules: product-rooted tree, verified from official routes/entry source.

        No task root is accepted: an Execution ID must never be inferred from a Project ID.
        """
        if module_type not in {"bug", "story", "case", "product"}:
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Unsupported product module type.")
        data = self.reader.json(
            f"{self.prefix}/modules", kind="zentao", params={"id": product, "type": module_type}
        )
        tree = data.get("modules")
        if not isinstance(tree, list):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Expected a ZenTao module tree.")
        if len(tree) > 10000:
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Module tree traversal limit exceeded.")
        pending: list[tuple[Any, str | None, int]] = [(node, None, 0) for node in reversed(tree)]
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        fields = {
            "id",
            "name",
            "short",
            "root",
            "type",
            "parent",
            "branch",
            "grade",
            "path",
            "order",
        }
        while pending:
            node, parent, depth = pending.pop()
            if depth > 30 or len(records) + len(pending) >= 10000:
                raise DceError(ErrorCode.INVALID_PAYLOAD, "Module tree traversal limit exceeded.")
            if not isinstance(node, dict):
                raise DceError(ErrorCode.API_INCOMPATIBLE, "Expected module objects.")
            identifier = node.get("id")
            if (
                not isinstance(identifier, (str, int))
                or isinstance(identifier, bool)
                or not str(identifier)
                or not isinstance(node.get("name"), str)
            ):
                raise DceError(ErrorCode.API_INCOMPATIBLE, "Module identity is missing.")
            identity = str(identifier)
            if identity in seen:
                raise DceError(ErrorCode.SNAPSHOT_CONFLICT, "Module identity is duplicated.")
            if "root" in node and str(node["root"]) != product:
                raise DceError(ErrorCode.SNAPSHOT_CONFLICT, "Module belongs to a different root.")
            seen.add(identity)
            children = node.get("children", [])
            if not isinstance(children, list):
                raise DceError(ErrorCode.API_INCOMPATIBLE, "Expected module children objects.")
            record = {k: v for k, v in node.items() if k in fields}
            if any(not isinstance(v, (str, int, float, type(None))) for v in record.values()):
                raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected module metadata.")
            records.append({**record, "tree_parent_id": parent})
            if len(records) + len(pending) + len(children) > 10000:
                raise DceError(ErrorCode.INVALID_PAYLOAD, "Module tree traversal limit exceeded.")
            pending.extend((child, identity, depth + 1) for child in reversed(children))
        return records

    @staticmethod
    def parse_steps(bug: dict[str, Any]) -> tuple[str, list[str]]:
        soup = BeautifulSoup(str(bug.get("steps", bug.get("steps_html", ""))), "html.parser")
        for tag in soup(["script", "style", "iframe", "object"]):
            tag.decompose()
        sources = [str(img["src"]) for img in soup.find_all("img", src=True)]
        files = bug.get("files") or []
        if isinstance(files, dict):
            files = list(files.values())
        for entry in files:
            if isinstance(entry, dict) and isinstance(entry.get("url"), str):
                sources.append(entry["url"])
        return soup.get_text(" ", strip=True), list(dict.fromkeys(sources))

    def image_content(self, source: str) -> tuple[bytes, str]:
        try:
            url = urljoin(self.reader.config.base_url + "/", source)
        except ValueError:
            raise DceError(ErrorCode.UNSAFE_URL, "Invalid attachment URL.") from None
        response = self.reader.get(url, kind="zentao")
        mime = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        content = response.content
        signatures = {
            "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
            "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
            "image/gif": (b"GIF8", ".gif"),
        }
        if mime not in signatures or not content.startswith(signatures[mime][0]):
            raise DceError(
                ErrorCode.INVALID_PAYLOAD, "Attachment is not a supported verified image."
            )
        return content, mime

    def download_image(self, source: str, cache: Path) -> dict[str, str]:
        content, mime = self.image_content(source)
        extensions = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif"}
        digest = hashlib.sha256(content).hexdigest()
        asset_id = hashlib.sha256(f"{self.reader.config.instance_id}:{source}".encode()).hexdigest()
        cache.mkdir(mode=0o700, parents=True, exist_ok=True)
        if cache.is_symlink():
            raise DceError(ErrorCode.PERMISSION_DENIED, "Asset cache must be a private directory.")
        cache.chmod(0o700)
        path = cache / f"{asset_id}-{digest}{extensions[mime]}"
        descriptor, temporary = tempfile.mkstemp(dir=cache)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return {
            "asset_id": asset_id,
            "mime": mime,
            "sha256": digest,
            "local_path": str(path.resolve()),
        }
