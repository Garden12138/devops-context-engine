"""Scoped fact tools: no graph lookup, inference, workspace write, or arbitrary URL."""

from typing import Literal

from pydantic import Field, model_validator

from dce.mcp.contracts import Input, Output, ResourceKey


class Query(Input):
    instance: ResourceKey = Field(description="Exact configured source-instance identity.")
    page: int = Field(default=1, ge=1, le=10000)
    limit: int = Field(default=20, ge=1, le=100)


class GitLabQuery(Query):
    operation: Literal[
        "projects", "project", "tree", "file", "commit", "pipelines", "pipeline", "jobs", "trace"
    ]
    project_id: ResourceKey | None = None
    ref: ResourceKey | None = None
    path: ResourceKey | None = None
    pipeline_id: ResourceKey | None = None
    job_id: ResourceKey | None = None
    search: str = Field(default="", max_length=100)
    tail_lines: int = Field(default=100, ge=1, le=500)
    start_line: int = Field(default=1, ge=1, le=100000)

    @model_validator(mode="after")
    def required_arguments(self) -> "GitLabQuery":
        if self.operation != "projects" and self.project_id is None:
            raise ValueError("project required")
        if self.operation in {"tree", "file", "commit"} and self.ref is None:
            raise ValueError("ref required")
        if self.operation == "file" and self.path is None:
            raise ValueError("path required")
        if self.operation in {"pipeline", "jobs"} and self.pipeline_id is None:
            raise ValueError("pipeline required")
        if self.operation == "trace" and self.job_id is None:
            raise ValueError("job required")
        return self


class ZenTaoQuery(Query):
    operation: Literal[
        "projects",
        "project",
        "products",
        "product",
        "modules",
        "bugs",
        "bug",
        "attachments",
        "image",
    ]
    project_id: ResourceKey | None = None
    product_id: ResourceKey | None = None
    bug_id: ResourceKey | None = None
    asset_index: int = Field(default=0, ge=0, le=9)
    search: str = Field(default="", max_length=100)

    @model_validator(mode="after")
    def required_arguments(self) -> "ZenTaoQuery":
        if self.operation == "project" and self.project_id is None:
            raise ValueError("project required")
        if self.operation == "product" and self.product_id is None:
            raise ValueError("product required")
        if self.operation in {"bugs", "modules"} and not (self.project_id or self.product_id):
            raise ValueError("parent required")
        if self.operation in {"bug", "attachments", "image"} and self.bug_id is None:
            raise ValueError("bug required")
        return self


class PortainerQuery(Query):
    operation: Literal[
        "endpoints",
        "endpoint",
        "stacks",
        "stack",
        "stack_file",
        "swarm_info",
        "services",
        "service",
    ]
    endpoint_id: ResourceKey | None = None
    stack_id: ResourceKey | None = None
    service_id: ResourceKey | None = None
    namespace: ResourceKey | None = None

    @model_validator(mode="after")
    def required_arguments(self) -> "PortainerQuery":
        if self.operation in {"endpoint", "stack_file", "swarm_info", "services", "service"}:
            if self.endpoint_id is None:
                raise ValueError("endpoint required")
        if self.operation in {"stack", "stack_file"} and self.stack_id is None:
            raise ValueError("stack required")
        if self.operation == "service" and self.service_id is None:
            raise ValueError("service required")
        return self


class Source(Output):
    platform: Literal["zentao", "gitlab", "portainer"]
    instance: str
    operation: str
    resource_id: str | None


class Pagination(Output):
    page: int
    limit: int
    next_page: int | None
    more_available: bool


class FactEvidence(Output):
    source: Source
    locator: str
    observed_at: str
    revision: str
    summary: str


class FactData(Output):
    source: Source
    observed_at: str
    revision: str
    records: list[dict[str, object]] = Field(description="Redacted operation-specific facts only.")
    evidence: list[FactEvidence]
    pagination: Pagination
    truncated: bool
    warnings: list[str]
    verification: Literal["live_read_only"]
    image_delivery: Literal["not_requested", "delivered", "not_delivered"]


FACT_INPUTS: dict[str, type[Input]] = {
    "zentao_query": ZenTaoQuery,
    "gitlab_query": GitLabQuery,
    "portainer_query": PortainerQuery,
}
FACT_DESCRIPTIONS = {
    "zentao_query": "ZenTao scoped read-only facts: projects/products/bugs, module IDs observed in "
    "a Bug page (partial inventory), attachment metadata, or one authenticated MCP ImageContent. "
    "Search only within startup scope. No mapping. Instance must match configuration.",
    "gitlab_query": "GitLab scoped project/tree/ref file/commit/pipeline/jobs/trace facts. "
    "Explicit page/limit; file uses start_line and tail_lines, trace uses tail_lines. "
    "Secret files forbidden; Compose excludes environment values. No inference.",
    "portainer_query": "Portainer scoped read-only endpoint/stack/Stack File/Swarm/services facts. "
    "Stack File returns parsed Compose facts only. Env/registry auth excluded. "
    "Status and replicas do not establish health, environment or deployment equivalence.",
}

# Publish descriptions for every input, including shared pagination controls.
for _model in FACT_INPUTS.values():
    for _name, _field in _model.model_fields.items():
        if not _field.description:
            _field.description = _name.replace("_", " ") + "; scoped read-only query parameter."
    _model.model_rebuild(force=True)
