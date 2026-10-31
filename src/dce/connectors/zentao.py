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

    def resources(
        self, kind: str, parent: str | None = None, *, max_pages: int = 1000
    ) -> Iterator[dict[str, Any]]:
        if kind not in {"projects", "products", "bugs"}:
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Unsupported ZenTao resource.")
        path = f"{self.prefix}/{kind}"
        if parent is not None:
            path = f"{self.prefix}/projects/{key(parent)}/{kind}"
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

    def download_image(self, source: str, cache: Path) -> dict[str, str]:
        response = self.reader.get(
            urljoin(self.reader.config.base_url + "/", source), kind="zentao"
        )
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
        digest = hashlib.sha256(content).hexdigest()
        asset_id = hashlib.sha256(f"{self.reader.config.instance_id}:{source}".encode()).hexdigest()
        cache.mkdir(mode=0o700, parents=True, exist_ok=True)
        if cache.is_symlink():
            raise DceError(ErrorCode.PERMISSION_DENIED, "Asset cache must be a private directory.")
        cache.chmod(0o700)
        path = cache / f"{asset_id}-{digest}{signatures[mime][1]}"
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
