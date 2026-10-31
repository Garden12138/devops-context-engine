from collections.abc import Callable
from functools import partial
from typing import Any

import httpx
from pydantic import SecretStr

from dce.common.config import PlatformConfig, Settings
from dce.common.errors import DceError
from dce.connectors.gitlab import GitLab
from dce.connectors.http import Reader
from dce.connectors.portainer import Portainer
from dce.connectors.zentao import ZenTao


def doctor(
    settings: Settings,
    *,
    mock: bool = False,
    transports: dict[str, httpx.BaseTransport] | None = None,
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for name in ("zentao", "gitlab", "portainer"):
        try:
            config = (
                PlatformConfig(
                    instance_id=f"{name}-demo",
                    base_url=f"https://{name}.example.invalid",
                    token=SecretStr("mock-only"),
                )
                if mock
                else settings.platform(name)
            )
            transport = httpx.MockTransport(_mock_probe) if mock else (transports or {}).get(name)
            with Reader(config, settings, transport=transport) as reader:
                probes: dict[str, Callable[[], object]]
                if name == "zentao":
                    adapter = ZenTao(reader)
                    probes = {
                        "projects_v1": partial(list, adapter.resources("projects")),
                        "products_v1": partial(list, adapter.resources("products")),
                    }
                elif name == "gitlab":
                    gitlab = GitLab(reader)
                    probes = {"projects_v4": partial(list, gitlab.projects())}
                else:
                    portainer = Portainer(reader)
                    probes = {"stacks": portainer.stacks, "endpoints": portainer.endpoints}
                capabilities: dict[str, Any] = {}
                for capability, probe in probes.items():
                    try:
                        probe()
                        capabilities[capability] = {"status": "ok", "read_only": True}
                    except DceError as exc:
                        capabilities[capability] = {"status": "error", **exc.as_dict()}
                ok = all(c["status"] == "ok" for c in capabilities.values())
                results[name] = {
                    "status": "ok" if ok else "partial",
                    "read_only": True,
                    "verification": "mock" if mock else "live",
                    "capabilities": capabilities,
                    "live_status": "not_verified" if mock else "probed_read_only",
                }
        except DceError as exc:
            results[name] = {"status": "error", "live_status": "not_verified", **exc.as_dict()}
    return {"mode": "offline-fixture" if mock else "local-readonly", "platforms": results}


def _mock_probe(request: httpx.Request) -> httpx.Response:
    if request.url.path.startswith("/api.php/v1/"):
        kind = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, json={kind: []})
    return httpx.Response(200, json=[], headers={"X-Next-Page": ""})
