"""Explicit, temporary initialization discovery. No workspace scanning or platform writes."""

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from dce.app.facts import FactScope, select
from dce.app.services import AppServices, external_id, resource_key
from dce.common.errors import DceError, ErrorCode
from dce.connectors.gitlab import GitLab
from dce.connectors.portainer import Portainer
from dce.connectors.zentao import ZenTao
from dce.graph.model import fingerprint
from dce.project.context import reject_secrets
from dce.project.model import Scope
from dce.security.redact import redact


class DiscoverySeeds(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    gitlab_paths: list[str] = Field(default_factory=list, max_length=20)
    zentao_bug: str | None = Field(default=None, min_length=1, max_length=250)
    zentao_search: str = Field(default="", max_length=100)
    portainer_search: str = Field(default="", max_length=100)
    deployment_repositories: list[str] = Field(default_factory=list, max_length=20)


def scope_from_project(scope: Scope) -> FactScope:
    return FactScope(
        gitlab_projects=set(scope.gitlab.projects if scope.gitlab else []),
        zentao_projects=set(scope.zentao.projects if scope.zentao else []),
        zentao_products=set(scope.zentao.products if scope.zentao else []),
        zentao_bugs=set(scope.zentao.bugs if scope.zentao else []),
        portainer_endpoints=set(scope.portainer.endpoints if scope.portainer else []),
        portainer_stacks=set(scope.portainer.stacks if scope.portainer else []),
        project_mode=True,
    )


def check_instances(scope: Scope, services: AppServices) -> None:
    for name in ("zentao", "gitlab", "portainer"):
        item = getattr(scope, name)
        config = getattr(services.settings, name)
        if item is not None and (config is None or item.instance != config.instance_id):
            raise DceError(
                ErrorCode.PERMISSION_DENIED, "Project source instance does not match configuration."
            )
    if scope.zentao and not (scope.zentao.projects or scope.zentao.products):
        raise DceError(
            ErrorCode.INVALID_PAYLOAD, "Project mode needs a ZenTao Project or Product scope."
        )


def subset(proposed: FactScope, allowed: FactScope) -> bool:
    return all(
        getattr(proposed, key) <= getattr(allowed, key)
        for key in (
            "gitlab_projects",
            "zentao_projects",
            "zentao_products",
            "zentao_bugs",
            "portainer_endpoints",
            "portainer_stacks",
        )
    )


def repository(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Expected a credential-free repository URL.")
    return parsed.hostname.casefold() + parsed.path.removesuffix(".git").rstrip("/")


class ProjectDiscovery:
    def __init__(self, services: AppServices) -> None:
        self.services = services
        self.scope = FactScope(project_mode=True)
        self.records: list[dict[str, Any]] = []
        self.failures: list[dict[str, str]] = []
        self.observed = datetime.now(UTC).isoformat()

    def remember(self, platform: str, kind: str, data: dict[str, Any]) -> None:
        for name, value in data.items():
            values = value.values() if name == "GitConfig" and isinstance(value, dict) else [value]
            if any(not isinstance(item, (str, int, float, bool, type(None))) for item in values):
                raise DceError(
                    ErrorCode.API_INCOMPATIBLE, "Unexpected initialization metadata shape."
                )
        safe = redact(data, self.services.settings.secrets())
        self.records.append(
            {
                "platform": platform,
                "kind": kind,
                "record": safe,
                "observed_at": self.observed,
                "revision": fingerprint(safe),
                "status": "candidate",
                "untrusted_data": True,
            }
        )

    def run(self, seeds: DiscoverySeeds) -> None:
        reject_secrets(seeds.model_dump())
        for path in seeds.gitlab_paths:
            resource_key(path)
        repos = {repository(r) for r in seeds.deployment_repositories}
        for platform in ("gitlab", "zentao", "portainer"):
            try:
                if platform == "gitlab" and seeds.gitlab_paths:
                    with self.services.reader(platform) as reader:
                        for path in seeds.gitlab_paths:
                            record = GitLab(reader).project(path)
                            if (
                                record.get("path_with_namespace") != path
                                or external_id(record.get("id")) is None
                            ):
                                raise DceError(
                                    ErrorCode.API_INCOMPATIBLE,
                                    "Git remote project identity mismatch.",
                                )
                            self.scope.gitlab_projects.add(str(record["id"]))
                            self.remember(
                                platform,
                                "project",
                                select(record, "id name path_with_namespace default_branch"),
                            )
                elif platform == "zentao" and (seeds.zentao_bug or seeds.zentao_search.strip()):
                    with self.services.reader(platform) as reader:
                        adapter = ZenTao(reader)
                        if seeds.zentao_bug:
                            resource_key(seeds.zentao_bug)
                            bug = adapter.bug(seeds.zentao_bug)
                            if str(bug["id"]) != seeds.zentao_bug:
                                raise DceError(ErrorCode.API_INCOMPATIBLE, "Bug identity mismatch.")
                            # Seed permits this one lookup; no body/images leave discovery.
                            self.scope.zentao_bugs.add(seeds.zentao_bug)
                            for field, target in (
                                ("project", self.scope.zentao_projects),
                                ("product", self.scope.zentao_products),
                            ):
                                value = external_id(bug.get(field + "_id", bug.get(field)))
                                if value is not None:
                                    resource_key(str(value))
                                    target.add(str(value))
                            self.remember(
                                platform,
                                "bug_seed",
                                {
                                    "id": bug["id"],
                                    **{
                                        k: external_id(bug.get(k + "_id", bug.get(k)))
                                        for k in ("project", "product", "module")
                                    },
                                },
                            )
                        if seeds.zentao_search.strip():
                            for kind in ("projects", "products"):
                                for page in range(1, 4):
                                    raw = reader.json(
                                        f"{adapter.prefix}/{kind}",
                                        kind="zentao",
                                        params={"page": page, "limit": 20},
                                    )
                                    items = raw.get(kind)
                                    if not isinstance(items, list) or not all(
                                        isinstance(r, dict) for r in items
                                    ):
                                        raise DceError(
                                            ErrorCode.API_INCOMPATIBLE,
                                            "Invalid discovery directory.",
                                        )
                                    for record in items[:20]:
                                        if (
                                            seeds.zentao_search.casefold()
                                            in str(record.get("name", "")).casefold()
                                        ):
                                            identity = external_id(record.get("id"))
                                            if identity is not None:
                                                resource_key(str(identity))
                                                getattr(self.scope, "zentao_" + kind).add(
                                                    str(identity)
                                                )
                                                self.remember(
                                                    platform,
                                                    kind[:-1],
                                                    select(record, "id name code"),
                                                )
                                    if len(items) < 20:
                                        break
                                    if page == 3:
                                        self.failures.append(
                                            {"platform": platform, "code": "DISCOVERY_PAGE_LIMIT"}
                                        )
                elif platform == "portainer" and (seeds.portainer_search.strip() or repos):
                    with self.services.reader(platform) as reader:
                        for stack in Portainer(reader).stacks():
                            url = stack.get("GitConfig", {}).get("URL")
                            matched = False
                            if isinstance(url, str):
                                try:
                                    matched = repository(url) in repos
                                except DceError:
                                    pass
                            if (
                                matched
                                or seeds.portainer_search.strip()
                                and seeds.portainer_search.casefold()
                                in str(stack.get("Name", "")).casefold()
                            ):
                                identity, endpoint = (
                                    external_id(stack.get("Id")),
                                    external_id(stack.get("EndpointId")),
                                )
                                if identity is None or endpoint is None:
                                    raise DceError(
                                        ErrorCode.API_INCOMPATIBLE, "Stack identity missing."
                                    )
                                resource_key(str(identity)), resource_key(str(endpoint))
                                self.scope.portainer_stacks.add(str(identity))
                                self.scope.portainer_endpoints.add(str(endpoint))
                                if len(self.records) >= 200:
                                    raise DceError(
                                        ErrorCode.INVALID_PAYLOAD,
                                        "Discovery result limit exceeded.",
                                    )
                                self.remember(platform, "stack", stack)
            except DceError as error:
                self.failures.append({"platform": platform, "code": error.code.value})

    def summary(self) -> dict[str, Any]:
        return {
            "discovered": len(self.records),
            "failures": self.failures,
            "next_action": (
                "Read paginated project_context discoveries; propose mappings with evidence."
            ),
        }
