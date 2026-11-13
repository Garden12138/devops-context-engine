"""Scoped live SDK smoke after Host initialization; never claims real Agent Host acceptance."""

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dce.project.context import load_project


async def check(
    workspace: Path, config: Path | None, catalog: Path, include_image: bool = False
) -> dict[str, Any]:
    project = load_project(workspace)
    executable = Path(__file__).resolve().parents[1] / ".venv/bin/dce"
    args = ["--catalog", str(catalog.resolve())]
    if config:
        if config.suffix != ".toml" or config.name.startswith(".env"):
            raise ValueError("non-secret TOML required")
        args += ["--config", str(config.resolve())]
    args += ["mcp", "serve", "--live", "--read-only"]
    scope = project.scope
    requests: list[tuple[str, dict[str, Any]]] = []
    if scope.gitlab:
        for i in scope.gitlab.projects:
            args += ["--gitlab-project", i]
        if scope.gitlab.projects:
            requests.append(
                (
                    "gitlab_query",
                    {
                        "instance": scope.gitlab.instance,
                        "operation": "project",
                        "project_id": scope.gitlab.projects[0],
                    },
                )
            )
    if scope.zentao:
        for flag, values in (
            ("--zentao-project", scope.zentao.projects),
            ("--zentao-product", scope.zentao.products),
            ("--zentao-bug", scope.zentao.bugs),
        ):
            for i in values:
                args += [flag, i]
        if scope.zentao.bugs:
            requests.append(
                (
                    "zentao_query",
                    {
                        "instance": scope.zentao.instance,
                        "operation": "bug",
                        "bug_id": scope.zentao.bugs[0],
                    },
                )
            )
            if include_image:
                requests.append(
                    (
                        "zentao_query",
                        {
                            "instance": scope.zentao.instance,
                            "operation": "image",
                            "bug_id": scope.zentao.bugs[0],
                            "asset_index": 0,
                        },
                    )
                )
        elif scope.zentao.projects:
            requests.append(
                (
                    "zentao_query",
                    {
                        "instance": scope.zentao.instance,
                        "operation": "project",
                        "project_id": scope.zentao.projects[0],
                    },
                )
            )
    if scope.portainer:
        for flag, values in (
            ("--portainer-endpoint", scope.portainer.endpoints),
            ("--portainer-stack", scope.portainer.stacks),
        ):
            for i in values:
                args += [flag, i]
        if scope.portainer.endpoints:
            requests.append(
                (
                    "portainer_query",
                    {
                        "instance": scope.portainer.instance,
                        "operation": "swarm_info",
                        "endpoint_id": scope.portainer.endpoints[0],
                    },
                )
            )
    sizes, errors, successful, image_delivered = [], [], 0, False
    # The child inherits protected process credentials. They never enter the report or argv.
    parameters = StdioServerParameters(
        command=str(executable), args=args, cwd="/", env=dict(os.environ)
    )
    with open(os.devnull, "w") as errlog:
        async with stdio_client(parameters, errlog=errlog) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = {t.name: t for t in (await session.list_tools()).tools}
                for name, arguments in requests:
                    result = await session.call_tool(name, arguments)
                    payload = result.structuredContent or {}
                    Draft202012Validator(tools[name].outputSchema).validate(payload)
                    sizes.append(len(json.dumps(payload, ensure_ascii=False).encode()))
                    if result.isError:
                        errors.append(payload.get("error", {}).get("code", "INVALID_PAYLOAD"))
                    elif payload.get("truncated") or payload.get("data") is None:
                        errors.append("OUTPUT_TRUNCATED")
                    else:
                        successful += 1
                    if arguments["operation"] == "image":
                        image_delivered = any(c.type == "image" for c in result.content)
    return {
        "status": "passed_scoped_sdk_reads" if successful >= 3 and not errors else "incomplete",
        "tool_count": len(tools),
        "successful_reads": successful,
        "error_codes": errors,
        "response_bytes": sizes,
        "image_content_received_by_sdk": image_delivered,
        "real_agent_host": "not_verified",
        "image_received_by_model": "not_verified",
        "workspace_written_by_dce": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument(
        "--include-image",
        action="store_true",
        help="Only with authorization to read the first scoped Bug image; no saving.",
    )
    args = parser.parse_args()
    try:
        result = asyncio.run(
            asyncio.wait_for(
                check(args.workspace, args.config, args.catalog, args.include_image), timeout=60
            )
        )
    except Exception as error:
        result = {
            "status": "not_verified",
            "error_type": type(error).__name__,
            "message": "Scoped SDK smoke could not complete; no private payload exported.",
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed_scoped_sdk_reads" else 2


if __name__ == "__main__":
    raise SystemExit(main())
