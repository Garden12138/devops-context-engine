"""Typed v2 facts. These are supplied by the Host, never discovered or inferred here."""

from datetime import datetime
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Identifier = Annotated[str, Field(min_length=1, max_length=250, pattern=r"^[\w./:@-]+$")]
CommitSha = Annotated[str, Field(pattern=r"^(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})$")]
Digest = Annotated[str, Field(pattern=r"^sha256:[a-fA-F0-9]{64}$")]
Repository = Annotated[
    str, Field(min_length=1, max_length=250, pattern=r"^[\w.-]+(?::\d+)?(?:/[\w.-]+)*$")
]


class Details(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BranchDetails(Details):
    kind: Literal["source_branch"]
    project_id: Identifier
    ref: Identifier
    commit_sha: CommitSha | None = None


class RefDetails(Details):
    kind: Literal["git_ref"]
    project_id: Identifier
    ref: Identifier
    ref_kind: Literal["branch", "tag", "commit"]
    commit_sha: CommitSha | None = None


class JobDefinitionDetails(Details):
    kind: Literal["ci_job_definition"]
    project_id: Identifier
    ref: Identifier
    path: Identifier
    job_name: Annotated[str, Field(min_length=1, max_length=200)]
    content_revision: Annotated[str | None, Field(max_length=250)] = None

    @field_validator("path")
    @classmethod
    def safe_path(cls, value: str) -> str:
        parts = PurePosixPath(value).parts
        if PurePosixPath(value).is_absolute() or ".." in parts or "\\" in value:
            raise ValueError("repository-relative definition path required")
        return value


class JobExecutionDetails(Details):
    kind: Literal["ci_job_execution"]
    project_id: Identifier
    pipeline_id: Identifier
    job_id: Identifier
    ref: Identifier | None = None
    sha: CommitSha | None = None
    status: Annotated[str | None, Field(max_length=100)] = None


class ImageTagDetails(Details):
    kind: Literal["image_tag"]
    repository: Repository
    tag: Annotated[str, Field(pattern=r"^[\w][\w.-]{0,127}$")]


class ImageDigestDetails(Details):
    kind: Literal["image_digest"]
    repository: Repository
    digest: Digest


class DeploymentDetails(Details):
    kind: Literal["deployment_definition"]
    endpoint_id: Identifier
    stack_id: Identifier
    service_name: Annotated[
        str, Field(min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
    ]
    file_revision: Annotated[str | None, Field(max_length=250)] = None


class RuntimeDetails(Details):
    kind: Literal["runtime_observation"]
    endpoint_id: Identifier
    service_id: Identifier
    observed_at: datetime
    image: Annotated[str | None, Field(max_length=500)] = None
    digest: Digest | None = None
    version_index: int | None = Field(default=None, ge=0)

    @field_validator("observed_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timezone required")
        return value


class EnvironmentDetails(Details):
    kind: Literal["environment"]
    name: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(max_length=2000)] = ""


NodeDetails = Annotated[
    BranchDetails
    | RefDetails
    | JobDefinitionDetails
    | JobExecutionDetails
    | ImageTagDetails
    | ImageDigestDetails
    | DeploymentDetails
    | RuntimeDetails
    | EnvironmentDetails,
    Field(discriminator="kind"),
]
V2_NODE_TYPES = {
    "source_branch",
    "git_ref",
    "ci_job_definition",
    "ci_job_execution",
    "image_tag",
    "image_digest",
    "deployment_definition",
    "runtime_observation",
}
