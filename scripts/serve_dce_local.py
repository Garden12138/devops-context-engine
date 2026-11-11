"""Explicit private credential source + ZenTao v1 login + existing read-only MCP server."""

import argparse
import sys
from pathlib import Path

from dce.app.facts import FactScope
from dce.app.services import AppServices
from dce.common.errors import DceError, ErrorCode
from dce.common.output import encode, envelope
from dce.mcp.server import serve
from dce.mcp.startup import (
    configure_stderr_audit,
    load_log_policy,
    parse_log_scopes,
    require_platforms,
)
from dce.security.local_credentials import local_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="Non-secret connection TOML.")
    parser.add_argument(
        "--credentials-file", type=Path, required=True, help="Explicit private dotenv input."
    )
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument(
        "--require-platform",
        action="append",
        choices=("zentao", "gitlab", "portainer"),
        default=[],
        help="Fail before stdio if a required connection is absent; no new grant.",
    )
    parser.add_argument("--portainer-log-scope", action="append", default=[])
    parser.add_argument("--portainer-log-policy", type=Path)
    for flag in (
        "gitlab-project",
        "zentao-project",
        "zentao-product",
        "zentao-bug",
        "portainer-endpoint",
        "portainer-stack",
    ):
        parser.add_argument("--" + flag, action="append", default=[])
    args = parser.parse_args()
    try:
        log_scopes = parse_log_scopes(
            args.portainer_log_scope, args.portainer_endpoint, args.portainer_stack
        )
        log_policy = load_log_policy(args.portainer_log_policy, log_scopes)
        settings = local_settings(
            args.config, args.credentials_file, live=args.live, read_only=args.read_only
        )
        require_platforms(settings, args.require_platform)
        settings.catalog_path = args.catalog
        scope = FactScope(
            gitlab_projects=set(args.gitlab_project),
            zentao_projects=set(args.zentao_project),
            zentao_products=set(args.zentao_product),
            zentao_bugs=set(args.zentao_bug),
            portainer_endpoints=set(args.portainer_endpoint),
            portainer_stacks=set(args.portainer_stack),
            portainer_log_scopes=log_scopes,
            portainer_log_policy=log_policy,
        )
        configure_stderr_audit()
        with AppServices(settings) as services:
            serve(
                services,
                live=True,
                read_only=True,
                fact_scope=scope,
                allowed_bug_ids=scope.zentao_bugs,
                allowed_gitlab_projects=scope.gitlab_projects,
            )
    except Exception as exc:
        error = (
            exc
            if isinstance(exc, DceError)
            else DceError(ErrorCode.INVALID_PAYLOAD, "Local MCP initialization failed.")
        )
        print(encode(envelope(error=error)), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
