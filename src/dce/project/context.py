"""Strict loading and pure refresh; no workspace writing API."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from dce.common.errors import DceError, ErrorCode
from dce.project.model import ProjectContext, Relationship

SECRET = re.compile(r"token|password|secret|credential|authorization|api.?key|private.?key", re.I)
ASSIGNMENT = re.compile(
    r"(?i)(?:token|password|secret|api.?key|authorization)\s*[:=]|"
    r"-----BEGIN .*PRIVATE KEY|\bglpat-[\w-]+|\bsk-(?:proj-)?[\w-]{20,}|"
    r"(?:https?|ssh)://[^/\s]*@|(?:https?://[^\s]*\?[^\s]+)"
)


def reject_secrets(value: Any, depth: int = 0) -> None:
    if depth > 30:
        raise ValueError("nesting limit")
    if isinstance(value, dict):
        for k, v in value.items():
            if SECRET.search(str(k)):
                raise ValueError("secret key")
            reject_secrets(v, depth + 1)
    elif isinstance(value, list):
        for v in value:
            reject_secrets(v, depth + 1)
    elif isinstance(value, str) and ASSIGNMENT.search(value):
        raise ValueError("secret value")


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader: UniqueLoader, node: yaml.MappingNode) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ValueError("duplicate or non-string key")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def validate_text(text: str, *, workspace_id: str | None = None) -> ProjectContext:
    try:
        if len(text.encode()) > 1_000_000:
            raise ValueError("size limit")
        tokens = list(yaml.scan(text))
        if len(tokens) > 50000 or any(
            isinstance(t, (yaml.AliasToken, yaml.AnchorToken)) for t in tokens
        ):
            raise ValueError("unsafe aliases or size")
        data = yaml.load(text, Loader=UniqueLoader)
        reject_secrets(data)
        project = ProjectContext.model_validate(data)
        if workspace_id is not None and project.workspace.id != workspace_id:
            raise ValueError("workspace mismatch")
        return project
    except (ValueError, TypeError, yaml.YAMLError, RecursionError, ValidationError):
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid or unsafe project context.") from None


def load_project(workspace: Path, *, workspace_id: str | None = None) -> ProjectContext:
    root = workspace.resolve(strict=True)
    path = root / ".dce" / "project.yaml"
    if path.is_symlink() or path.parent.is_symlink() or not path.resolve().is_relative_to(root):
        raise DceError(ErrorCode.PERMISSION_DENIED, "Project context must stay in workspace.")
    if path.stat().st_size > 1_000_000:
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Project context size limit exceeded.")
    project = validate_text(path.read_text(), workspace_id=workspace_id)
    for item in project.workspace.roots:
        if not (root / item.path).resolve().is_relative_to(root):
            raise DceError(ErrorCode.PERMISSION_DENIED, "Git root escapes workspace.")
    return project


def evidence_signature(r: Relationship) -> str:
    return json.dumps(
        [e.model_dump(mode="json", exclude={"observed_at"}) for e in r.evidence], sort_keys=True
    )


def refresh(project: ProjectContext, observations: list[Relationship]) -> ProjectContext:
    """Host supplies facts; existing approval/rejection/notes survive. No automatic confirmation."""
    if len({r.id for r in observations}) != len(observations):
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Duplicate refresh relationship identity.")
    pending = {r.id: r for r in observations}
    merged = []
    timestamp = datetime.now(UTC)
    for old in project.relationships:
        new = pending.pop(old.id, None)
        current = old.model_copy(deep=True)
        if old.status == "rejected":
            merged.append(current)
            continue
        if new is None:
            current.status = "stale"
        elif (old.from_, old.relation, old.to) != (new.from_, new.relation, new.to):
            current.status = "conflicted"
        elif evidence_signature(old) != evidence_signature(new):
            current.status = "stale" if old.status == "confirmed" else "conflicted"
            current.evidence = new.evidence
        else:
            current.last_verified_at = timestamp
        merged.append(current)
    for new in pending.values():
        merged.append(
            new.model_copy(
                update={"status": "proposed", "approved_by": None, "approved_at": None}, deep=True
            )
        )
    data = project.model_dump(by_alias=True, mode="json")
    data["relationships"] = [r.model_dump(by_alias=True, mode="json") for r in merged]
    data["metadata"]["last_refresh_at"] = timestamp.isoformat()
    data["metadata"]["updated_at"] = timestamp.isoformat()
    return validate_text(yaml.safe_dump(data))


def template(workspace_id: str = "business-project") -> dict[str, Any]:
    return ProjectContext.model_validate(
        {"workspace": {"id": workspace_id, "name": "Business Project", "roots": [{"path": "."}]}}
    ).model_dump(mode="json", by_alias=True)
