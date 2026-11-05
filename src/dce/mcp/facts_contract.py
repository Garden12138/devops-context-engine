"""Scoped fact tools: no graph lookup, inference, workspace write, or arbitrary URL."""

from typing import Any, Literal

from pydantic import Field, model_validator

from dce.mcp.contracts import Input, Output, ResourceKey


class Query(Input):
    instance: ResourceKey = Field(description="Exact configured source-instance identity.")
    page: int = Field(default=1, ge=1, le=10000)
    limit: int = Field(default=20, ge=1, le=100)


class GitLabQuery(Query):
    operation: Literal[
        "projects",
        "project",
        "tree",
        "file",
        "commit",
        "pipelines",
        "pipeline",
        "jobs",
        "trace",
        "project_jobs",
        "branch_jobs",
        "pipeline_bridges",
    ]
    project_id: ResourceKey | None = None
    ref: ResourceKey | None = None
    path: ResourceKey | None = None
    pipeline_id: ResourceKey | None = None
    job_id: ResourceKey | None = None
    include_retried: bool = Field(default=False, description="Pipeline jobs only; include retries.")
    job_statuses: list[
        Literal[
            "created",
            "pending",
            "running",
            "failed",
            "success",
            "canceled",
            "skipped",
            "waiting_for_resource",
            "manual",
            "scheduled",
            "preparing",
            "canceling",
            "waiting_for_callback",
        ]
    ] = Field(
        default_factory=list,
        max_length=13,
        description="Optional scope[] filter. Empty includes manual and all other states.",
    )
    trigger_api: Literal["bridges", "trigger_jobs"] = Field(
        default="bridges", description="Explicit trigger route; trigger_jobs needs GitLab 19.2+."
    )
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
        if self.operation in {"pipeline", "jobs", "pipeline_bridges"} and self.pipeline_id is None:
            raise ValueError("pipeline required")
        if self.operation == "trace" and self.job_id is None:
            raise ValueError("job required")
        if self.operation == "branch_jobs" and self.ref is None:
            raise ValueError("branch ref required")
        if self.operation in {"project_jobs", "branch_jobs"} and self.pipeline_id is not None:
            raise ValueError("use jobs for a pipeline-specific query")
        if self.operation == "project_jobs" and self.ref is not None:
            raise ValueError("use branch_jobs for a branch-specific query")
        if self.include_retried and self.operation != "jobs":
            raise ValueError("include_retried applies only to pipeline jobs")
        return self


class ZenTaoQuery(Query):
    operation: Literal[
        "projects",
        "project",
        "products",
        "product",
        "modules",
        "module_tree",
        "bugs",
        "bug",
        "attachments",
        "image",
    ]
    project_id: ResourceKey | None = None
    product_id: ResourceKey | None = None
    bug_id: ResourceKey | None = None
    module_type: Literal["bug", "story", "case", "product"] = Field(
        default="bug", description="Product module tree view; never a Project/Execution task root."
    )
    asset_index: int = Field(default=0, ge=0, le=9)
    search: str = Field(default="", max_length=100)

    @model_validator(mode="after")
    def required_arguments(self) -> "ZenTaoQuery":
        if self.operation == "project" and self.project_id is None:
            raise ValueError("project required")
        if self.operation == "module_tree" and (
            self.product_id is None or self.project_id is not None
        ):
            raise ValueError("module tree requires a Product ID, not a Project ID")
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
        "stack_service",
    ]
    endpoint_id: ResourceKey | None = None
    stack_id: ResourceKey | None = None
    service_id: ResourceKey | None = None
    namespace: ResourceKey | None = None
    service_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$",
        description="Exact Compose service key for stack_service; not a Swarm service name.",
    )

    @model_validator(mode="after")
    def required_arguments(self) -> "PortainerQuery":
        if self.operation in {
            "endpoint",
            "stack_file",
            "swarm_info",
            "services",
            "service",
            "stack_service",
        }:
            if self.endpoint_id is None:
                raise ValueError("endpoint required")
        if self.operation in {"stack", "stack_file", "stack_service"} and self.stack_id is None:
            raise ValueError("stack required")
        if self.operation == "service" and self.service_id is None:
            raise ValueError("service required")
        if self.operation == "stack_service" and self.service_name is None:
            raise ValueError("Compose service name required")
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
    "a Bug page (partial inventory), or module_tree (Product tree with local search/pagination), "
    "attachment metadata, or one authenticated MCP ImageContent. "
    "Search only within startup scope. No mapping. Instance must match configuration.",
    "gitlab_query": "GitLab scoped project/tree/ref file/commit/pipeline/jobs/trace facts. "
    "project_jobs and branch_jobs page project executions; branch ref filtering is local to "
    "each upstream page. Empty jobs do not prove no build; inspect pipeline_bridges separately. "
    "Manual jobs included unless a status filter excludes them; no downstream auto traversal. "
    "Explicit page/limit; file uses start_line and tail_lines, trace uses tail_lines. "
    "Secret files forbidden; Compose excludes environment values. No inference.",
    "portainer_query": "Portainer scoped read-only endpoint/stack/Stack File/Swarm/services facts. "
    "stack_service selects one exact Compose service server-side before output budgeting. "
    "Stack File returns parsed Compose facts only. Env/registry auth excluded. "
    "Status and replicas do not establish health, environment or deployment equivalence.",
}

