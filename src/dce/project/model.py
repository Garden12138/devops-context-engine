import json
import re
from datetime import datetime
from pathlib import PurePosixPath
from typing import Annotated, Any, Literal, get_args
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)

from dce.project.details import (
    V2_NODE_TYPES,
    BranchDetails,
    DeploymentDetails,
    JobDefinitionDetails,
    JobExecutionDetails,
    NodeDetails,
    RefDetails,
    RuntimeDetails,
)

Id = Annotated[str, Field(min_length=1, max_length=250, pattern=r"^[\w./:@-]+$")]
Text = Annotated[str, Field(max_length=2000)]
Status = Literal["proposed", "confirmed", "rejected", "stale", "conflicted", "unresolved"]
NodeType = Literal[
    "zentao_product",
    "zentao_project",
    "zentao_module",
    "zentao_bug",
    "gitlab_project",
    "code_module",
    "source_path",
    "ci_pipeline",
    "ci_job",
    "container_image",
    "deployment_repository",
    "compose_file",
    "compose_service",
    "portainer_endpoint",
    "portainer_stack",
    "swarm_cluster",
    "swarm_service",
    "environment",
    "source_branch",
    "git_ref",
    "ci_job_definition",
    "ci_job_execution",
    "image_tag",
    "image_digest",
    "deployment_definition",
    "runtime_observation",
]
RelationType = Literal[
    "contains_module",
    "implements",
    "implemented_by",
    "builds",
    "produces_image",
    "uses_image",
    "declares_service",
    "deployed_as",
    "managed_by_stack",
    "runs_in_environment",
    "depends_on",
    "related_to",
]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Root(Model):
    path: str
    kind: Literal["git_repository"] = "git_repository"
    remote_url: str | None = None
    default_branch: str | None = None

    @field_validator("path")
    @classmethod
    def relative_path(cls, v: str) -> str:
        if not v or PurePosixPath(v).is_absolute() or ".." in PurePosixPath(v).parts or "\\" in v:
            raise ValueError("root must be workspace relative")
        return v

    @field_validator("remote_url")
    @classmethod
    def credential_free(cls, v: str | None) -> str | None:
        if v is not None:
            u = urlsplit(v)
            if (
                u.scheme not in {"https", "http", "ssh"}
                or not u.hostname
                or u.username
                or (u.password or u.query or u.fragment)
            ):
                raise ValueError("credential-free canonical remote required")
        return v


class Workspace(Model):
    id: Id
    name: Annotated[str, Field(min_length=1, max_length=200)]
    roots: list[Root] = Field(min_length=1, max_length=100)


class ZenTaoScope(Model):
    instance: Id
    projects: list[Id] = Field(default_factory=list, max_length=1000)
    products: list[Id] = Field(default_factory=list, max_length=1000)
    bugs: list[Id] = Field(default_factory=list, max_length=1000)


class GitLabScope(Model):
    instance: Id
    projects: list[Id] = Field(default_factory=list, max_length=1000)


class PortainerScope(Model):
    instance: Id
    endpoints: list[Id] = Field(default_factory=list, max_length=1000)
    stacks: list[Id] = Field(default_factory=list, max_length=1000)


class Scope(Model):
    zentao: ZenTaoScope | None = None
    gitlab: GitLabScope | None = None
    portainer: PortainerScope | None = None


def node_schema(schema: dict[str, Any]) -> None:
    schema.update(
        {
            "allOf": [
                {
                    "if": {"properties": {"type": {"const": kind}}},
                    "then": {
                        "required": ["details"] if kind in V2_NODE_TYPES else [],
                        "properties": {
                            "details": {
                                "anyOf": [
                                    *([] if kind in V2_NODE_TYPES else [{"type": "null"}]),
                                    {
                                        "type": "object",
                                        "required": ["kind"],
                                        "properties": {"kind": {"const": kind}},
                                    },
                                ]
                            }
                        },
                    },
                }
                for kind in get_args(NodeType)
            ]
        }
    )


