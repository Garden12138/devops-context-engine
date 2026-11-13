import asyncio
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dce.app.services import AppServices
from dce.common.config import Settings
from dce.common.errors import DceError
from dce.mcp.server import McpApplication


@pytest.mark.parametrize(
    "values,endpoints,stacks,code",
    [
        ([], [], [], None),
        (["1:7"], ["1"], ["7"], None),
        (["1:7", "1:7"], ["1"], ["7"], None),
        (["1:7"], [], ["7"], "PERMISSION_DENIED"),
        (["1:7"], ["1"], [], "PERMISSION_DENIED"),
        (["1:7:8"], ["1"], ["7"], "INVALID_PAYLOAD"),
        (["x:7"], ["x"], ["7"], "INVALID_PAYLOAD"),
    ],
)
def test_log_grant_parser_shared_by_both_launchers(values, endpoints, stacks, code):
    from dce.mcp.startup import parse_log_scopes

    if code:
        with pytest.raises(DceError) as e:
            parse_log_scopes(values, endpoints, stacks)
        assert e.value.code == code
    else:
        assert parse_log_scopes(values, endpoints, stacks) == ({("1", "7")} if values else set())


def test_explicit_launcher_missing_required_platform_fails_before_stdio_and_catalog(tmp_path):
    config = tmp_path / "connection.toml"
    config.write_text('[zentao]\nbase_url="https://example.invalid"\n')
    credentials = tmp_path / ".env"
    credentials.write_text("ZEN_USER=fixture-user\nZEN_PASSWORD=fixture-password\n")
    credentials.chmod(0o600)
    catalog = tmp_path / "not-created.sqlite3"
    result = subprocess.run(
        [
            str(Path(".venv/bin/python").absolute()),
            str(Path("scripts/serve_dce_local.py").resolve()),
            "--config",
            str(config),
            "--credentials-file",
            str(credentials),
            "--catalog",
            str(catalog),
            "--live",
            "--read-only",
            "--require-platform",
            "gitlab",
        ],
        cwd="/",
        env={k: v for k, v in os.environ.items() if not k.startswith("DCE_")},
        input="",
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 2 and result.stdout == "" and not catalog.exists()
    error = json.loads(result.stderr)["error"]
    assert error["code"] == "AUTH_FAILED" and "configuration missing for gitlab" in error["message"]
    for secret in ["fixture-password", "fixture-user", "example.invalid", str(credentials)]:
        assert secret not in result.stderr


def test_invalid_log_grant_rejected_before_credential_file_open(tmp_path):
    result = subprocess.run(
        [
            str(Path(".venv/bin/python").absolute()),
            str(Path("scripts/serve_dce_local.py").resolve()),
            "--config",
            str(tmp_path / "absent.toml"),
            "--credentials-file",
            str(tmp_path / "absent.env"),
            "--catalog",
            str(tmp_path / "absent.sqlite3"),
            "--live",
            "--read-only",
            "--portainer-log-scope",
            "1:7",
        ],
        input="",
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 2 and result.stdout == ""
    assert json.loads(result.stderr)["error"]["code"] == "PERMISSION_DENIED"
    assert not (tmp_path / "absent.sqlite3").exists()


def test_runtime_identity_connects_schema_and_call_without_private_configuration(tmp_path, caplog):
    caplog.set_level("INFO", logger="dce.audit")
    with AppServices(Settings(catalog_path=tmp_path / "cache.sqlite3")) as services:
        app = McpApplication(services, live=True, read_only=True)
        with caplog.at_level("INFO", logger="dce.audit"):
            tools = asyncio.run(app.list_tools())
            call = asyncio.run(
                app.call_tool(
                    "zentao_query",
                    {
                        "instance": "fixture",
                        "operation": "bug",
                        "bug_id": "fixture-bug",
                    },
                )
            )
        assert len(tools) == 9
        runtime = tools[0].meta["dce"]["runtime"]
        assert all(t.meta["dce"]["runtime"] == runtime for t in tools)
        assert call.meta["dce"]["runtime"] == runtime
        assert runtime["server_version"] == "1.1.1" and runtime["process_id"] == os.getpid()
        assert runtime["configured_platforms"] == []
        schemas = {t.name: t.inputSchema for t in tools}
        assert (
            runtime["schema_sha256"]
            == hashlib.sha256(json.dumps(schemas, sort_keys=True).encode()).hexdigest()
        )
        portainer = next(t for t in tools if t.name == "portainer_query")
        assert "service_logs" in portainer.inputSchema["properties"]["operation"]["enum"]
        assert "service_logs" in portainer.description
        assert f"pid={os.getpid()}" in caplog.text and "fixture-bug" not in caplog.text
        assert f"request_id={call.structuredContent['request_id']}" in caplog.text
        assert "schema=" in caplog.text and "mcp_start" in caplog.text


def test_optional_runtime_never_evicts_a_result_that_fits_without_diagnostics(tmp_path):
    with AppServices(Settings(catalog_path=tmp_path / "cache.sqlite3")) as services:
        services.initialize()
        app = McpApplication(services)
        original = asyncio.run(app.call_tool("discovery_status", {}))
        assert (
            original.structuredContent["data"] is not None
            and not original.structuredContent["truncated"]
        )
        required = len(
            original.model_copy(update={"meta": None})
            .model_dump_json(
                by_alias=True,
                exclude_none=True,
            )
            .encode()
        )
        complete = len(original.model_dump_json(by_alias=True, exclude_none=True).encode())
        services.settings.output_budget = (required + complete) // 2
        assert required < services.settings.output_budget < complete
        bounded = asyncio.run(app.call_tool("discovery_status", {}))
        assert bounded.meta is None
        assert (
            bounded.structuredContent["data"] is not None
            and not bounded.structuredContent["truncated"]
        )
        assert (
            len(bounded.model_dump_json(by_alias=True, exclude_none=True).encode())
            <= services.settings.output_budget
        )


def test_cached_instructions_stable_across_processes_and_runtime_is_not_persisted(tmp_path):
    config = tmp_path / "connections.toml"
    config.write_text('[gitlab]\ninstance_id="fixture"\nbase_url="https://example.invalid"\n')
    credentials = tmp_path / ".env"
    credentials.write_text("GITLAB_TOKEN=fixture-token\n")
    credentials.chmod(0o600)
    parameters = StdioServerParameters(
        command=str(Path(".venv/bin/python").absolute()),
        cwd="/",
        args=[
            str(Path("scripts/serve_dce_local.py").resolve()),
            "--config",
            str(config),
            "--credentials-file",
            str(credentials),
            "--catalog",
            str(tmp_path / "shared.sqlite3"),
            "--live",
            "--read-only",
            "--require-platform",
            "gitlab",
        ],
        env={k: v for k, v in os.environ.items() if not k.startswith("DCE_")},
    )

    async def connection(index):
        stderr = tmp_path / f"stderr-{index}.txt"
        with stderr.open("w") as err:
            async with stdio_client(parameters, errlog=err) as (read, write):
                async with ClientSession(read, write) as client:
                    info = await client.initialize()
                    tools = (await client.list_tools()).tools
                    result = await client.call_tool("discovery_status", {})
                    assert info.serverInfo.version == "1.1.1" and len(tools) == 9
                    runtime = result.meta["dce"]["runtime"]
                    assert not result.isError
                    assert all(t.meta["dce"]["runtime"] == runtime for t in tools)
                    assert runtime["configured_platforms"] == ["gitlab"]
                    assert "Runtime pid=" not in info.instructions
                    assert f"sha256={runtime['schema_sha256']}" in info.instructions
                    request_id = result.structuredContent["request_id"]
                    schemas = {t.name: t.inputSchema for t in tools}
        audit = stderr.read_text()
        assert f"pid={runtime['process_id']} request_id={request_id}" in audit
        assert "fixture-token" not in audit
        return info.instructions, runtime, schemas, request_id

    first = asyncio.run(connection(1))
    second = asyncio.run(connection(2))
    assert first[0] == second[0] and first[2] == second[2]
    assert first[1]["schema_sha256"] == second[1]["schema_sha256"]
    assert first[1]["process_id"] != second[1]["process_id"]
    assert first[3] != second[3]
