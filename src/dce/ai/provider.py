import asyncio
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    target_id: str
    relation: Literal["implements", "related_to", "deployed_in"]
    status: Literal["candidate"] = "candidate"
    evidence_ids: list[str] = Field(min_length=1, max_length=20)
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=500)


class CandidateBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[Candidate] = Field(max_length=20)


class CandidateProvider(Protocol):
    async def generate(self, summary: dict[str, Any]) -> Any: ...


class NoopProvider:
    async def generate(self, summary: dict[str, Any]) -> Any:
        return {"candidates": []}


class FakeProvider:
    """Deterministic offline provider for contracts; never opens network connections."""

    def __init__(self, payload: Any, *, delay: float = 0, fail: bool = False) -> None:
        self.payload = payload
        self.delay = delay
        self.fail = fail
        self.received: list[dict[str, Any]] = []

    async def generate(self, summary: dict[str, Any]) -> Any:
        self.received.append(summary)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("Synthetic provider failure; never expose raw exception.")
        return self.payload
