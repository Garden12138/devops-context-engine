"""Command-line entry points for DCE workflows."""

import json
import math
import time
from difflib import unified_diff
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Any

import typer

from dce import __version__
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
def deploy(ctx: typer.Context, run: Annotated[str, typer.Option("--run")]) -> None:
    emit(ctx, 'service_deploy', run_id=run)


@app.command("deploy-status")
def deploy_status(
    ctx: typer.Context, run: Annotated[str, typer.Option("--run")],
    wait: Annotated[int, typer.Option(min=0)] = 0,
    logs: Annotated[int, typer.Option(min=0, max=300)] = 0,
) -> None:
    deadline = time.monotonic() + wait
    while True:
        remaining = max(0, math.ceil(deadline - time.monotonic()))
        result = ctx.obj['runtime'].call('service_status', run_id=run,
                                        wait_seconds=min(45, remaining), logs_tail=logs)
        if not result['ok'] or time.monotonic() >= deadline:
            break
        services = result['data']['services']
        if (any(s['verdict'] == 'failed' for s in services)
                or not any(s['verdict'] == 'updating' for s in services)):
            break
    render(ctx, result)


@run_app.command("update")
def run_update(
    ctx: typer.Context,
    run: Annotated[str, typer.Option("--run")],
    bug: Annotated[int | None, typer.Option("--bug")] = None,
    result: Annotated[str | None, typer.Option("--result")] = None,
    notes: Annotated[str | None, typer.Option("--notes")] = None,
    evidence: Annotated[list[str] | None, typer.Option("--evidence")] = None,
    file: Annotated[str | None, typer.Option("--file")] = None,
    commit: Annotated[str | None, typer.Option("--commit")] = None,
    note: Annotated[str | None, typer.Option("--note")] = None,
) -> None:
    verification = None
    if any(value is not None for value in (bug, result, notes, evidence)):
        verification = {'bug_id': bug, 'result': result, 'notes': notes or '',
                        'evidence': evidence or []}
    record = None if file is None and commit is None else {'file': file, 'commit': commit}
    emit(ctx, 'run_update', run_id=run, verification=verification, record=record, note=note)


@app.command()
def resolve(
    ctx: typer.Context,
    run: Annotated[str, typer.Option("--run")],
    bug: Annotated[list[int] | None, typer.Option("--bug")] = None,
    comment: Annotated[str | None, typer.Option("--comment")] = None,
) -> None:
    emit(ctx, 'bug_resolve', run_id=run, bug_ids=bug, comment=comment)


@app.command("install-skill")
def install_skill(
    dest: Annotated[Path, typer.Option("--dest", file_okay=False)],
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    name = 'dce-bugfix-loop'
    source = files('dce').joinpath('_skills', name)
    if not source.is_dir():
        source = Path(__file__).resolve().parents[2] / 'skills' / name
    target = dest / name
    changes: dict[Path, bytes] = {}
    try:
        if target.is_symlink() or (target.exists() and not target.is_dir()):
            raise OSError(f'{target} 必须是普通目录。')
        exists = target.is_dir()
        for filename in ('SKILL.md', 'record-template.md'):
            path = target / filename
            if path.is_symlink() or (path.exists() and not path.is_file()):
                raise OSError(f'{path} 必须是普通文件。')
            previous = path.read_bytes() if path.is_file() else b''
            content = source.joinpath(filename).read_bytes()
            if previous == content:
                continue
            changes[path] = content
            if exists:
                before = previous.decode('utf-8', errors='replace').splitlines(keepends=True)
                after = content.decode('utf-8').splitlines(keepends=True)
                typer.echo(''.join(unified_diff(before, after, f'现有/{filename}',
                                                f'随附/{filename}')), nl=False)
        if not changes:
            typer.echo(f'Skill 已是当前版本：{target}')
            return
        if exists and not force:
            typer.echo('核对以上差异后，加 --force 安装随附版本。', err=True)
            raise typer.Exit(1)
        target.mkdir(parents=True, exist_ok=True)
        for path, content in changes.items():
            path.write_bytes(content)
    except OSError as exc:
        typer.echo(f'Skill 安装到 {target} 失败：{exc} 请核对源文件及目标权限。', err=True)
        raise typer.Exit(1) from None
    typer.echo(f'Skill 已安装：{target}')


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
