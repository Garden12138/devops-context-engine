import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, Field


def identity(source: str, kind: str, external_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, json.dumps([source, kind, str(external_id)])))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def now() -> str:
    return datetime.now(UTC).isoformat()


class Entity(BaseModel):
    source_instance: str
    kind: str
    external_id: str
    attributes: dict[str, Any] = Field(default_factory=dict)

    @property
    def id(self) -> str:
        return identity(self.source_instance, self.kind, self.external_id)


class Snapshot(BaseModel):
    source_instance: str
    resource_key: str
    kind: Literal["git_current", "portainer_saved", "swarm_runtime", "repository", "business"]
    version: str
    observed_at: str = Field(default_factory=now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def id(self) -> str:
        return identity(self.source_instance, self.kind, f"{self.resource_key}:{self.version}")


class Evidence(BaseModel):
    snapshot_id: str
    source_instance: str
    locator: str
    version: str
    observed_at: str = Field(default_factory=now)
    summary: str

    @property
    def id(self) -> str:
        return identity(self.source_instance, "evidence", f"{self.snapshot_id}:{self.locator}")


class Edge(BaseModel):
    source_id: str
    target_id: str
    relation: str
    status: Literal["observed_verified", "candidate", "unresolved", "stale_candidate"]
    evidence_ids: list[str] = Field(min_length=1)
    confidence: float = Field(default=1, ge=0, le=1)

    @property
    def id(self) -> str:
        return identity(self.source_id, self.relation, self.target_id)


class DiscoveryResult(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    snapshots: list[Snapshot] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
