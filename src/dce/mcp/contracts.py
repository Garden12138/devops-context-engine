"""Published MCP contracts; free-form metadata is limited to explicit containers."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

from dce.common.errors import ErrorCode

ResourceKey = Annotated[
    str,
    Field(
        min_length=1,
        max_length=250,
        json_schema_extra={
            "pattern": r"^(?!.*\.\.)(?!.*://)[\w./:-]+$",
        },
    ),
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class BugInput(Input):
    bug_id: ResourceKey = Field(description="ZenTao Bug ID, within the session Bug allowlist.")
    include_assets: bool = Field(
        default=False,
        description="Download authenticated Bug images only if authorized; default off.",
    )


class ProjectInput(Input):
    source: ResourceKey = Field(
        description="Catalog source-instance ID, not a platform/project ID."
    )
    project_key: ResourceKey = Field(
        description="Catalog entity ID or external GitLab repository / ZenTao business-project ID."
    )
    depth: int = Field(default=2, ge=0, le=5, description="Catalog graph hops, 0 through 5.")


class TraceInput(Input):
    service_key: ResourceKey = Field(description="Catalog service entity ID or unique external ID.")
    direction: Literal["in", "out", "both"] = Field(
        default="both", description="Traverse incoming, outgoing, or both Catalog edge directions."
    )
    max_depth: int = Field(
        default=2, ge=0, le=5, description="Maximum Catalog graph hops, 0 through 5."
    )


class PipelineInput(Input):
    project_key: ResourceKey = Field(
        description="GitLab project ID in the session Project allowlist."
    )
    pipeline_id: ResourceKey = Field(description="GitLab pipeline ID belonging to that project.")


class DeploymentInput(Input):
    model_config = ConfigDict(
        json_schema_extra={
            "oneOf": [
                {
                    "required": ["stack_key"],
                    "properties": {
                        "stack_key": {"type": "string"},
                        "service_key": {"type": "null"},
                    },
                },
                {
                    "required": ["service_key"],
                    "properties": {
                        "service_key": {"type": "string"},
                        "stack_key": {"type": "null"},
                    },
                },
            ]
        }
    )
    stack_key: ResourceKey | None = Field(
        default=None,
        description="Catalog stack entity ID or unique external ID; choose exactly one key.",
    )
    service_key: ResourceKey | None = Field(
        default=None,
        description="Catalog service entity ID or unique external ID; choose exactly one key.",
    )

    @model_validator(mode="after")
    def one_resource(self) -> "DeploymentInput":
        if (self.stack_key is None) == (self.service_key is None):
            raise ValueError("provide exactly one resource key")
        return self


class DiscoveryInput(Input):
    scan_id: ResourceKey | None = Field(
        default=None,
        description="Local scan-run ID; omit to read up to 20 recent runs. Does not scan.",
    )


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CatalogEntity(Output):
    id: str
    source_instance: str
    kind: str
    external_id: str
    attributes: dict[str, Any] = Field(
        description="Redacted platform-specific metadata; extensible keys."
    )
    version: int
    deleted: bool
    first_seen: str
    last_verified: str = Field(
        description="Saved entity observation/verification time, not current health."
    )


class CatalogEdge(Output):
    id: str
    source_id: str
    target_id: str
    relation: str
    observed_status: str
    status: str = Field(
        description="Observed/candidate/unresolved or human-reviewed state; never auto-confirm."
    )
    evidence_ids: list[str]
    confidence: float
    version: int
    human_decision: str | None
    conflict: bool
    stale: bool
    deleted: bool
    valid_from: str
    last_verified: str
    valid_until: str | None


class TraceData(Output):
    resource: str = Field(description="Starting Catalog entity ID; not a nested resource object.")
    edges: list[CatalogEdge]
    more_available: bool
    direction: Literal["in", "out", "both"]
    max_depth: int


class ProjectData(Output):
    project: CatalogEntity
    trace: TraceData


class AssetReference(Output):
    asset_id: str
    mime: str
    sha256: str
    resource_uri: str = Field(
        description="Session-authorized dce://assets/ reference; no local/upstream path."
    )


class ModuleMapping(Output):
    module_id: str
    path: str | None
    status: str
    confidence: float
    evidence_ids: list[str]
    mapping_id: str


class BugData(Output):
    bug_id: str
    source_instance: str
    title: str
    steps: str
    project_id: str | int | None
    product_id: str | int | None
    assets: list[AssetReference]
    modules: list[ModuleMapping] = Field(
        description="Catalog module mappings; may be empty or candidate."
    )
    evidence_ids: list[str]
    warnings: list[str]
    uncertainties: list[str]
    next_action: str
    truncated: bool
    verification: Literal["live_read_only", "synthetic"]


class FailedJob(Output):
    job_id: str | int
    stage: str | None
    status: Literal["failed"]
    root_cause: str
    secondary: list[str]
    trace_excerpt: list[str] = Field(
        description="At most the last 100 redacted trace lines; not a full log."
    )


class PipelineData(Output):
    project_id: str
    pipeline_id: str
    status: str
    default_branch: str | None
    failures: list[FailedJob]
    next_action: str


class SnapshotSummary(Output):
    snapshot_id: str
    kind: str
    version: str
    observed_at: str = Field(
        description="Saved snapshot acquisition time; does not imply a fresh API read."
    )
    service_count: int
    incomplete: bool


class StackData(Output):
    stack: CatalogEntity
    snapshots: list[SnapshotSummary]
    health: Literal["unknown"]
    environment: Literal["unresolved"]
    version_match: Literal["not_verified"]
    trace: TraceData


class ServiceData(Output):
    service: CatalogEntity
    trace: TraceData
    health: Literal["unknown"]


class DeploymentData(RootModel[StackData | ServiceData]):
    """Stack summary, or an orphan service when no runs_service edge is saved."""


class ScanItem(Output):
    id: str
    scope: str
    status: str
    started_at: str
    finished_at: str | None
    error_code: str | None
    summary: dict[str, Any] = Field(
        description="Saved scan-specific counts/checkpoints; extensible keys."
    )
    anomaly_count: int


class DiscoveryData(Output):
    items: list[ScanItem]
    more_available: bool
    pending_reviews: int


class ErrorData(Output):
    code: ErrorCode
    error_code: ErrorCode
    message: str = Field(
        description="Fixed safe diagnostic; never raw validation/upstream content."
    )
    retryable: bool


INPUTS: dict[str, type[Input]] = {
    "bug_context": BugInput,
    "project_context": ProjectInput,
    "service_trace": TraceInput,
    "pipeline_diagnose": PipelineInput,
    "deployment_inspect": DeploymentInput,
    "discovery_status": DiscoveryInput,
}
OUTPUTS: dict[str, type[BaseModel]] = {
    "bug_context": BugData,
    "project_context": ProjectData,
    "service_trace": TraceData,
    "pipeline_diagnose": PipelineData,
    "deployment_inspect": DeploymentData,
    "discovery_status": DiscoveryData,
}
DESCRIPTIONS = {
    "bug_context": "ZenTao (禅道): read Bug title/steps and Catalog module-mapping evidence; "
    "optional authenticated images return session asset references. Live mode never uses fixtures.",
    "project_context": "Read saved Catalog GitLab repository or ZenTao business-project context "
    "and evidence graph. Uses a source-instance ID. No platform fetch or refresh.",
    "service_trace": "Trace saved Catalog relations across GitLab code/build/images and "
    "Portainer/Docker Swarm services. Preserve candidate/stale states. No platform fetch.",
    "pipeline_diagnose": "GitLab: read pipeline/jobs/default branch and bounded redacted job "
    "trace diagnostics. Does not trigger CI. Live mode never uses fixtures.",
    "deployment_inspect": "Read saved Portainer/Docker Swarm stack/service Catalog snapshots. "
    "No live Portainer fetch or live Swarm comparison; health=unknown, environment=unresolved, "
    "version_match=not_verified. Snapshot observed_at records acquisition time.",
    "discovery_status": "Read local Catalog scan runs, anomaly counts and pending mapping reviews. "
    "No discovery scan, platform fetch, mapping approval or deployment is performed.",
}


def output_schema(name: str, model: type[BaseModel] | None = None) -> dict[str, Any]:
    data = (model or OUTPUTS[name]).model_json_schema()
    error = ErrorData.model_json_schema()
    definitions = {**data.pop("$defs", {}), **error.pop("$defs", {})}
    definitions.update(ToolData=data, ToolError=error)
    strings = {"type": "array", "items": {"type": "string"}}
    properties = {
        "schema_version": {"type": "string", "const": "1.0"},
        "request_id": {"type": "string"},
        "status": {"type": "string", "enum": ["ok", "error"]},
        "data": {"anyOf": [{"$ref": "#/$defs/ToolData"}, {"type": "null"}]},
        "evidence": strings,
        "warnings": strings,
        "uncertainties": strings,
        "truncated": {"type": "boolean"},
        "omissions": strings,
        "next_action": {"type": ["string", "null"]},
        "snapshot_at": {
            "type": "string",
            "description": "Response creation time (legacy name), NOT platform acquisition time. "
            "Use last_verified, scan finished_at or snapshot observed_at for evidence freshness.",
        },
        "error": {"$ref": "#/$defs/ToolError"},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "$defs": definitions,
        "properties": properties,
        "required": [k for k in properties if k != "error"],
        "oneOf": [
            {
                "properties": {"status": {"const": "ok"}},
                "not": {"required": ["error"]},
                "anyOf": [
                    {"properties": {"data": {"$ref": "#/$defs/ToolData"}}},
                    {"properties": {"data": {"type": "null"}, "truncated": {"const": True}}},
                ],
            },
            {
                "required": ["error"],
                "properties": {
                    "status": {"const": "error"},
                    "data": (
                        {
                            "anyOf": [
                                {"type": "null"},
                                {
                                    "allOf": [
                                        {"$ref": "#/$defs/ToolData"},
                                        {
                                            "properties": {
                                                "source": {
                                                    "properties": {
                                                        "operation": {"const": "service_logs"}
                                                    }
                                                }
                                            }
                                        },
                                    ]
                                },
                            ]
                        }
                        if name == "portainer_query"
                        else {"type": "null"}
                    ),
                },
            },
        ],
    }
