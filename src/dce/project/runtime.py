"""Per-session project workflow. Workspace writes belong exclusively to the Host."""

import fcntl
import json
import os
import secrets
import stat
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, NoReturn

from pydantic import Field

from dce.app.facts import FactScope
from dce.app.services import AppServices
from dce.common.errors import DceError, ErrorCode
from dce.graph.model import fingerprint
from dce.mcp.contracts import Input, Output
from dce.project.approval import ApprovalBroker, NativeApproval, review_message
from dce.project.context import load_project, validate_text
from dce.project.discovery import (
    DiscoverySeeds,
    ProjectDiscovery,
    check_instances,
    scope_from_project,
    subset,
)
from dce.project.model import ProjectContext, Scope
from dce.security.log_grant import ServiceLogGrant


def refuse(
    message: str = "Project is not initialized; explicitly request initialization first.",
) -> NoReturn:
    raise DceError(ErrorCode.REVIEW_REQUIRED, message)


class ProjectRequest(Input):
    workspace: str | None = Field(default=None, min_length=1, max_length=4096)
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=5, ge=1, le=20)


class InitializeRequest(ProjectRequest):
    model_config = {
        "extra": "forbid",
        "strict": True,
        "json_schema_extra": {
            "allOf": [
                {
                    "if": {
                        "properties": {"operation": {"const": "review"}},
                        "required": ["operation"],
                    },
                    "then": {
                        "required": ["proposal"],
                        "properties": {"proposal": {"type": "object"}},
                    },
                },
                {
                    "if": {
                        "properties": {"operation": {"const": "complete"}},
                        "required": ["operation"],
                    },
                    "then": {
                        "required": ["receipt"],
                        "properties": {"receipt": {"type": "string"}},
                    },
                },
            ]
        },
    }
    operation: Literal["begin", "review", "complete", "cancel", "revoke"]
    refresh: bool = False
    seeds: DiscoverySeeds = Field(default_factory=DiscoverySeeds)
    proposal: dict[str, Any] | None = None
    receipt: str | None = Field(default=None, max_length=100)


class ProjectData(Output):
    state: str
    discovered: int | None = None
    workspace_id: str | None = None
    document: dict[str, Any] | None = None
    discoveries: list[dict[str, Any]] = Field(default_factory=list)
    failures: list[dict[str, str]] = Field(default_factory=list)
    unverified_platforms: list[str] = Field(default_factory=list)
    revision: str | None = None
    receipt: str | None = None
    approval_url: str | None = None
    pagination: dict[str, Any] | None = None
    next_action: str | None = None


def document_hash(project: ProjectContext) -> str:
    return fingerprint(project.model_dump(mode="json", by_alias=True))


def private_directory(path: Path) -> Path:
    if path.is_symlink():
        raise DceError(
            ErrorCode.PERMISSION_DENIED, "Private state directory must not be a symlink."
        )
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise DceError(
            ErrorCode.PERMISSION_DENIED, "Private state directory requires owner-only access."
        )
    return path


class PolicyStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.path = directory / "authorization.json"

    def read(self) -> dict[str, Any]:
        private_directory(self.directory)
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return {}
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077
                or info.st_size > 2_000_000
            ):
                raise DceError(ErrorCode.PERMISSION_DENIED, "Unsafe project authorization file.")
            try:
                data = json.loads(stream.read())
                if not isinstance(data, dict):
                    raise ValueError
                return data
            except (ValueError, UnicodeError):
                raise DceError(
                    ErrorCode.INVALID_PAYLOAD, "Invalid project authorization file."
                ) from None

    @contextmanager
    def locked(self) -> Iterator[None]:
        private_directory(self.directory)
        fd = os.open(
            self.directory / ".lock",
            os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
            0o600,
        )
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_mode & 0o077
                or info.st_uid != os.geteuid()
            ):
                raise DceError(ErrorCode.PERMISSION_DENIED, "Unsafe project authorization lock.")
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def write(self, data: dict[str, Any], expected: str | None) -> None:
        with self.locked():
            if self.read().get("generation") != expected:
                raise DceError(
                    ErrorCode.SNAPSHOT_CONFLICT, "Project authorization changed during review."
                )
            fd, name = tempfile.mkstemp(dir=self.directory, prefix=".authorization-")
            try:
                with os.fdopen(fd, "w") as stream:
                    json.dump(data, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(name, self.path)
            finally:
                Path(name).unlink(missing_ok=True)


class ProjectRuntime:
    def __init__(self, state_dir: Path, log_policy: Path | None = None) -> None:
        self.log_policy = log_policy
        self.state_dir = state_dir.expanduser().absolute()
        self.workspace: Path | None = None
        self.bound_with_host_roots = False
        self.store: PolicyStore | None = None
        self.broker = ApprovalBroker()
        self.discovery: ProjectDiscovery | None = None
        self.discovery_deadline = 0.0
        self.reviewed: ProjectContext | None = None
        self.receipt: str | None = None
        self.review_deadline = 0.0
        self.base_generation: str | None = None
        self.seed_revision: str | None = None
        self.review_revision: str | None = None
        self.review_actor: dict[str, str] = {}

    async def bind(
        self,
        requested: str | None,
        roots: list[Path] | None,
        native: NativeApproval | None,
        *,
        require_confirmation: bool = False,
    ) -> dict[str, Any] | None:
        if roots is not None:
            try:
                # Only the selected workspace must exist; unrelated Host roots can be stale.
                roots = [p.resolve(strict=False) for p in roots]
            except (OSError, RuntimeError, ValueError):
                raise DceError(
                    ErrorCode.API_INCOMPATIBLE, "Host workspace paths cannot be resolved."
                ) from None
        if self.workspace is not None:
            if self.bound_with_host_roots and roots is None:
                raise DceError(
                    ErrorCode.API_INCOMPATIBLE,
                    "Host workspace roots became unavailable; retry or open a new MCP session.",
                    retryable=True,
                )
            if (
                requested is not None
                and Path(requested).resolve(strict=True) != self.workspace
                or roots is not None
                and self.workspace not in roots
            ):
                raise DceError(
                    ErrorCode.PERMISSION_DENIED, "Workspace changed; open a new MCP session."
                )
            return None
        if requested is None:
            if roots is None or len(roots) != 1:
                return {
                    "state": "workspace_selection_required",
                    "next_action": "Select the business workspace explicitly.",
                }
            workspace = roots[0]
        else:
            path = Path(requested)
            if not path.is_absolute():
                raise DceError(
                    ErrorCode.PERMISSION_DENIED, "Workspace must be an absolute directory."
                )
            try:
                workspace = path.resolve(strict=True)
            except FileNotFoundError:
                raise DceError(ErrorCode.NOT_FOUND, "Selected workspace does not exist.") from None
            except (OSError, RuntimeError, ValueError):
                raise DceError(
                    ErrorCode.PERMISSION_DENIED, "Selected workspace cannot be resolved."
                ) from None
        if not workspace.exists():
            raise DceError(ErrorCode.NOT_FOUND, "Selected Host workspace does not exist.")
        if not workspace.is_dir():
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Workspace must be a directory.")
        if roots is not None and workspace not in roots:
            raise DceError(ErrorCode.PERMISSION_DENIED, "Workspace is outside Host roots.")
        private_directory(self.state_dir)
        store = PolicyStore(self.state_dir / fingerprint(str(workspace)))
        existing = store.read()
        # Roots-less Hosts can resume an approved path; a new path requires user consent.
        if roots is None and (require_confirmation or existing.get("workspace") != str(workspace)):
            key = "bind:" + fingerprint(str(workspace))
            answer = await self.broker.request(
                key, review_message("绑定工作区", str(workspace), {}), native
            )
            if answer is None:
                return self.broker.waiting(key)
        self.workspace, self.store = workspace, store
        self.bound_with_host_roots = roots is not None
        return None

    def bindings(self, services: AppServices) -> str:
        return fingerprint(
            {
                name: {"instance": config.instance_id, "url": config.base_url}
                for name in ("zentao", "gitlab", "portainer")
                if (config := getattr(services.settings, name)) is not None
            }
        )

    def policy(self, services: AppServices) -> dict[str, Any]:
        if self.workspace is None or self.store is None:
            refuse("Select a workspace using project_context first.")
        assert self.workspace is not None and self.store is not None
        data = self.store.read()
        if (
            not data
            or data.get("revoked")
            or data.get("workspace") != str(self.workspace)
            or data.get("bindings") != self.bindings(services)
        ):
            refuse()
        project = load_project(self.workspace)
        if data.get("workspace_id") != project.workspace.id:
            refuse("Project workspace identity changed; review initialization again.")
        scope = Scope.model_validate(data["scope"])
        check_instances(scope, services)
        return data

    def active_scope(self, services: AppServices) -> FactScope:
        return scope_from_project(Scope.model_validate(self.policy(services)["scope"]))

    @staticmethod
    def check_document_secrets(project: ProjectContext, services: AppServices) -> None:
        secrets_ = services.settings.secrets()
        pending: list[Any] = [project.model_dump(mode="json", by_alias=True)]
        while pending:
            value = pending.pop()
            if isinstance(value, str) and any(secret and secret in value for secret in secrets_):
                raise DceError(
                    ErrorCode.INVALID_PAYLOAD, "Project document contains a configured credential."
                )
            if isinstance(value, dict):
                pending.extend(value)
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)

    def query_scope(self, services: AppServices, name: str, params: dict[str, Any]) -> FactScope:
        active: FactScope | None = None
        try:
            active = self.active_scope(services)
        except DceError as exc:
            if exc.code != ErrorCode.REVIEW_REQUIRED:
                raise
        if self.discovery is None or time.monotonic() >= self.discovery_deadline:
            if active is None:
                refuse()
            assert active is not None
            return self.log_scope(active, services, name, params)
        assert self.store is not None
        if self.store.read().get("generation") != self.base_generation:
            refuse("Authorization changed; start a new explicit initialization.")
        op = params.get("operation")
        allowed = {
            "gitlab_query": {"projects", "project", "tree", "file", "commit"},
            "zentao_query": {"projects", "project", "products", "product", "module_tree"},
            "portainer_query": {
                "stacks",
                "stack",
                "endpoints",
                "endpoint",
                "swarm_info",
                "stack_service",
                "stack_file",
                "services",
                "service",
            },
        }
        if op not in allowed.get(name, set()):
            if active is not None:
                return self.log_scope(active, services, name, params)
            refuse("Temporary discovery only allows initialization facts; review a project first.")
        if name == "gitlab_query" and op == "file":
            allowed_files = {
                "pom.xml",
                "package.json",
                "settings.gradle",
                "settings.gradle.kts",
                "build.gradle",
                "build.gradle.kts",
                "go.mod",
                "go.work",
                "Dockerfile",
                ".gitlab-ci.yml",
                "compose.yml",
                "compose.yaml",
                "docker-compose.yml",
                "docker-compose.yaml",
            }
            if Path(params["path"]).name not in allowed_files:
                refuse("Discovery file reads are limited to build/deployment metadata.")
        assert self.discovery is not None
        result = scope_from_project(Scope())
        for field in (
            "gitlab_projects",
            "zentao_projects",
            "zentao_products",
            "zentao_bugs",
            "portainer_endpoints",
            "portainer_stacks",
        ):
            values = set(getattr(self.discovery.scope, field))
            if active is not None:
                values.update(getattr(active, field))
            setattr(result, field, values)
        return result

    def log_scope(
        self, scope: FactScope, services: AppServices, name: str, params: dict[str, Any]
    ) -> FactScope:
        if name != "portainer_query" or params.get("operation") != "service_logs":
            return scope
        if self.log_policy is None:
            raise DceError(
                ErrorCode.PERMISSION_DENIED, "Service logs require an independent exact policy."
            )
        grant = ServiceLogGrant.load(self.log_policy)
        config = services.settings.portainer
        if (
            config is None
            or grant.spec.source_instance != config.instance_id
            or grant.spec.endpoint_id not in scope.portainer_endpoints
            or grant.spec.stack_id not in scope.portainer_stacks
        ):
            raise DceError(
                ErrorCode.PERMISSION_DENIED, "Log policy is outside the approved project."
            )
        scope.portainer_log_policy = grant
        scope.portainer_log_scopes = {(grant.spec.endpoint_id, grant.spec.stack_id)}
        return scope

    def context(self, services: AppServices, page: int = 1, limit: int = 10) -> dict[str, Any]:
        if self.workspace is None or self.store is None:
            return {"state": "workspace_selection_required"}
        try:
            policy = self.policy(services)
        except DceError as exc:
            if exc.code != ErrorCode.REVIEW_REQUIRED:
                raise
            policy = {}
        project: ProjectContext | None = None
        if (self.workspace / ".dce/project.yaml").exists():
            project = load_project(self.workspace)
            self.check_document_secrets(project, services)
        state = (
            policy.get("state", "ready")
            if policy
            else "discovering"
            if self.discovery and time.monotonic() < self.discovery_deadline
            else "uninitialized"
        )
        if project is not None and policy and document_hash(project) != policy["document_revision"]:
            state = "changed_pending_review"
        if state == "uninitialized" and self.store.read().get("revoked"):
            state = "revoked"
        result: dict[str, Any] = {
            "state": state,
            "workspace_id": project.workspace.id if project else None,
            "next_action": (
                "User must explicitly request initialization/refresh; no automatic scan."
            ),
        }
        if policy:
            result["unverified_platforms"] = policy.get("unverified_platforms", [])
            result["failures"] = policy.get("failures", [])
        if project is not None:
            document = project.model_dump(mode="json", by_alias=True)
            relationships = document["relationships"]
            # Unreviewed files must not impersonate effective confirmed mappings.
            if state not in {"ready", "partial"}:
                for row in relationships:
                    if row["status"] == "confirmed" and (
                        policy.get("approved_relations", {}).get(row["id"]) != fingerprint(row)
                    ):
                        row.update(status="proposed", approved_by=None, approved_at=None)
            document["relationships"] = relationships[(page - 1) * limit : page * limit]
            result.update(
                document=document,
                revision=document_hash(project),
                pagination={
                    "page": page,
                    "limit": limit,
                    "total": len(relationships),
                    "more_available": page * limit < len(relationships),
                },
            )
        if self.discovery is not None:
            result["discoveries"] = self.discovery.records[(page - 1) * limit : page * limit]
            result["failures"] = self.discovery.failures
            if project is None:
                result["pagination"] = {
                    "page": page,
                    "limit": limit,
                    "total": len(self.discovery.records),
                    "more_available": page * limit < len(self.discovery.records),
                }
        return result

    async def initialize(
        self, request: InitializeRequest, services: AppServices, native: NativeApproval | None
    ) -> dict[str, Any]:
        if self.workspace is None or self.store is None:
            refuse("Select a workspace before initialization.")
        assert self.workspace is not None and self.store is not None
        op = request.operation
        if op == "cancel":
            self.close()
            return {"state": "cancelled"}
        if op == "revoke":
            key = "revoke"
            answer = await self.broker.request(
                key, review_message("撤销项目授权", str(self.workspace), {}), native
            )
            if answer is None:
                return self.broker.waiting(key)
            current = self.store.read()
            self.store.write(
                {"generation": secrets.token_hex(16), "revoked": True}, current.get("generation")
            )
            self.close()
            return {"state": "revoked"}
        if op == "begin":
            current = self.store.read()
            if (
                current
                and not current.get("revoked")
                and not request.refresh
                and current.get("bindings") == self.bindings(services)
            ):
                return {
                    "state": "already_initialized",
                    "next_action": (
                        "Read project_context; explicitly request refresh to change mappings."
                    ),
                }
            seeds = request.seeds
            from dce.project.context import reject_secrets

            reject_secrets(seeds.model_dump())
            revision = fingerprint(seeds.model_dump())
            if (
                self.discovery is not None
                and self.seed_revision == revision
                and time.monotonic() < self.discovery_deadline
            ):
                return {"state": "discovering", **self.discovery.summary()}
            self.reviewed = self.receipt = None
            key = "begin:" + revision
            message = review_message(
                "用户主动初始化：允许30分钟有界发现", str(self.workspace), seeds.model_dump()
            )
            answer = await self.broker.request(key, message, native)
            if answer is None:
                return self.broker.waiting(key)
            if self.store.read().get("generation") != current.get("generation"):
                refuse("Authorization changed during user confirmation.")
            self.base_generation = current.get("generation")
            self.discovery = ProjectDiscovery(services)
            self.discovery.run(seeds)
            self.discovery_deadline = time.monotonic() + 1800
            self.seed_revision = revision
            return {"state": "discovering", **self.discovery.summary()}
        if op == "review":
            if self.discovery is None or time.monotonic() >= self.discovery_deadline:
                refuse("Explicitly begin initialization before proposing a project.")
            if request.proposal is None:
                raise DceError(ErrorCode.INVALID_PAYLOAD, "Project proposal is required.")
            project = validate_text(json.dumps(request.proposal))
            self.check_document_secrets(project, services)
            for root in project.workspace.roots:
                if not (self.workspace / root.path).resolve().is_relative_to(self.workspace):
                    refuse("Project Git root escapes the selected workspace.")
            check_instances(project.scope, services)
            proposed = scope_from_project(project.scope)
            allowed = self.discovery.scope
            try:
                old = self.active_scope(services)
                for name in (
                    "gitlab_projects",
                    "zentao_projects",
                    "zentao_products",
                    "zentao_bugs",
                    "portainer_endpoints",
                    "portainer_stacks",
                ):
                    getattr(allowed, name).update(getattr(old, name))
            except DceError as error:
                if error.code != ErrorCode.REVIEW_REQUIRED:
                    raise
            if not subset(proposed, allowed):
                refuse("Proposal contains resources not discovered or previously authorized.")
            previous_approvals: dict[str, str] = {}
            try:
                previous_approvals = self.policy(services).get("approved_relations", {})
            except DceError as error:
                if error.code != ErrorCode.REVIEW_REQUIRED:
                    raise
            # Keep unchanged actual approvals, but never trust newly supplied approval fields.
            for relation in project.relationships:
                if relation.status == "confirmed" and previous_approvals.get(
                    relation.id
                ) != fingerprint(relation.model_dump(mode="json", by_alias=True)):
                    relation.status, relation.approved_by, relation.approved_at = (
                        "proposed",
                        None,
                        None,
                    )
            key = "review:" + document_hash(project)
            if self.reviewed is None or self.receipt is None or self.review_revision != key:
                self.reviewed = None
                self.receipt = None
                answer = await self.broker.request(
                    key,
                    review_message(
                        "审核完整关系和长期项目范围",
                        str(self.workspace),
                        project.model_dump(mode="json", by_alias=True),
                    ),
                    native,
                )
                if answer is None:
                    return self.broker.waiting(key)
                selected = {s.strip() for s in answer["relationships"].split(",") if s.strip()}
                if selected - {r.id for r in project.relationships}:
                    raise DceError(
                        ErrorCode.INVALID_PAYLOAD, "Unknown relationship selected for confirmation."
                    )
                for relation in project.relationships:
                    if relation.id in selected:
                        relation.status, relation.approved_by = "confirmed", answer["actor"]
                        relation.approved_at = datetime.now(UTC)
                self.reviewed = validate_text(
                    json.dumps(project.model_dump(mode="json", by_alias=True))
                )
                self.check_document_secrets(self.reviewed, services)
                self.receipt, self.review_deadline = (
                    secrets.token_urlsafe(32),
                    time.monotonic() + 600,
                )
                self.review_revision = key
                self.review_actor = answer
            if time.monotonic() >= self.review_deadline:
                refuse("Review receipt expired.")
            assert self.reviewed is not None
            document = self.reviewed.model_dump(mode="json", by_alias=True)
            total = len(document["relationships"])
            document["relationships"] = document["relationships"][
                (request.page - 1) * request.limit : request.page * request.limit
            ]
            return {
                "state": "awaiting_host_save",
                "document": document,
                "receipt": self.receipt,
                "revision": document_hash(self.reviewed),
                "pagination": {
                    "page": request.page,
                    "limit": request.limit,
                    "total": total,
                    "more_available": request.page * request.limit < total,
                },
                "next_action": (
                    "Host assembles all pages, saves project.yaml, "
                    "then calls complete with receipt."
                ),
            }
        if (
            self.reviewed is None
            or self.receipt is None
            or request.receipt is None
            or not secrets.compare_digest(request.receipt, self.receipt)
            or time.monotonic() >= self.review_deadline
        ):
            refuse("A current user-reviewed receipt is required.")
        saved = load_project(self.workspace)
        if document_hash(saved) != document_hash(self.reviewed):
            refuse("Saved project differs from the user-reviewed proposal.")
        missing = [
            name for name in ("zentao", "gitlab", "portainer") if getattr(saved.scope, name) is None
        ]
        state = "partial" if missing else "ready"
        self.store.write(
            {
                "state": state,
                "unverified_platforms": missing,
                "failures": self.discovery.failures if self.discovery is not None else [],
                "version": 1,
                "generation": secrets.token_hex(16),
                "workspace": str(self.workspace),
                "workspace_id": saved.workspace.id,
                "bindings": self.bindings(services),
                "approval": self.review_actor,
                "approved_relations": {
                    r.id: fingerprint(r.model_dump(mode="json", by_alias=True))
                    for r in saved.relationships
                    if r.status == "confirmed"
                },
                "document_revision": document_hash(saved),
                "scope": saved.scope.model_dump(mode="json"),
            },
            self.base_generation,
        )
        self.close()
        return {
            "state": state,
            "unverified_platforms": missing,
            "workspace_id": saved.workspace.id,
            "revision": document_hash(saved),
        }

    def close(self) -> None:
        self.broker.close()
        self.discovery = None
        self.reviewed = None
        self.receipt = None
        self.discovery_deadline = 0
