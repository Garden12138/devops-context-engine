import json
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from dce.common.errors import DceError, ErrorCode
from dce.common.service_logs import LogControls
from dce.connectors.docker_logs import project_logs, read_logs
from dce.connectors.gitlab import key
from dce.connectors.http import Reader
from dce.security.log_grant import ServiceLogGrant


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
        for service in data:
            spec = service.get("Spec", {})
            if not isinstance(spec, dict) or not isinstance(spec.get("Labels", {}), dict):
                raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected service labels.")
        return [
            service
            for service in data
            if namespace is None
            or service.get("Spec", {}).get("Labels", {}).get("com.docker.stack.namespace")
            == namespace
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

    async def service_logs(
        self,
        endpoint: str,
        stack_id: str,
        *,
        service_id: str | None,
        service_name: str | None,
        controls: LogControls,
        grant: ServiceLogGrant | None = None,
    ) -> dict[str, Any]:
        controls.bounds()
        if bool(service_id) == bool(service_name):
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Exactly one service selector is required.")
        if grant is not None:
            grant.authorize(
                self.reader.config.instance_id,
                endpoint,
                stack_id,
                service_id=service_id,
                service_name=service_name,
                controls=controls,
            )
        stack = self.stack(stack_id)
        if (
            str(stack.get("Id")) != stack_id
            or str(stack.get("EndpointId")) != endpoint
            or stack.get("Type") != 1
        ):
            raise DceError(ErrorCode.PERMISSION_DENIED, "Stack identity or endpoint mismatch.")
        swarm = self.docker_info(endpoint)["Swarm"]
        cluster = swarm.get("Cluster")
        if (
            not isinstance(cluster, dict)
            or not cluster.get("ID")
            or cluster["ID"] != stack.get("SwarmId")
            or not isinstance(cluster["ID"], str)
            or not re.fullmatch(r"[a-z0-9]{1,64}", cluster["ID"])
        ):
            raise DceError(ErrorCode.SNAPSHOT_CONFLICT, "Stack does not match the current Swarm.")
        namespace = stack.get("Namespace") or stack.get("Name")
        if not isinstance(namespace, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,199}", namespace
        ):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Stack namespace is unavailable.")
        if service_name is not None:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,199}", service_name):
                raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid Compose service key.")
            exact_name = namespace + "_" + service_name
            candidates = self.reader.json(
                f"/api/endpoints/{key(endpoint)}/docker/services",
                kind="portainer",
                expected=list,
                params={
                    "filters": json.dumps(
                        {"name": [exact_name], "label": [f"com.docker.stack.namespace={namespace}"]}
                    )
                },
            )
            selected = [
                s
                for s in candidates
                if isinstance(s.get("Spec"), dict) and s["Spec"].get("Name") == exact_name
            ]
            if len(selected) != 1:
                raise DceError(ErrorCode.NOT_FOUND, "Service selector is absent or ambiguous.")
            service_id = selected[0].get("ID")
        if not isinstance(service_id, str) or not re.fullmatch(r"[a-z0-9]{1,64}", service_id):
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Full Docker service ID is required.")
        if grant is not None and service_id != grant.spec.service_id:
            raise DceError(
                ErrorCode.PERMISSION_DENIED, "Resolved service is outside temporary grant."
            )
        service = self.service(endpoint, service_id)
        spec = service.get("Spec")
        if not isinstance(spec, dict) or not isinstance(spec.get("Labels"), dict):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Service scope labels are unavailable.")
        name = spec.get("Name")
        if (
            service.get("ID") != service_id
            or spec["Labels"].get("com.docker.stack.namespace") != namespace
            or not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,399}", name)
            or not name.startswith(namespace + "_")
            or (service_name is not None and name != namespace + "_" + service_name)
        ):
            raise DceError(ErrorCode.PERMISSION_DENIED, "Service is outside the requested Stack.")
        version_info = service.get("Version")
        if (
            not isinstance(version_info, dict)
            or type(version_info.get("Index")) is not int
            or version_info["Index"] < 0
        ):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Service version is unavailable.")
        task = spec.get("TaskTemplate")
        if not isinstance(task, dict) or not isinstance(task.get("ContainerSpec"), dict):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Container service metadata is required.")
        tty = task["ContainerSpec"].get("TTY", False)
        if not isinstance(tty, bool):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Invalid service TTY metadata.")
        driver = task.get("LogDriver") or {}
        if not isinstance(driver, dict):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Invalid log driver metadata.")
        if driver.get("Name") not in (None, "", "json-file", "journald"):
            raise DceError(ErrorCode.LOG_DRIVER_UNSUPPORTED, "Service log driver is unsupported.")
        version = self.reader.json(
            f"/api/endpoints/{key(endpoint)}/docker/version", kind="portainer"
        )
        api = version.get("ApiVersion", "")
        if not isinstance(api, str) or not re.fullmatch(r"1\.\d{1,3}", api) or int(api[2:]) < 30:
            raise DceError(
                ErrorCode.LOG_FILTER_UNSUPPORTED, "Service logs require Docker API 1.30+."
            )
        if grant is not None:
            grant.verify_identity(stack.get("Name"), namespace, cluster["ID"], service_id, name)
            grant.consume(controls)
        start, _ = controls.bounds()
        # Integer Docker filtering must not widen a temporary grant by rounding down.
        since = (start + 999_999_999) // 1_000_000_000 if grant else start // 1_000_000_000
        raw = await read_logs(
            self.reader,
            f"/api/endpoints/{key(endpoint)}/docker/v{api}/services/{key(service_id)}/logs",
            {
                "since": str(since),
                "tail": str(controls.max_lines),
                "follow": "false",
                "stdout": "true",
                "stderr": "true",
                "timestamps": "true",
                "details": "true",
            },
            controls,
        )
        record = project_logs(raw, controls, tty=tty, service_id=service_id)
        # A concurrent update invalidates the pinned service identity/version, not just its name.
        current = self.service(endpoint, service_id)
        if (
            current.get("ID") != service_id
            or current.get("Version") != service.get("Version")
            or current.get("Spec") != spec
        ):
            raise DceError(ErrorCode.SNAPSHOT_CONFLICT, "Service changed during log retrieval.")
        record["identity"] = {
            "endpoint_id": endpoint,
            "stack_id": stack_id,
            "service_id": service_id,
            "service_name": name,
            "namespace": namespace,
            "swarm_id": cluster["ID"],
            "service_version": {"Index": version_info["Index"]},
        }
        return record
