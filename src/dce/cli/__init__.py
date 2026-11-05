import asyncio
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer
from alembic.util.exc import CommandError
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table
from sqlalchemy.exc import SQLAlchemyError

from dce.app.doctor import doctor as run_doctor
from dce.app.mapping import MappingService
from dce.app.services import DEFAULT_FIXTURE, AppServices
from dce.common.config import load_settings
from dce.common.errors import DceError, ErrorCode
from dce.common.output import encode, envelope
from dce.discovery.crawler import ScanScope

app = typer.Typer(no_args_is_help=True, help="Read-only DevOps Context Engine.")


@app.callback()
def main(
    ctx: typer.Context,
    config: Path | None = None,
    catalog: Path | None = None,
    output_budget: int | None = None,
) -> None:
    """Discover resources without changing platform state."""
    try:
        ctx.obj = load_settings(config, catalog_path=catalog, output_budget=output_budget)
    except DceError as exc:
        typer.echo(encode(envelope(error=exc)))
        raise typer.Exit(2) from None


@app.command("init")
def initialize(
    ctx: typer.Context,
    fixture: Path | None = None,
    no_ai: bool = False,
    legacy_mapping: bool = False,
    live: bool = False,
    read_only: bool = False,
    scope: str | None = None,
) -> None:
    def operation(service: AppServices) -> Any:
        service.require_live(live, read_only)
        if live:
            if scope is None:
                raise DceError(ErrorCode.INVALID_PAYLOAD, "Live init requires explicit JSON scope.")
            try:
                selected = ScanScope.model_validate_json(scope)
            except ValidationError:
                raise DceError(
                    ErrorCode.INVALID_PAYLOAD, "Scope must be a JSON ScanScope."
                ) from None
            return service.discover(selected, live=True, read_only=read_only)
        return service.initialize(fixture=fixture, no_ai=no_ai, legacy_mapping=legacy_mapping)

    perform(ctx, operation, fixture=fixture)


@app.command()
def discover(
    ctx: typer.Context,
    fixture: Path | None = None,
    live: bool = False,
    read_only: bool = False,
    gitlab_project: list[str] | None = None,
    gitlab_group: list[str] | None = None,
    zentao_project: list[str] | None = None,
    zentao_product: list[str] | None = None,
    portainer_stack: list[str] | None = None,
    portainer_endpoint: list[str] | None = None,
) -> None:
    def operation(service: AppServices) -> Any:
        service.require_live(live, read_only)
        if not live:
            return service.initialize(fixture=fixture)
        selected = ScanScope(
            gitlab_projects=gitlab_project or [],
            gitlab_groups=gitlab_group or [],
            zentao_projects=zentao_project or [],
            zentao_products=zentao_product or [],
            portainer_stacks=portainer_stack or [],
            portainer_endpoints=portainer_endpoint or [],
        )
        return service.discover(selected, live=live, read_only=read_only)

    perform(ctx, operation, fixture=fixture)


catalog_app = typer.Typer(no_args_is_help=True)
mapping_app = typer.Typer(no_args_is_help=True)
bug_app = typer.Typer(no_args_is_help=True)
pipeline_app = typer.Typer(no_args_is_help=True)
stack_app = typer.Typer(no_args_is_help=True)
trace_app = typer.Typer(no_args_is_help=True)
for name, group in (
    ("catalog", catalog_app),
    ("mapping", mapping_app),
    ("bug", bug_app),
    ("pipeline", pipeline_app),
    ("stack", stack_app),
    ("trace", trace_app),
):
    app.add_typer(group, name=name)


@catalog_app.command("list")
def catalog_list(
    ctx: typer.Context,
    kind: str | None = None,
    limit: int = 20,
    offset: int = 0,
    format: str = "json",
) -> None:
    perform(
        ctx,
        lambda service: service.catalog.list_entities(kind=kind, limit=limit, offset=offset),
        format=format,
    )


@catalog_app.command()
def anomalies(ctx: typer.Context, limit: int = 20, offset: int = 0, format: str = "json") -> None:
    perform(ctx, lambda service: service.catalog.anomalies(limit, offset), format=format)


@trace_app.command("service")
def trace_service(
    ctx: typer.Context, key: str, direction: str = "both", max_depth: int = 2, format: str = "json"
) -> None:
    perform(ctx, lambda service: service.service_trace(key, direction, max_depth), format=format)


@mapping_app.command()
def suggest(
    ctx: typer.Context, no_ai: bool = False, offline: bool = False, format: str = "json"
) -> None:
    perform(
        ctx,
        lambda service: asyncio.run(
            MappingService(service.catalog).suggest(no_ai=no_ai or offline)
        ),
        format=format,
    )


