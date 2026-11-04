from datetime import datetime
from pathlib import PurePosixPath
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class Node(Model):
    type: NodeType
    instance: Id = Field(description="Source-instance ID; never infer from a platform numeric ID.")
    id: Id


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
    schema_version: Literal[1] = 1
    workspace: Workspace
    scope: Scope = Field(default_factory=Scope)
    relationships: list[Relationship] = Field(default_factory=list, max_length=5000)
    metadata: Metadata = Field(default_factory=Metadata)

    @model_validator(mode="after")
    def identities(self) -> "ProjectContext":
        if len({r.id for r in self.relationships}) != len(self.relationships):
            raise ValueError("duplicate relationship identity within workspace")
        for r in self.relationships:
            for n in (r.from_, r.to):
                platform = (
                    "zentao"
                    if n.type.startswith("zentao_")
                    else "portainer"
                    if n.type.startswith(("portainer_", "swarm_"))
                    else "gitlab"
                    if n.type
                    in {"gitlab_project", "deployment_repository", "ci_pipeline", "ci_job"}
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
