"""Shared startup checks; no network, credential source or authorization expansion."""

import logging
import sys
from collections.abc import Iterable
from pathlib import Path

from dce.common.config import Settings
from dce.common.errors import DceError, ErrorCode
from dce.security.log_grant import ServiceLogGrant


def parse_log_scopes(
    values: Iterable[str], endpoints: Iterable[str], stacks: Iterable[str]
) -> set[tuple[str, str]]:
    endpoint_scope, stack_scope = set(endpoints), set(stacks)
    grants: set[tuple[str, str]] = set()
    for value in values:
        parts = value.split(":")
        if len(parts) != 2 or not all(p.isdecimal() for p in parts):
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Log scope must be ENDPOINT_ID:STACK_ID.")
        if parts[0] not in endpoint_scope or parts[1] not in stack_scope:
            raise DceError(ErrorCode.PERMISSION_DENIED, "Log scope requires metadata scope.")
        grants.add((parts[0], parts[1]))
    return grants


def require_platforms(settings: Settings, platforms: Iterable[str]) -> None:
    for platform in platforms:
        if platform not in {"zentao", "gitlab", "portainer"}:
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Unknown required MCP platform.")
        if getattr(settings, platform) is None:
            raise DceError(
                ErrorCode.AUTH_FAILED,
                f"MCP startup configuration missing for {platform}; "
                "check --config and --credentials-file.",
            )
        settings.platform(platform)


def load_log_policy(path: Path | None, scopes: set[tuple[str, str]]) -> ServiceLogGrant | None:
    if path is None:
        return None
    grant = ServiceLogGrant.load(path)
    if scopes != {(grant.spec.endpoint_id, grant.spec.stack_id)}:
        raise DceError(ErrorCode.PERMISSION_DENIED, "Log policy requires its exact log scope pair.")
    return grant


def configure_stderr_audit() -> None:
    logger = logging.getLogger("dce.audit")
    if not any(h.name == "dce-mcp-stderr" for h in logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.set_name("dce-mcp-stderr")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def serve_project(settings: Settings, state_dir: Path, log_policy: Path | None = None) -> None:
    """Startup is inert: a temporary empty Catalog, no roots scan or platform probe."""
    import tempfile

    from dce.app.services import AppServices
    from dce.mcp.server import serve
    from dce.project.runtime import ProjectRuntime

    configure_stderr_audit()
    runtime = ProjectRuntime(state_dir, log_policy)
    with tempfile.TemporaryDirectory(prefix="dce-unbound-") as temporary:
        initial = settings.model_copy(update={"catalog_path": Path(temporary) / "catalog.sqlite3"})
        try:
            with AppServices(initial) as services:
                serve(services, live=True, read_only=True, project=runtime)
        finally:
            runtime.close()
