"""Reject incompatible startup settings before credentials or platform access."""

import os
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dce.cli import app


@pytest.mark.parametrize(
    "flags",
    [
        ["--mode", "project", "--live"],
        ["--mode", "project", "--live", "--read-only", "--zentao-bug", "seed"],
        ["--mode", "project", "--live", "--read-only", "--transport", "http"],
        ["--mode", "unknown"],
    ],
)
def test_cli_mode_validation_before_service_creation(tmp_path, flags):
    result = CliRunner().invoke(
        app, ["--catalog", str(tmp_path / "cache.sqlite3"), "mcp", "serve", *flags]
    )
    assert result.exit_code == 2 and "INVALID_PAYLOAD" in result.stderr
    assert not (tmp_path / "cache.sqlite3").exists()


def test_explicit_launcher_rejects_mixed_scopes_before_opening_credentials(tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("DCE_")}
    result = subprocess.run(
        [
            str(Path(".venv/bin/python").absolute()),
            "scripts/serve_dce_local.py",
            "--mode",
            "project",
            "--live",
            "--read-only",
            "--config",
            str(tmp_path / "missing.toml"),
            "--credentials-file",
            str(tmp_path / "missing.env"),
            "--zentao-bug",
            "seed",
        ],
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2 and result.stdout == ""
    assert "cannot mix" in result.stderr and "INVALID_PAYLOAD" in result.stderr
    assert not list(tmp_path.iterdir())