class Node(Model):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, json_schema_extra=node_schema)
    type: NodeType
    instance: Id = Field(description="Source-instance ID; never infer from a platform numeric ID.")
    id: Id
    details: NodeDetails | None = None

    @model_serializer(mode="wrap")
    def compatible_dump(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if self.details is None:
            data.pop("details", None)
        return data

    @model_validator(mode="after")
    def typed_details(self) -> "Node":
        if self.type in V2_NODE_TYPES and self.details is None:
            raise ValueError("typed v2 node details required")
        if self.details is not None and self.details.kind != self.type:
            raise ValueError("node type and details kind differ")
        return self


class Evidence(Model):
    kind: Literal[
        "direct_config",
        "structure",
        "platform_observation",
        "agent_analysis",
        "human_statement",
        "legacy_catalog",
    ]
    source: Id
    locator: Annotated[str, Field(min_length=1, max_length=500)]
    observed_at: datetime
    revision: Annotated[str | None, Field(max_length=250)]
    summary: Text

    @field_validator("observed_at")
    @classmethod
    def timezone_required(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timezone required")
        return v


class VersionMatch(Model):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "allOf": [
                {
                    "if": {
                        "properties": {"status": {"enum": ["matched", "mismatched"]}},
                        "required": ["status"],
                    },
                    "then": {
                        "required": ["basis", "expected", "observed", "evidence"],
                        "properties": {
                            "basis": {"type": "string"},
                            "expected": {"type": "string"},
                            "observed": {"type": "string"},
                            "evidence": {"minItems": 1},
                        },
                        "allOf": [
                            {
                                "if": {"properties": {"basis": {"const": basis}}},
                                "then": {
                                    "properties": {
                                        name: {"pattern": pattern}
                                        for name in ("expected", "observed")
                                    }
                                },
                            }
                            for basis, pattern in (
                                ("image_digest", r"^sha256:[a-fA-F0-9]{64}$"),
                                ("commit_sha", r"^(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})$"),
                            )
                        ],
                    },
                }
            ],
        },
    )
    status: Literal["not_verified", "matched", "mismatched", "inconclusive"] = "not_verified"
    basis: Literal["image_digest", "commit_sha"] | None = None
    expected: Annotated[str | None, Field(max_length=250)] = None
    observed: Annotated[str | None, Field(max_length=250)] = None
    evidence: list[Evidence] = Field(default_factory=list, max_length=100)
    notes: Text = ""

    @model_validator(mode="after")
    def immutable_comparison(self) -> "VersionMatch":
        if self.status in {"matched", "mismatched"}:
            pattern = (
                r"sha256:[a-fA-F0-9]{64}"
                if self.basis == "image_digest"
                else r"(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})"
                if self.basis == "commit_sha"
                else None
            )
            if (
                not pattern
                or not self.evidence
                or not all(
                    isinstance(v, str) and re.fullmatch(pattern, v)
                    for v in (self.expected, self.observed)
                )
            ):
                raise ValueError("version comparison needs immutable identities and evidence")
            assert self.expected is not None and self.observed is not None
            same = self.expected.lower() == self.observed.lower()
            if (self.status == "matched") != same:
                raise ValueError("version comparison status contradicts identities")
        return self