@mapping_app.command()
def review(
    ctx: typer.Context,
    edge_id: Annotated[str | None, typer.Argument()] = None,
    action: str | None = None,
    actor: str = "",
    reason: str = "",
    expected_version: int | None = None,
    confirm_environment: bool = False,
    format: str = "json",
) -> None:
    def operation(service: AppServices) -> Any:
        mappings = MappingService(service.catalog)
        if edge_id is None:
            if action:
                raise DceError(ErrorCode.INVALID_PAYLOAD, "Review action requires an edge ID.")
            candidates = service.catalog.list_edges(status="candidate", limit=10)
            unresolved = service.catalog.list_edges(status="unresolved", limit=10)
            return {
                "items": candidates["items"] + unresolved["items"],
                "more_available": candidates["more_available"] or unresolved["more_available"],
            }
        if action:
            if expected_version is None:
                raise DceError(
                    ErrorCode.REVIEW_REQUIRED, "Review requires --expected-version from preview."
                )
            mappings.review(
                edge_id,
                action=action,
                actor=actor,
                reason=reason,
                expected_version=expected_version,
                confirm_environment=confirm_environment,
            )
        return mappings.preview(edge_id)

    perform(ctx, operation, format=format)


@mapping_app.command()
def verify(ctx: typer.Context, format: str = "json") -> None:
    def operation(service: AppServices) -> Any:
        graph = service.catalog.read_graph()
        known = {item.id for item in graph.evidence}
        invalid = [edge.id for edge in graph.edges if not set(edge.evidence_ids) <= known]
        return {
            "status": "ok" if not invalid else "conflict",
            "invalid_edges": invalid,
            "external_status": "not_verified",
        }

    perform(ctx, operation, format=format)


@bug_app.command("context")
def bug_context(
    ctx: typer.Context,
    bug_id: str,
    fixture: Path | None = None,
    live: bool = False,
    read_only: bool = False,
    format: str = "json",
) -> None:
    perform(
        ctx,
        lambda service: service.bug_context(bug_id, live=live, read_only=read_only),
        fixture=fixture,
        format=format,
    )


@pipeline_app.command("diagnose")
def pipeline_diagnose(
    ctx: typer.Context,
    project: str,
    pipeline_id: str,
    fixture: Path | None = None,
    live: bool = False,
    read_only: bool = False,
    format: str = "json",
) -> None:
    perform(
        ctx,
        lambda service: service.pipeline_diagnose(
            project, pipeline_id, live=live, read_only=read_only
        ),
        fixture=fixture,
        format=format,
    )


@stack_app.command("inspect")
def stack_inspect(ctx: typer.Context, stack_id: str, format: str = "json") -> None:
    perform(ctx, lambda service: service.deployment_inspect(stack_id), format=format)


def perform(
    ctx: typer.Context,
    operation: Callable[[AppServices], Any],
    *,
    format: str = "json",
    fixture: Path | None = None,
) -> None:
    try:
        if format not in {"json", "table"}:
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Format must be json or table.")
        with AppServices(ctx.obj, fixture=fixture or DEFAULT_FIXTURE) as services:
            text = encode(envelope(operation(services)), ctx.obj.output_budget)
        if format == "json":
            typer.echo(text)
        else:
            table = Table("Field", "Value")
            for key, value in json.loads(text).items():
                table.add_row(key, json.dumps(value, ensure_ascii=False))
            Console(file=sys.stdout, color_system=None, width=100).print(table)
    except (DceError, ValidationError, OSError, SQLAlchemyError, CommandError) as exc:
        error = (
            exc
            if isinstance(exc, DceError)
            else DceError(
                ErrorCode.INVALID_PAYLOAD, "Operation failed validation or local storage access."
            )
        )
        typer.echo(encode(envelope(error=error)))
        raise typer.Exit(2) from None


@app.command()
def doctor(
    ctx: typer.Context,
    mock: bool = False,
    live: bool = False,
    read_only: bool = False,
    config: Annotated[Path | None, typer.Option(help="Explicit non-secret TOML config.")] = None,
) -> None:
    """Check platform capabilities; defaults to offline synthetic checks."""
    try:
        settings = load_settings(config) if config else ctx.obj
        if mock and live:
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Choose either mock or live.")
        if live:
            if not read_only:
                raise DceError(ErrorCode.PERMISSION_DENIED, "Live mode requires --read-only.")
        result = run_doctor(settings, mock=not live)
        typer.echo(encode(envelope(result), settings.output_budget))
        if any(platform["status"] != "ok" for platform in result["platforms"].values()):
            raise typer.Exit(2)
    except DceError as exc:
        typer.echo(encode(envelope(error=exc)))
        raise typer.Exit(2) from None


