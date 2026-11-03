"""Exercise catalog-only MCP over stdio without printing private tool payloads."""

import argparse
import asyncio
import json
import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dce.catalog.db import Catalog

TOOLS = {
    "bug_context",
    "project_context",
    "service_trace",
    "pipeline_diagnose",
    "deployment_inspect",
    "discovery_status",
}


class CheckFailure(Exception):
    """A fixed, public diagnostic that contains no tool or upstream content."""


async def check(catalog_path: Path) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    executable = root / ".venv/bin/dce"
    if not catalog_path.is_file() or not executable.is_file():
        raise CheckFailure("Catalog and installed DCE must exist.")
    catalog = Catalog(catalog_path)
    try:
        before = catalog.counts()
        resources = {
            kind: catalog.list_entities(kind=kind, limit=1)["items"]
            for kind in ("repository", "service", "stack")
        }
        if not all(resources.values()):
            raise CheckFailure("Catalog must contain repository, service and stack metadata.")
        repo, service, stack = (resources[k][0] for k in ("repository", "service", "stack"))
        requests = [
            ("project_context", {"source": repo["source_instance"], "project_key": repo["id"]}),
            ("service_trace", {"service_key": service["id"]}),
            ("deployment_inspect", {"stack_key": stack["id"]}),
            ("discovery_status", {}),
        ]
        environment = {k: v for k, v in os.environ.items() if not k.startswith("DCE_")}
        environment.update(DCE_AI_ENABLED="false", DCE_ALLOW_HTTP="false")
        parameters = StdioServerParameters(
            command=str(executable),
            args=[
                "--catalog",
                str(catalog_path),
                "mcp",
                "serve",
                "--transport",
                "stdio",
                "--live",
                "--read-only",
            ],
            env=environment,
            cwd="/",  # Prove the executable and catalog do not depend on the host cwd.
        )
        sizes = []
        with open(os.devnull, "w") as errlog:
            async with stdio_client(parameters, errlog=errlog) as (read, write):
                async with ClientSession(
                    read, write, read_timeout_seconds=timedelta(seconds=20)
                ) as session:
                    initialized = await session.initialize()
                    listed = await session.list_tools()
                    if {t.name for t in listed.tools} != TOOLS or not all(
                        t.annotations
                        and t.annotations.readOnlyHint
                        and t.annotations.destructiveHint is False
                        and t.inputSchema.get("additionalProperties") is False
                        and t.meta
                        and t.meta.get("dce", {}).get("contract_revision") == "1.1"
                        for t in listed.tools
                    ):
                        raise CheckFailure("Read-only tool contract mismatch.")
                    validators = {}
                    for tool in listed.tools:
                        Draft202012Validator.check_schema(tool.inputSchema)
                        Draft202012Validator.check_schema(tool.outputSchema)
                        validators[tool.name] = Draft202012Validator(tool.outputSchema)
                    for name, arguments in requests:
                        response = await session.call_tool(name, arguments)
                        payload = response.structuredContent
                        if response.isError or not payload or payload.get("status") != "ok":
                            raise CheckFailure("Catalog query failed.")
                        validators[name].validate(payload)
                        size = len(json.dumps(payload, ensure_ascii=False).encode())
                        if size > 16000 or payload.get("truncated"):
                            raise CheckFailure("Response exceeded the configured budget.")
                        sizes.append(size)
                    for name, arguments, expected in (
                        ("bug_context", {"bug_id": "unconfigured"}, "PERMISSION_DENIED"),
                        (
                            "pipeline_diagnose",
                            {"project_key": "unconfigured", "pipeline_id": "1"},
                            "PERMISSION_DENIED",
                        ),
                        ("deploy_execute", {}, "NOT_FOUND"),
                    ):
                        response = await session.call_tool(name, arguments)
                        payload = response.structuredContent or {}
                        if (
                            not response.isError
                            or payload.get("error", {}).get("error_code") != expected
                        ):
                            raise CheckFailure("Scope guard did not fail closed.")
                        if name in validators:
                            validators[name].validate(payload)
        if catalog.counts() != before:
            raise CheckFailure("MCP reads changed Catalog counts.")
        return {
            "status": "passed",
            "mode": "catalog_only",
            "transport": "stdio",
            "server_version": initialized.serverInfo.version,
            "contract_revision": "1.1",
            "tool_count": len(listed.tools),
            "successful_reads": len(requests),
            "scope_denials": 2,
            "unknown_write_denied": True,
            "response_bytes": sizes,
            "catalog_counts": before,
            "catalog_counts_unchanged": True,
            "cursor_host": "not_verified",
        }
    finally:
        catalog.engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        result = asyncio.run(asyncio.wait_for(check(arguments.catalog.resolve()), timeout=60))
    except CheckFailure as exc:
        print(json.dumps({"status": "error", "error_type": "CheckFailure", "message": str(exc)}))
        return 1
    except Exception as exc:
        # Exception text may contain internal paths or upstream content. Never print it.
        print(json.dumps({"status": "error", "error_type": type(exc).__name__}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
