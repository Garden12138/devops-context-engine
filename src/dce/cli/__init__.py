from pathlib import Path
from typing import Annotated

import typer

from dce.app.doctor import mock_doctor
from dce.common.config import load_settings
from dce.common.errors import DceError, ErrorCode
from dce.common.output import encode, envelope

app = typer.Typer(no_args_is_help=True, help="Read-only DevOps Context Engine.")


@app.callback()
def main() -> None:
    """Discover resources without changing platform state."""


@app.command()
def doctor(
    mock: bool = False,
    live: bool = False,
    read_only: bool = False,
    config: Annotated[Path | None, typer.Option(help="Explicit non-secret TOML config.")] = None,
) -> None:
    """Check platform capabilities; defaults to offline synthetic checks."""
    try:
        settings = load_settings(config)
        if mock and live:
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Choose either mock or live.")
        if live:
            if not read_only:
                raise DceError(ErrorCode.PERMISSION_DENIED, "Live mode requires --read-only.")
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Live probes are not implemented yet.")
        typer.echo(encode(envelope(mock_doctor()), settings.output_budget))
    except DceError as exc:
        typer.echo(encode(envelope(error=exc)))
        raise typer.Exit(2) from None