class Relationship(Model):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "allOf": [
                {
                    "if": {
                        "properties": {"status": {"const": "confirmed"}},
                        "required": ["status"],
                    },
                    "then": {
                        "required": ["approved_by", "approved_at"],
                        "properties": {
                            "approved_by": {"type": "string", "minLength": 1},
                            "approved_at": {"type": "string"},
                        },
                    },
                }
            ]
        },
    )
    id: Id
    from_: Node = Field(alias="from")
    relation: RelationType
    to: Node
    status: Status = "proposed"
    confidence: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)
    evidence: list[Evidence] = Field(min_length=1, max_length=100)
    approved_by: Annotated[str | None, Field(max_length=200)] = None
    approved_at: datetime | None = None
    last_verified_at: datetime | None = None
    notes: Text = ""
    version_match: VersionMatch | None = None

    @model_serializer(mode="wrap")
    def compatible_dump(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if self.version_match is None:
            data.pop("version_match", None)
        return data

    @field_validator("approved_at", "last_verified_at")
    @classmethod
    def timezone_required(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("timezone required")
        return v

    @model_validator(mode="after")
    def human_confirmation(self) -> "Relationship":
        if self.status == "confirmed":
            if not self.approved_by or not self.approved_by.strip() or self.approved_at is None:
                raise ValueError("confirmed requires human approval metadata")
            if self.approved_by.casefold().strip() in {"agent", "ai", "codex", "cursor", "model"}:
                raise ValueError("Agent cannot approve a relationship")
        return self


class Metadata(Model):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    initialized_by: str = Field(default="host_agent", max_length=200)
    last_refresh_at: datetime | None = None


class ProjectContext(Model):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "allOf": [
                {
                    "if": {"properties": {"schema_version": {"const": 1}}},
                    "then": {
                        "properties": {
                            "relationships": {
                                "items": {
                                    "properties": {
                                        "version_match": {"type": "null"},
                                        **{
                                            name: {
                                                "properties": {
                                                    "type": {
                                                        "enum": [
                                                            k
                                                            for k in get_args(NodeType)
                                                            if k not in V2_NODE_TYPES
                                                        ]
                                                    },
                                                    "details": {"type": "null"},
                                                }
                                            }
                                            for name in ("from", "to")
                                        },
                                    }
                                }
                            }
                        }
                    },
                }
            ],
        },
    )
    schema_version: Literal[1, 2] = 1
    workspace: Workspace
    scope: Scope = Field(default_factory=Scope)
    relationships: list[Relationship] = Field(default_factory=list, max_length=5000)
    metadata: Metadata = Field(default_factory=Metadata)

    @model_validator(mode="after")
    def identities(self) -> "ProjectContext":
        if len({r.id for r in self.relationships}) != len(self.relationships):
            raise ValueError("duplicate relationship identity within workspace")
        seen: dict[tuple[str, str, str], str] = {}
        for r in self.relationships:
            if self.schema_version == 1 and r.version_match is not None:
                raise ValueError("version_match requires explicit v2 migration")
            for n in (r.from_, r.to):
                if self.schema_version == 1 and (n.type in V2_NODE_TYPES or n.details is not None):
                    raise ValueError("typed details require explicit v2 migration")
                identity = (n.type, n.instance, n.id)
                detail = json.dumps(n.model_dump(mode="json"), sort_keys=True)
                if identity in seen and seen[identity] != detail:
                    raise ValueError("same node identity has conflicting details")
                seen[identity] = detail
                platform = (
                    "zentao"
                    if n.type.startswith("zentao_")
                    else "portainer"
                    if n.type.startswith(("portainer_", "swarm_"))
                    or n.type in {"deployment_definition", "runtime_observation"}
                    else "gitlab"
                    if n.type
                    in {
                        "gitlab_project",
                        "deployment_repository",
                        "ci_pipeline",
                        "ci_job",
                        "source_branch",
                        "git_ref",
                        "ci_job_definition",
                        "ci_job_execution",
                    }
                    else None
                )
                if platform:
                    scope = getattr(self.scope, platform)
                    if scope is None or n.instance != scope.instance:
                        raise ValueError("node source instance is outside project scope")
                    collections = {
                        "zentao_project": "projects",
                        "zentao_product": "products",
                        "zentao_bug": "bugs",
                        "gitlab_project": "projects",
                        "deployment_repository": "projects",
                        "portainer_endpoint": "endpoints",
                        "portainer_stack": "stacks",
                    }
                    if n.type in collections and n.id not in getattr(scope, collections[n.type]):
                        raise ValueError("node resource is outside project scope")
                    if isinstance(
                        n.details,
                        (BranchDetails, RefDetails, JobDefinitionDetails, JobExecutionDetails),
                    ):
                        assert self.scope.gitlab is not None
                        if n.details.project_id not in self.scope.gitlab.projects:
                            raise ValueError("qualified project is outside scope")
                    if isinstance(n.details, (DeploymentDetails, RuntimeDetails)):
                        assert self.scope.portainer is not None
                        if n.details.endpoint_id not in self.scope.portainer.endpoints:
                            raise ValueError("qualified endpoint is outside scope")
                        if isinstance(n.details, DeploymentDetails):
                            if n.details.stack_id not in self.scope.portainer.stacks:
                                raise ValueError("qualified Stack is outside scope")
                elif n.instance not in {
                    self.workspace.id,
                    *(
                        s.instance
                        for s in (self.scope.zentao, self.scope.gitlab, self.scope.portainer)
                        if s
                    ),
                }:
                    raise ValueError("unknown source instance")
        return self
