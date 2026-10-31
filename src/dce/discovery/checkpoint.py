import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from dce.common.errors import DceError, ErrorCode
from dce.graph.model import DiscoveryResult, now


class Checkpoint:
    """Private normalized-result cache; a failed resource never advances its version."""

    def __init__(self, path: Path, scope_key: str) -> None:
        self.path = path
        self.state: dict[str, Any] = {
            "schema_version": 1,
            "scope_key": scope_key,
            "status": "running",
            "resources": {},
        }
        if path.exists():
            try:
                state = json.loads(path.read_text())
                if (
                    state["schema_version"] != 1
                    or state["scope_key"] != scope_key
                    or not isinstance(state["resources"], dict)
                ):
                    raise ValueError
                self.state = state
            except (ValueError, KeyError, TypeError):
                raise DceError(
                    ErrorCode.SNAPSHOT_CONFLICT, "Checkpoint scope/schema mismatch."
                ) from None

    def save(self) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.state["updated_at"] = now()
        descriptor, temporary = tempfile.mkstemp(dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w") as stream:
                json.dump(self.state, stream, sort_keys=True)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def resource(
        self, key: str, version: str, collect: Callable[[], DiscoveryResult]
    ) -> DiscoveryResult:
        cached = self.state["resources"].get(key)
        if cached and cached["version"] == version:
            try:
                return DiscoveryResult.model_validate(cached["result"])
            except ValidationError:
                raise DceError(
                    ErrorCode.INVALID_PAYLOAD, "Invalid normalized checkpoint."
                ) from None
        self.state["status"] = "running"
        try:
            result = collect()
        except DceError as exc:
            self.state["status"] = "failed"
            self.state["failed_resource"] = key
            self.state["error_code"] = exc.code.value
            self.save()
            raise
        self.state["resources"][key] = {"version": version, "result": result.model_dump()}
        self.state.pop("error_code", None)
        self.state.pop("failed_resource", None)
        self.save()
        return result

    def complete(self) -> None:
        self.state["status"] = "complete"
        self.save()
