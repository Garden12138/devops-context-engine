"""CLI entry points; milestones M1–M5 supply their implementations."""

import json
import math
import time
from pathlib import Path
from typing import Annotated, Any, NoReturn

import typer

from dce import __version__
from dce.errors import DceError, ErrorCode
from dce.loop.bugs import ImageBytes, save_image_files
from dce.mcp_server import Runtime, create_server
from dce.output import invoke

app = typer.Typer(no_args_is_help=True)
setup_app = typer.Typer(no_args_is_help=True)
bug_app = typer.Typer(no_args_is_help=True)
run_app = typer.Typer(no_args_is_help=True)
app.add_typer(setup_app, name="setup")
app.add_typer(bug_app, name="bug")
app.add_typer(run_app, name="run")


def pending(tool: str) -> NoReturn:
    error = DceError(
        ErrorCode.NOT_IMPLEMENTED,
        f"{tool} is scheduled for a later milestone.",
        "See docs/v2/05-实施计划.md for implementation order.",
    )
    typer.echo(json.dumps({"ok": False, "error": error.as_dict()}, ensure_ascii=False))
    raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", is_eager=True)] = False,
    connections: Annotated[Path | None, typer.Option(envvar="DCE_CONNECTIONS")] = None,
    credentials: Annotated[Path | None, typer.Option(envvar="DCE_CREDENTIALS")] = None,
    workspace: Annotated[Path | None, typer.Option(envvar="DCE_WORKSPACE")] = None,
    pretty: Annotated[bool, typer.Option("--pretty")] = False,
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    ctx.obj = {'runtime': Runtime(connections, credentials, workspace), 'pretty': pretty}


def emit(ctx: typer.Context, tool: str, **arguments: object) -> None:
    result = ctx.obj['runtime'].call(tool, **arguments)
    render(ctx, result)


def render(ctx: typer.Context, result: dict[str, Any]) -> None:
    typer.echo(result.get('summary', json.dumps(result, ensure_ascii=False))
               if ctx.obj['pretty'] else json.dumps(result, ensure_ascii=False))
    if not result['ok'] or result.get('data', {}).get('passed') is False:
        raise typer.Exit(1)


@setup_app.command("scan")
def setup_scan(ctx: typer.Context) -> None:
    emit(ctx, 'project_setup', action='scan')


@setup_app.command("check")
def setup_check(ctx: typer.Context) -> None:
    emit(ctx, 'project_setup', action='check')


@app.command()
def status(ctx: typer.Context, run: Annotated[str | None, typer.Option("--run")] = None) -> None:
    emit(ctx, 'dce_status', run_id=run)


@bug_app.command("list")
def bug_list(
    ctx: typer.Context,
    all_bugs: Annotated[bool, typer.Option("--all")] = False,
    status: str = "active",
) -> None:
    emit(ctx, 'bug_list', scope='all' if all_bugs else 'mine', status=status)


@bug_app.command("show")
def bug_show(ctx: typer.Context, bug_id: int, save_images: Path | None = None) -> None:
    runtime: Runtime = ctx.obj['runtime']

    def operation() -> dict[str, Any]:
        images: list[ImageBytes] = []
        payload = runtime.call('bug_get', bug_id=bug_id, images=save_images is not None,
                               image_sink=images)
        if payload['ok'] and save_images is not None:
            save_image_files(save_images, images)
        return payload

    render(ctx, invoke(operation, lambda: runtime.settings.secrets() if runtime.settings else ()))


@app.command()
def plan(
    ctx: typer.Context,
    bugs: list[int],
    repo: Annotated[list[str] | None, typer.Option("--repo")] = None,
    run: Annotated[str | None, typer.Option("--run")] = None,
) -> None:
    emit(ctx, 'deploy_plan', bug_ids=bugs, repos=repo, run_id=run)


@app.command()
def merge(
    ctx: typer.Context,
    run: Annotated[str, typer.Option("--run")],
    yes: Annotated[bool, typer.Option("--yes")] = False,
) -> None:
    emit(ctx, 'merge_to_test', run_id=run, approved_by_user=yes)


@app.command()
def build(
    ctx: typer.Context,
    run: Annotated[str, typer.Option("--run")],
    retry_failed: Annotated[bool, typer.Option("--retry-failed")] = False,
) -> None:
    emit(ctx, 'ci_build', run_id=run, retry_failed=retry_failed)


@app.command("build-status")
def build_status(ctx: typer.Context, run: Annotated[str, typer.Option("--run")],
                 wait: Annotated[int, typer.Option(min=0)] = 0) -> None:
    deadline = time.monotonic() + wait
    while True:
        remaining = max(0, math.ceil(deadline - time.monotonic()))
        result = ctx.obj['runtime'].call('ci_status', run_id=run, wait_seconds=min(45, remaining))
        if (not result['ok'] or result['data']['overall'] != 'building'
                or time.monotonic() >= deadline):
            break
    render(ctx, result)


@app.command()
def deploy(run: Annotated[str, typer.Option("--run")]) -> None:
    pending("service_deploy")


@app.command("deploy-status")
def deploy_status(
    run: Annotated[str, typer.Option("--run")], wait: int = 0, logs: int = 0
) -> None:
    pending("service_status")


@run_app.command("update")
def run_update(run: Annotated[str, typer.Option("--run")]) -> None:
    pending("run_update")


@app.command()
def resolve(
    run: Annotated[str, typer.Option("--run")],
    bug: Annotated[list[int] | None, typer.Option("--bug")] = None,
) -> None:
    pending("bug_resolve")


@app.command()
def mcp(
    ctx: typer.Context,
    connections: Annotated[Path | None, typer.Option(envvar="DCE_CONNECTIONS")] = None,
    credentials: Annotated[Path | None, typer.Option(envvar="DCE_CREDENTIALS")] = None,
    workspace: Annotated[Path | None, typer.Option(envvar="DCE_WORKSPACE")] = None,
) -> None:
    runtime = ctx.obj['runtime']
    create_server(connections or runtime.connections, credentials or runtime.credentials,
                  workspace or runtime.workspace).run(transport='stdio')