# Publish descriptions for every input, including shared pagination controls.
for _model in FACT_INPUTS.values():
    for _name, _field in _model.model_fields.items():
        if not _field.description:
            _field.description = _name.replace("_", " ") + "; scoped read-only query parameter."
    _model.model_rebuild(force=True)

# Conditional argument requirements are published as well as checked at runtime.
_required = {
    "gitlab_query": {
        "project": ["project_id"],
        "tree": ["project_id", "ref"],
        "file": ["project_id", "ref", "path"],
        "commit": ["project_id", "ref"],
        "pipelines": ["project_id"],
        "pipeline": ["project_id", "pipeline_id"],
        "jobs": ["project_id", "pipeline_id"],
        "project_jobs": ["project_id"],
        "branch_jobs": ["project_id", "ref"],
        "pipeline_bridges": ["project_id", "pipeline_id"],
        "trace": ["project_id", "job_id"],
    },
    "zentao_query": {
        "project": ["project_id"],
        "product": ["product_id"],
        "module_tree": ["product_id"],
        "bug": ["bug_id"],
        "attachments": ["bug_id"],
        "image": ["bug_id"],
    },
    "portainer_query": {
        "endpoint": ["endpoint_id"],
        "stack": ["stack_id"],
        "stack_file": ["stack_id", "endpoint_id"],
        "swarm_info": ["endpoint_id"],
        "services": ["endpoint_id"],
        "service": ["endpoint_id", "service_id"],
        "stack_service": ["endpoint_id", "stack_id", "service_name"],
    },
}
for _tool, _operations in _required.items():
    _conditions: Any = []
    for _op, _fields in _operations.items():
        _conditions.append(
            {
                "if": {"properties": {"operation": {"const": _op}}, "required": ["operation"]},
                "then": {
                    "required": _fields,
                    "properties": {f: {"type": "string"} for f in _fields},
                },
            }
        )
    if _tool == "gitlab_query":
        _conditions.append(
            {
                "if": {
                    "properties": {"include_retried": {"const": True}},
                    "required": ["include_retried"],
                },
                "then": {"properties": {"operation": {"const": "jobs"}}},
            }
        )
        for _operation in ("project_jobs", "branch_jobs"):
            _conditions.append(
                {
                    "if": {
                        "properties": {"operation": {"const": _operation}},
                        "required": ["operation"],
                    },
                    "then": {
                        "properties": {
                            "pipeline_id": {"type": "null"},
                            **({"ref": {"type": "null"}} if _operation == "project_jobs" else {}),
                        }
                    },
                }
            )
    if _tool == "zentao_query":
        _conditions.append(
            {
                "if": {
                    "properties": {"operation": {"const": "module_tree"}},
                    "required": ["operation"],
                },
                "then": {"properties": {"project_id": {"type": "null"}}},
            }
        )
        _conditions.append(
            {
                "if": {
                    "properties": {"operation": {"enum": ["bugs", "modules"]}},
                    "required": ["operation"],
                },
                "then": {
                    "anyOf": [
                        {"required": [f], "properties": {f: {"type": "string"}}}
                        for f in ["project_id", "product_id"]
                    ]
                },
            }
        )
    FACT_INPUTS[_tool].model_config["json_schema_extra"] = {"allOf": _conditions}
    FACT_INPUTS[_tool].model_rebuild(force=True)
