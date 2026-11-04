from typing import Any
from urllib.parse import urlsplit, urlunsplit

from dce.common.errors import DceError, ErrorCode
from dce.connectors.gitlab import key
from dce.connectors.http import Reader


def safe_stack(stack: dict[str, Any]) -> dict[str, Any]:
    # No raw auth/URL payload is retained; repository identity is verified separately.
    result = {
        name: stack[name]
        for name in ("Id", "Name", "Type", "EndpointId", "SwarmId", "Status", "Namespace")
        if name in stack
    }
    git = stack.get("GitConfig") or {}
    if not isinstance(git, dict):
        raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected GitConfig structure.")
    result["GitConfig"] = {
        name: git[name] for name in ("ReferenceName", "ConfigHash", "ConfigFilePath") if name in git
    }
    if isinstance(git.get("URL"), str):
        try:
            url = urlsplit(git["URL"])
            if url.scheme in {"https", "http"} and url.hostname:
                result["GitConfig"]["URL"] = urlunsplit(
                    (url.scheme, url.netloc.rsplit("@", 1)[-1], url.path, "", "")
                )
        except ValueError:
            pass  # Unsupported repository address remains unresolved.
    return result


class Portainer:
    def __init__(self, reader: Reader) -> None:
        self.reader = reader

    def stacks(self) -> list[dict[str, Any]]:
        return [
            safe_stack(s) for s in self.reader.json("/api/stacks", kind="portainer", expected=list)
        ]

    def stack(self, stack: str) -> dict[str, Any]:
        return safe_stack(self.reader.json(f"/api/stacks/{key(stack)}", kind="portainer"))

    def stack_file(self, stack: str, endpoint: str) -> str:
        data = self.reader.json(
            f"/api/stacks/{key(stack)}/file", kind="portainer", params={"endpointId": endpoint}
        )
        if not isinstance(data.get("StackFileContent"), str):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "StackFileContent is missing.")
        return str(data["StackFileContent"])

    def endpoints(self) -> list[dict[str, Any]]:
        data = self.reader.json("/api/endpoints", kind="portainer", expected=list)
        return [
            {k: item[k] for k in ("Id", "Name", "Type", "Status") if k in item} for item in data
        ]

    def docker_info(self, endpoint: str) -> dict[str, Any]:
        data = self.reader.json(f"/api/endpoints/{key(endpoint)}/docker/info", kind="portainer")
        if not isinstance(data.get("Swarm"), dict):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Docker Swarm info is missing.")
        return {"Swarm": data["Swarm"]}

    def services(self, endpoint: str, namespace: str | None = None) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = self.reader.json(
            f"/api/endpoints/{key(endpoint)}/docker/services", kind="portainer", expected=list
        )
        return [
            s
            for s in data
            if namespace is None
            or s.get("Spec", {}).get("Labels", {}).get("com.docker.stack.namespace") == namespace
        ]

    def endpoint(self, endpoint: str) -> dict[str, Any]:
        return {
            k: v
            for k, v in self.reader.json(
                f"/api/endpoints/{key(endpoint)}", kind="portainer"
            ).items()
            if k in {"Id", "Name", "Type", "Status"}
        }

    def service(self, endpoint: str, service: str) -> dict[str, Any]:
        return dict(
            self.reader.json(
                f"/api/endpoints/{key(endpoint)}/docker/services/{key(service)}", kind="portainer"
            )
        )
