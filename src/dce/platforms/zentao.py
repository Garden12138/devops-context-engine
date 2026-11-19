from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pydantic import SecretStr

from dce.errors import DceError, ErrorCode
from dce.platforms.gitlab import key
from dce.platforms.http import PlatformClient
from dce.redact import redact


class ZenTao:
    prefix = "/api.php/v1"

    def __init__(self, reader: PlatformClient) -> None:
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
            raise DceError(ErrorCode.PLATFORM_ERROR, "Bug ID is missing.")
        return dict(data)

    def resolve(self, bug_id: int, body: dict[str, Any]) -> None:
        path = f"{self.prefix}/bugs/{bug_id}/resolve"
        response = self.reader.post(path, json=body, kind="zentao", defer_status=True)
        status = response.status_code
        if 400 <= status < 500:
            detail = response.text.strip()
            try:
                data = response.json()
            except ValueError:
                data = None
            if isinstance(data, dict):
                detail = str(data.get("message") or data.get("error") or detail)
            detail = redact(detail, self.reader.secrets())[:500] or "上游未提供错误文字"
            raise DceError(
                ErrorCode.PLATFORM_ERROR, f"禅道缺陷 {bug_id} resolve HTTP {status}: {detail}",
                "检查 zentao.resolve.assign_to 和 zentao.resolve.resolved_build，"
                "以及当前凭证对此缺陷的解决权限。",
            )
        if status >= 500:
            raise DceError(
                ErrorCode.PLATFORM_ERROR, f"禅道缺陷 {bug_id} resolve HTTP {status}: 服务端错误。",
                "核对禅道服务日志和缺陷当前状态，再决定是否重试。",
            )

    def bugs_page(self, product: int, page: int, limit: int = 100) -> list[dict[str, Any]]:
        data = self.reader.json(f"{self.prefix}/products/{product}/bugs", kind="zentao",
                                params={"page": page, "limit": limit})
        bugs = data.get("bugs")
        if not isinstance(bugs, list) or any(not isinstance(b, dict) for b in bugs):
            raise DceError(ErrorCode.PLATFORM_ERROR,
                           f"禅道产品 {product} 缺陷列表 HTTP 200: bugs 应为列表。",
                           "检查该实例 v1 缺陷列表响应格式。")
        return bugs

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
            raise DceError(ErrorCode.OUT_OF_SCOPE, "Invalid attachment URL.") from None
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
                ErrorCode.PLATFORM_ERROR,
                f"ZenTao attachment {url} HTTP {response.status_code}: "
                f"MIME {mime!r} or signature is not a supported verified image.",
                "Check the attachment MIME and image file header in ZenTao.",
            )
        return content, mime