mcp_app = typer.Typer(no_args_is_help=True)
app.add_typer(mcp_app, name="mcp")


@mcp_app.command("serve")
def mcp_serve(
    ctx: typer.Context,
    transport: str = "stdio",
    fixture: Path | None = None,
    live: bool = False,
    read_only: bool = False,
    zentao_bug: list[str] | None = None,
    gitlab_project: list[str] | None = None,
    zentao_project: list[str] | None = None,
    zentao_product: list[str] | None = None,
    portainer_endpoint: list[str] | None = None,
    portainer_stack: list[str] | None = None,
) -> None:
    from dce.app.facts import FactScope
    from dce.mcp.server import serve

    try:
        if transport != "stdio":
            raise DceError(ErrorCode.INVALID_PAYLOAD, "V1 MCP supports stdio only.")
        with AppServices(ctx.obj, fixture=fixture or DEFAULT_FIXTURE) as services:
            serve(
                services,
                live=live,
                read_only=read_only,
                allowed_bug_ids=set(zentao_bug or []),
                allowed_gitlab_projects=set(gitlab_project or []),
                fact_scope=FactScope(
                    gitlab_projects=set(gitlab_project or []),
                    zentao_projects=set(zentao_project or []),
                    zentao_products=set(zentao_product or []),
                    zentao_bugs=set(zentao_bug or []),
                    portainer_endpoints=set(portainer_endpoint or []),
                    portainer_stacks=set(portainer_stack or []),
                ),
            )
    except (DceError, OSError, SQLAlchemyError) as exc:
        error = (
            exc
            if isinstance(exc, DceError)
            else DceError(ErrorCode.INVALID_PAYLOAD, "MCP initialization failed.")
        )
        typer.echo(encode(envelope(error=error)), err=True)
        raise typer.Exit(2) from None


project_app = typer.Typer(
    no_args_is_help=True, help="Project contracts; never writes workspace files."
)
app.add_typer(project_app, name="project")


@project_app.command("schema")
def project_schema() -> None:
    from dce.project.model import ProjectContext

    typer.echo(json.dumps(ProjectContext.model_json_schema(by_alias=True), ensure_ascii=False))


@project_app.command("template")
def project_template(workspace_id: str = "business-project", schema_version: int = 1) -> None:
    from dce.project.context import template

    try:
        typer.echo(json.dumps(template(workspace_id, schema_version), ensure_ascii=False, indent=2))
    except ValidationError:
        typer.echo(
            encode(
                envelope(error=DceError(ErrorCode.INVALID_PAYLOAD, "Invalid workspace identity."))
            )
        )
        raise typer.Exit(2) from None


@project_app.command("migrate")
def project_migrate(
    workspace: Path, workspace_id: str | None = None, target_version: int = 2
) -> None:
    """Print a lossless v2 candidate to stdout; never changes the workspace file."""
    from dce.project.context import load_project, migrate

    try:
        result = migrate(
            load_project(workspace, workspace_id=workspace_id), target_version=target_version
        )
        typer.echo(
            json.dumps(result.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        )
    except (DceError, OSError, ValueError):
        typer.echo(
            encode(
                envelope(
                    error=DceError(ErrorCode.INVALID_PAYLOAD, "Project migration preview failed.")
                )
            )
        )
        raise typer.Exit(2) from None


@project_app.command("validate")
def project_validate(workspace: Path, workspace_id: str | None = None) -> None:
    from dce.project.context import load_project

    try:
        project = load_project(workspace, workspace_id=workspace_id)
        typer.echo(
            encode(
                envelope(
                    {
                        "valid": True,
                        "schema_version": project.schema_version,
                        "relationship_count": len(project.relationships),
                    }
                )
            )
        )
    except (DceError, OSError, ValueError) as exc:
        error = (
            exc
            if isinstance(exc, DceError)
            else DceError(ErrorCode.INVALID_PAYLOAD, "Project context cannot be read safely.")
        )
        typer.echo(encode(envelope(error=error)))
        raise typer.Exit(2) from None


@catalog_app.command("backup")
def catalog_backup(ctx: typer.Context) -> None:
    """Create a private SQLite backup; does not export to any business workspace."""
    perform(ctx, lambda service: service.catalog.backup())


@catalog_app.command("status")
def catalog_role(ctx: typer.Context) -> None:
    perform(ctx, lambda service: service.catalog.role())
