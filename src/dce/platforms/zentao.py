from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pydantic import SecretStr

from dce.errors import DceError, ErrorCode
from dce.platforms.gitlab import key
from dce.platforms.http import PlatformClient


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
                ErrorCode.PLATFORM_ERROR, "Attachment is not a supported verified image."
            )
        return content, mime
