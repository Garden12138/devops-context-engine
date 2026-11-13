import json
import logging
import time
from collections.abc import Callable, Iterator
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx
from pydantic import SecretStr

from dce.common.config import PlatformConfig, Settings
from dce.common.errors import DceError, ErrorCode
from dce.connectors.zentao_auth import auth_expired, response_error
from dce.security.redact import RedactingFilter

AUTH_HEADERS = {"zentao": "Token", "gitlab": "PRIVATE-TOKEN", "portainer": "X-API-Key"}


class Reader:
    def __init__(
        self,
        config: PlatformConfig,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_bytes: int = 2_000_000,
    ) -> None:
        if config.base_url.startswith("http:") and not settings.allow_http:
            raise DceError(ErrorCode.UNSAFE_URL, "HTTP requires explicit allow_http.")
        self.config = config
        self.settings = settings
        self.max_bytes = max_bytes
        self.transport = transport
        self.sleep = sleep
        self.client = httpx.Client(
            transport=transport, timeout=settings.timeout, follow_redirects=False, trust_env=False
        )
        self.log_filter = RedactingFilter(
            (config.token.get_secret_value(), urlsplit(config.base_url).hostname or "")
        )
        self.loggers = [
            logging.getLogger("httpx"),
            *(
                logging.getLogger(name)
                for name in ("httpcore.connection", "httpcore.http11", "httpcore.http2")
            ),
        ]
        for logger in self.loggers:
            logger.addFilter(self.log_filter)

    def __enter__(self) -> "Reader":
        return self

    def __exit__(self, *_: object) -> None:
        self.client.close()
        for logger in self.loggers:
            logger.removeFilter(self.log_filter)

    def safe_url(self, path: str) -> str:
        # urljoin permits scheme-relative URLs; compare the full origin afterwards.
        try:
            route = (
                path.lstrip("/")
                if not urlsplit(path).scheme and not path.startswith("//")
                else path
            )
            url = urljoin(self.config.base_url + "/", route)
            parsed, base = urlsplit(url), urlsplit(self.config.base_url)
            if (
                (parsed.scheme, parsed.hostname, parsed.port)
                != (base.scheme, base.hostname, base.port)
                or parsed.username
                or parsed.password
                or parsed.fragment
            ):
                raise ValueError
        except ValueError:
            raise DceError(ErrorCode.UNSAFE_URL, "URL is outside configured origin.") from None
        return url

    def get(
        self, path: str, *, kind: str = "gitlab", params: dict[str, Any] | None = None
    ) -> httpx.Response:
        if kind != "zentao":
            return self._request("GET", path, kind=kind, params=params)
        # A refused URL must not trigger lazy authentication either.
        self.safe_url(path)
        self.log_filter.opaque = True
        manager = self.settings._zentao_tokens
        if manager is not None:
            manager.require_connection(self.config)
        lease = manager.lease() if manager else None
        token = lease.token if lease else self.config.token
        self.log_filter.secrets += self.settings.secrets() + (token.get_secret_value(),)
        response = self._request(
            "GET",
            path,
            kind=kind,
            params=params,
            token=token,
            defer_status=True,
        )
        if auth_expired(response) and manager is not None and lease is not None:
            fresh = manager.lease(failed_generation=lease.generation)
            self.log_filter.secrets += self.settings.secrets() + (fresh.token.get_secret_value(),)
            response = self._request(
                "GET",
                path,
                kind=kind,
                params=params,
                token=fresh.token,
                defer_status=True,
            )
            if auth_expired(response):
                manager.reject(fresh.generation)
        error = response_error(response)
        if error is not None:
            raise error
        return response

    def secrets(self) -> tuple[str, ...]:
        return self.log_filter.secrets + self.settings.secrets()

    def zentao_token(self, username: str, password: str) -> httpx.Response:
        # Only authentication POST exists; no arbitrary method/path surface.
        self.log_filter.opaque = True
        response = self._request(
            "POST",
            "/api.php/v1/tokens",
            kind="zentao",
            body={"account": username, "password": password},
            defer_status=True,
        )
        if response.status_code >= 400:
            raise DceError(ErrorCode.AUTH_FAILED, "AUTH_FAILED: ZenTao login rejected.")
        return response

    def _request(
        self,
        method: str,
        path: str,
        *,
        kind: str,
        params: dict[str, Any] | None = None,
        body: dict[str, str] | None = None,
        token: SecretStr | None = None,
        defer_status: bool = False,
    ) -> httpx.Response:
        if method != "GET" and not (
            method == "POST" and kind == "zentao" and path == "/api.php/v1/tokens"
        ):
            raise DceError(ErrorCode.PERMISSION_DENIED, "Platform mutation is forbidden.")
        url = self.safe_url(path)
        headers = (
            {AUTH_HEADERS[kind]: (token or self.config.token).get_secret_value()}
            if method == "GET"
            else {}
        )
        retry_count = self.settings.max_retries if method == "GET" else 0
        for attempt in range(retry_count + 1):
            self.sleep(self.settings.request_interval)
            try:
                if kind == "zentao":
                    # v1 uses the explicit Token header; stale PHP cookies must not win.
                    self.client.cookies.clear()
                with self.client.stream(
                    method, url, params=params, headers=headers, json=body
                ) as response:
                    status = response.status_code
                    if status in {429, 502, 503, 504} and attempt < retry_count:
                        try:
                            delay = min(max(float(response.headers.get("Retry-After", "0")), 0), 5)
                        except ValueError:
                            delay = 0
                        self.sleep(max(delay, min(0.1 * 2**attempt, 2)))
                        continue
                    if 300 <= status < 400:
                        raise DceError(ErrorCode.UNSAFE_URL, "Redirect responses are forbidden.")
                    if status >= 400 and not defer_status:
                        code = {
                            401: ErrorCode.AUTH_FAILED,
                            403: ErrorCode.PERMISSION_DENIED,
                            404: ErrorCode.NOT_FOUND,
                            429: ErrorCode.RATE_LIMITED,
                        }.get(status, ErrorCode.API_INCOMPATIBLE)
                        raise DceError(
                            code,
                            "Platform request failed.",
                            retryable=status in {429, 502, 503, 504},
                        )
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        cap = min(self.max_bytes, 16384) if status >= 400 else self.max_bytes
                        if len(content) > cap:
                            if defer_status and status >= 400:
                                # Preserve the HTTP error class; never infer expiry from
                                # incomplete JSON or consume an unbounded error response.
                                content.clear()
                                break
                            raise DceError(
                                ErrorCode.INVALID_PAYLOAD, "Response size limit exceeded."
                            )
                    # iter_bytes() has decoded content/transfer encodings already.
                    # A buffered Response must not apply them again or reuse wire length.
                    buffered_headers = httpx.Headers(response.headers)
                    for name in ("Content-Encoding", "Content-Length", "Transfer-Encoding"):
                        buffered_headers.pop(name, None)
                    return httpx.Response(
                        status,
                        headers=buffered_headers,
                        content=bytes(content),
                        request=response.request,
                    )
            except httpx.DecodingError:
                raise DceError(
                    ErrorCode.INVALID_PAYLOAD, "Platform returned invalid content encoding."
                ) from None
            except httpx.RequestError:
                if attempt == retry_count:
                    raise DceError(
                        ErrorCode.NETWORK_UNAVAILABLE, "Platform connection failed.", retryable=True
                    ) from None
                self.sleep(min(0.1 * 2**attempt, 2))
        raise AssertionError("unreachable")

    def json(
        self,
        path: str,
        *,
        kind: str = "gitlab",
        expected: type = dict,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self.decode(self.get(path, kind=kind, params=params), expected)

    @staticmethod
    def decode(response: httpx.Response, expected: type) -> Any:
        try:
            data: Any = response.json()
        except (ValueError, json.JSONDecodeError):
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Platform returned invalid JSON.") from None
        if not isinstance(data, expected):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected platform response shape.")
        if (
            expected is list
            and isinstance(data, list)
            and not all(isinstance(item, dict) for item in data)
        ):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Expected resource objects.")
        return data

    def pages(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        start_page: int = 1,
        max_pages: int = 1000,
    ) -> Iterator[dict[str, Any]]:
        page = start_page
        for _ in range(max_pages):
            response = self.get(
                path, params={**(params or {}), "page": page, "per_page": self.settings.page_size}
            )
            data = self.decode(response, list)
            yield from data
            next_page = response.headers.get("X-Next-Page")
            if next_page == "" or (next_page is None and len(data) < self.settings.page_size):
                return
            try:
                following = int(next_page) if next_page is not None else page + 1
                if following <= page:
                    raise ValueError
            except ValueError:
                raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid pagination cursor.") from None
            page = following
            self.sleep(0.01)
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Pagination limit exceeded; narrow scan scope.")
