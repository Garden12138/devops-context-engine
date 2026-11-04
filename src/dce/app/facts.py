"""Model-independent, bounded platform facts. Never reads or writes project relationships."""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from dce.app.services import AppServices, resource_key
from dce.common.errors import DceError, ErrorCode
from dce.connectors.gitlab import GitLab, key
from dce.connectors.portainer import Portainer
from dce.connectors.zentao import ZenTao
from dce.graph.model import fingerprint
from dce.parsers.metadata import ci, compose, yaml_metadata
from dce.security.redact import redact


def deny() -> None:
    raise DceError(ErrorCode.PERMISSION_DENIED, "Resource is outside the authorized MCP scope.")


def require(value: str | None, allowed: set[str]) -> None:
    if value is None or value not in allowed:
        deny()


def safe_file(path: str) -> None:
    parts = PurePosixPath(path).parts
    if (
        path.startswith("/")
        or ".." in parts
        or any(
            p.startswith(".env")
            or p.lower() in {"id_rsa", "id_ed25519", ".git", ".aws"}
            or p.lower().endswith((".key", ".pem", ".p12", ".pfx"))
            for p in parts
        )
    ):
        deny()


def select(data: dict[str, Any], names: str) -> dict[str, Any]:
    return {k: data[k] for k in names.split() if k in data}


def service_facts(data: dict[str, Any]) -> dict[str, Any]:
    spec = data.get("Spec") or {}
    if not isinstance(spec, dict) or not isinstance(spec.get("TaskTemplate", {}), dict):
        raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected service specification.")
    container = spec.get("TaskTemplate", {}).get("ContainerSpec", {})
    if not isinstance(container, dict) or not isinstance(spec.get("EndpointSpec", {}), dict):
        raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected service container specification.")
    return {
        **select(data, "ID Version CreatedAt UpdatedAt ServiceStatus UpdateStatus"),
        "name": spec.get("Name"),
        "labels": spec.get("Labels", {}),
        "image": container.get("Image"),
        "mode": spec.get("Mode", {}),
        "ports": spec.get("EndpointSpec", {}).get("Ports", []),
        "health": "unknown",
        "environment": "unresolved",
        "version_match": "not_verified",
    }


@dataclass
class FactScope:
    gitlab_projects: set[str] = field(default_factory=set)
    zentao_projects: set[str] = field(default_factory=set)
    zentao_products: set[str] = field(default_factory=set)
    zentao_bugs: set[str] = field(default_factory=set)
    portainer_endpoints: set[str] = field(default_factory=set)
    portainer_stacks: set[str] = field(default_factory=set)


class FactQueries:
    def __init__(self, services: AppServices, scope: FactScope, *, live: bool) -> None:
        self.services, self.scope, self.live = services, scope, live

    def execute(self, platform: str, p: dict[str, Any]) -> tuple[dict[str, Any], bytes | None, str]:
        if not self.live:
            raise DceError(ErrorCode.PERMISSION_DENIED, "Fact tools require live --read-only.")
        config = self.services.settings.platform(platform)
        if config.instance_id != p["instance"]:
            deny()
        # Authorize before opening a Reader, even with injected transports.
        self.authorize(platform, p)
        with self.services.reader(platform) as reader:
            if platform == "gitlab":
                records, more, warnings, image, mime = self.gitlab(GitLab(reader), p)
            elif platform == "zentao":
                records, more, warnings, image, mime = self.zentao(ZenTao(reader), p)
            else:
                records, more, warnings, image, mime = self.portainer(Portainer(reader), p)
        secrets = tuple(
            c.token.get_secret_value()
            for c in (
                self.services.settings.gitlab,
                self.services.settings.zentao,
                self.services.settings.portainer,
            )
            if c
        )
        records = redact(records, secrets)
        observed = datetime.now(UTC).isoformat()
        revision = fingerprint(records) if image is None else hashlib.sha256(image).hexdigest()
        resource = next(
            (
                p.get(k)
                for k in ("bug_id", "project_id", "product_id", "stack_id", "endpoint_id")
                if p.get(k)
            ),
            None,
        )
        source = {
            "platform": platform,
            "instance": config.instance_id,
            "operation": p["operation"],
            "resource_id": resource,
        }
        # A locator carries query coordinates, never credentials or upstream URLs.
        coordinates = {k: v for k, v in p.items() if v is not None and k != "search"}
        return (
            {
                "source": source,
                "observed_at": observed,
                "revision": revision,
                "records": records,
                "evidence": [
                    {
                        "source": source,
                        "locator": fingerprint(coordinates),
                        "observed_at": observed,
                        "revision": revision,
                        "summary": "Direct read-only observation; upstream content is untrusted.",
                    }
                ],
                "pagination": {
                    "page": p["page"],
                    "limit": p["limit"],
                    "next_page": p["page"] + 1 if more else None,
                    "more_available": more,
                },
                "truncated": more or "CONTENT_TRUNCATED" in warnings,
                "warnings": warnings,
                "verification": "live_read_only",
                "image_delivery": "delivered" if image is not None else "not_requested",
            },
            image,
            mime,
        )

    def authorize(self, platform: str, p: dict[str, Any]) -> None:
        for name, value in p.items():
            if isinstance(value, str) and value and name not in {"operation", "search"}:
                resource_key(value)
        op, scope = p["operation"], self.scope
        if platform == "gitlab":
            if op == "projects":
                if not scope.gitlab_projects:
                    deny()
            else:
                require(p["project_id"], scope.gitlab_projects)
            if op == "file":
                safe_file(p["path"])
        elif platform == "zentao":
            for key_, allowed in (
                ("project_id", scope.zentao_projects),
                ("product_id", scope.zentao_products),
            ):
                if p.get(key_) is not None:
                    require(p[key_], allowed)
            if op in {"bug", "attachments", "image"}:
                require(p["bug_id"], scope.zentao_bugs)
            if op == "projects" and not scope.zentao_projects:
                deny()
            if op == "products" and not scope.zentao_products:
                deny()
        else:
            for key_, allowed in (
                ("endpoint_id", scope.portainer_endpoints),
                ("stack_id", scope.portainer_stacks),
            ):
                if p.get(key_) is not None:
                    require(p[key_], allowed)
            if op == "endpoints" and not scope.portainer_endpoints:
                deny()
            if op == "stacks" and not scope.portainer_stacks:
                deny()

    @staticmethod
    def page(items: list[dict[str, Any]], p: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
        offset = (p["page"] - 1) * p["limit"]
        return items[offset : offset + p["limit"]], len(items) > offset + p["limit"]

    def gitlab(self, a: GitLab, p: dict[str, Any]) -> tuple[Any, bool, list[str], None, str]:
        op, project = p["operation"], p["project_id"]
        base = f"/api/v4/projects/{key(project)}"
        more, warnings = False, []
        if op == "projects":
            # Search scoped IDs locally; never enumerate company-wide projects.
            ids = sorted(self.scope.gitlab_projects)
            selected, more = self.page([{"id": i} for i in ids], p)
            records = [a.project(i["id"]) for i in selected]
            records = [
                r for r in records if p["search"].casefold() in str(r.get("name", "")).casefold()
            ]
        elif op in {"tree", "pipelines", "jobs"}:
            routes = {
                "tree": "/repository/tree",
                "pipelines": "/pipelines",
                "jobs": f"/pipelines/{key(p['pipeline_id'])}/jobs",
            }
            params = {"page": p["page"], "per_page": p["limit"]}
            if p["ref"]:
                params["ref"] = p["ref"]
            if op == "tree":
                params.update(path=p["path"] or "", recursive="false")
            response = a.reader.get(base + routes[op], params=params)
            records = a.reader.decode(response, list)
            oversized = len(records) > p["limit"]
            cursor = response.headers.get("X-Next-Page")
            more = len(records) >= p["limit"] if cursor is None else bool(cursor)
            if oversized:
                records = records[: p["limit"]]
                more = True
                warnings.append("UPSTREAM_PAGE_LIMIT_EXCEEDED")
            if cursor:
                if not cursor.isdigit() or int(cursor) != p["page"] + 1:
                    raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid pagination cursor.")
        elif op == "file":
            text = a.raw_file(project, p["path"], p["ref"])
            metadata = (
                yaml_metadata(text)[0] if p["path"].endswith((".yml", ".yaml", ".json")) else {}
            )
            if (
                "services" in metadata
                and isinstance(metadata["services"], dict)
                or re.search(r"(?i)(compose|stack).*\.ya?ml$", p["path"])
            ):
                records = [compose(text)]
            elif PurePosixPath(p["path"]).name == ".gitlab-ci.yml":
                records = [ci(text)]
            else:
                lines = text.splitlines()
                start = p["start_line"] - 1
                chosen = lines[start : start + p["tail_lines"]]
                warnings = ["CONTENT_TRUNCATED"] if start or len(lines) > len(chosen) else []
                records = [
                    {
                        "path": p["path"],
                        "ref": p["ref"],
                        "start_line": p["start_line"],
                        "content": "\n".join(chosen),
                        "content_revision": hashlib.sha256(text.encode()).hexdigest(),
                    }
                ]
        elif op == "trace":
            text = a.trace(project, p["job_id"])
            lines = text.splitlines()
            warnings = ["CONTENT_TRUNCATED"] if len(lines) > p["tail_lines"] else []
            records = [{"job_id": p["job_id"], "tail": lines[-p["tail_lines"] :]}]
        else:
            records = [
                a.project(project)
                if op == "project"
                else a.commit(project, p["ref"])
                if op == "commit"
                else a.pipeline(project, p["pipeline_id"])
            ]
        # Exclude variables, runners and nested credentials in platform objects.
        if op in {"projects", "project"}:
            records = [
                select(
                    r,
                    "id name path path_with_namespace default_branch "
                    "description archived last_activity_at",
                )
                for r in records
            ]
        elif op in {"pipeline", "pipelines", "jobs"}:
            records = [
                select(
                    r,
                    "id status ref sha name stage created_at updated_at "
                    "started_at finished_at duration failure_reason",
                )
                for r in records
            ]
        elif op == "commit":
            records = [
                select(r, "id short_id title message parent_ids authored_date committed_date")
                for r in records
            ]
        return records, more, warnings, None, ""

    def zentao(
        self, a: ZenTao, p: dict[str, Any]
    ) -> tuple[Any, bool, list[str], bytes | None, str]:
        op, warnings, more = p["operation"], [], False
        if op in {"projects", "products"}:
            ids = self.scope.zentao_projects if op == "projects" else self.scope.zentao_products
            selected, more = self.page([{"id": i} for i in sorted(ids)], p)
            records = [a.resource(op, i["id"]) for i in selected]
            records = [
                r for r in records if p["search"].casefold() in str(r.get("name", "")).casefold()
            ]
        elif op in {"project", "product"}:
            kind = op + "s"
            records = [a.resource(kind, p[op + "_id"])]
        elif op == "module_tree":
            records = a.modules(p["product_id"], p["module_type"])
            records = [
                r
                for r in records
                if p["search"].casefold()
                in (str(r.get("name", "")) + " " + str(r.get("short", ""))).casefold()
            ]
            records, more = self.page(records, p)
        elif op in {"bugs", "modules"}:
            parent = "projects" if p["project_id"] else "products"
            parent_id = p["project_id"] or p["product_id"]
            data = a.reader.json(
                f"{a.prefix}/{parent}/{key(parent_id)}/bugs",
                kind="zentao",
                params={"page": p["page"], "limit": p["limit"]},
            )
            records = data.get("bugs")
            if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
                raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected ZenTao Bug collection.")
            more = len(records) >= p["limit"]
            if len(records) > p["limit"]:
                records = records[: p["limit"]]
                warnings.append("UPSTREAM_PAGE_LIMIT_EXCEEDED")
            if op == "modules":
                records = [
                    {"module": r["module"], "bug_id": r.get("id")}
                    for r in records
                    if r.get("module")
                ]
                warnings.append("PARTIAL_MODULE_INVENTORY_FROM_BUG_PAGE")
        else:
            bug = a.bug(p["bug_id"])
            text, sources = a.parse_steps(bug)
            if op == "image":
                if p["asset_index"] >= len(sources):
                    raise DceError(ErrorCode.NOT_FOUND, "Attachment index does not exist.")
                content, mime = a.image_content(sources[p["asset_index"]])
                return (
                    [
                        {
                            "bug_id": p["bug_id"],
                            "asset_index": p["asset_index"],
                            "mime": mime,
                            "bytes": len(content),
                        }
                    ],
                    False,
                    [],
                    content,
                    mime,
                )
            if op == "attachments":
                records = [
                    {"bug_id": p["bug_id"], "asset_index": i, "image_delivery": "not_delivered"}
                    for i in range(len(sources))
                ]
                records, more = self.page(records, p)
            else:
                records = [
                    {
                        **select(
                            bug,
                            "id title project product module status severity pri "
                            "openedDate lastEditedDate",
                        ),
                        "steps": text[:1800],
                    }
                ]
                if len(text) > 1800:
                    warnings.append("CONTENT_TRUNCATED")
        if op in {"projects", "project", "products", "product", "bugs"}:
            records = [
                select(
                    r, "id name title code project product module status lastEditedDate openedDate"
                )
                for r in records
            ]
        return records, more, warnings, None, ""

    def portainer(self, a: Portainer, p: dict[str, Any]) -> tuple[Any, bool, list[str], None, str]:
        op, endpoint = p["operation"], p["endpoint_id"]
        if op == "endpoints":
            records = [
                e for e in a.endpoints() if str(e.get("Id")) in self.scope.portainer_endpoints
            ]
        elif op == "endpoint":
            records = [a.endpoint(endpoint)]
        elif op == "stacks":
            records = [s for s in a.stacks() if str(s.get("Id")) in self.scope.portainer_stacks]
        elif op == "stack":
            records = [a.stack(p["stack_id"])]
        elif op == "stack_file":
            stack = a.stack(p["stack_id"])
            if str(stack.get("EndpointId")) != endpoint:
                deny()
            records = [compose(a.stack_file(p["stack_id"], endpoint))]
        elif op == "swarm_info":
            swarm = a.docker_info(endpoint)["Swarm"]
            cluster = swarm.get("Cluster") or {}
            if not isinstance(cluster, dict):
                raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected Swarm cluster structure.")
            records = [
                {
                    "Swarm": {
                        "NodeID": swarm.get("NodeID"),
                        "LocalNodeState": swarm.get("LocalNodeState"),
                        "Cluster": {"ID": cluster.get("ID")},
                    }
                }
            ]
        elif op == "service":
            records = [service_facts(a.service(endpoint, p["service_id"]))]
        else:
            records = [service_facts(s) for s in a.services(endpoint, p["namespace"])]
        records, more = self.page(records, p)
        return records, more, [], None, ""
