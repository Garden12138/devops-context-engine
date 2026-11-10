import asyncio
from typing import Any

from pydantic import ValidationError

from dce.ai.provider import CandidateBatch, CandidateProvider
from dce.catalog.db import Catalog
from dce.common.errors import DceError, ErrorCode
from dce.graph.model import Edge, Evidence, Snapshot, fingerprint
from dce.graph.rules import provider_summary, suggestions
from dce.security.redact import redact


class MappingService:
    def __init__(
        self, catalog: Catalog, *, provider: CandidateProvider | None = None, timeout: float = 5
    ) -> None:
        self.catalog = catalog
        self.provider = provider
        self.timeout = min(max(timeout, 0.001), 30)

    async def suggest(self, *, no_ai: bool = False) -> dict[str, Any]:
        graph = self.catalog.read_graph()
        additions = suggestions(graph)
        ai_status = "disabled"
        if self.provider is not None and not no_ai:
            try:
                payload = await asyncio.wait_for(
                    self.provider.generate(provider_summary(graph)), self.timeout
                )
                batch = (
                    CandidateBatch.model_validate_json(payload)
                    if isinstance(payload, str)
                    else CandidateBatch.model_validate(payload)
                )
                resource_ids = {entity.id for entity in graph.entities}
                evidence_ids = {item.id for item in graph.evidence}
                candidates = []
                for candidate in batch.candidates:
                    if (
                        candidate.source_id not in resource_ids
                        or candidate.target_id not in resource_ids
                        or not set(candidate.evidence_ids) <= evidence_ids
                    ):
                        raise ValueError("untraceable candidate")
                    candidates.append(
                        Edge(
                            source_id=candidate.source_id,
                            target_id=candidate.target_id,
                            relation=candidate.relation,
                            status="candidate",
                            confidence=min(candidate.confidence, 0.79),
                            evidence_ids=candidate.evidence_ids,
                        )
                    )
                if candidates:
                    metadata = {"candidates": redact(batch.model_dump()["candidates"])}
                    snapshot = Snapshot(
                        source_instance="ai-candidate-provider",
                        resource_key="mapping-proposals",
                        kind="ai_candidate",
                        version=fingerprint(metadata),
                        metadata=metadata,
                    )
                    additions.snapshots.append(snapshot)
                    for candidate, edge in zip(batch.candidates, candidates, strict=True):
                        proposal = Evidence(
                            source_instance="ai-candidate-provider",
                            snapshot_id=snapshot.id,
                            locator=f"candidate/{edge.id}",
                            version=snapshot.version,
                            summary="AI candidate (untrusted rationale): "
                            + redact(candidate.rationale),
                        )
                        additions.evidence.append(proposal)
                        edge.evidence_ids = sorted(set(edge.evidence_ids + [proposal.id]))
                additions.edges.extend(candidates)
                ai_status = "ok"
            except TimeoutError:
                ai_status = "timeout"
            except (ValueError, ValidationError):
                ai_status = "invalid_response"
            except Exception:
                ai_status = "failed"
        unique: dict[str, Edge] = {}
        for edge in additions.edges:
            if edge.id in unique:
                previous = unique[edge.id]
                edge = edge.model_copy(
                    update={
                        "evidence_ids": sorted(set(previous.evidence_ids + edge.evidence_ids)),
                        "confidence": max(previous.confidence, edge.confidence),
                        "status": "candidate"
                        if "candidate" in {previous.status, edge.status}
                        else previous.status,
                    }
                )
            unique[edge.id] = edge
        additions.edges = list(unique.values())
        # Only add edges/evidence: mapping scopes must never claim resource ownership.
        if additions.edges:
            self.catalog.import_scan(additions, scope="mapping-suggestions", complete=False)
        run_id = self.catalog.record_mapping_run(ai_status, len(additions.edges))
        return {
            "run_id": run_id,
            "ai_status": ai_status,
            "suggested": len(additions.edges),
            "warnings": additions.warnings,
            "next_action": "Review candidates with actor, reason and expected version.",
        }

    def preview(self, edge_id: str) -> dict[str, Any]:
        edge = self.catalog.edge(edge_id)
        target = self.catalog.get_entity(edge["target_id"])
        source = self.catalog.get_entity(edge["source_id"])
        requires_environment = (
            source["kind"] == "environment"
            or target["kind"] == "environment"
            or edge["relation"]
            in {
                "deployed_in",
                "environment",
            }
        )
        return {
            "edge": edge,
            "source": source,
            "target": target,
            "evidence": self.catalog.get_evidence(edge["evidence_ids"]),
            "environment_confirmation_required": requires_environment,
            "environment": target["attributes"]
            if target["kind"] == "environment"
            else "unresolved",
            "impact": {"source_id": source["id"], "target_id": target["id"]},
            "reviews": self.catalog.reviews(edge_id),
        }

    def review(
        self,
        edge_id: str,
        *,
        action: str,
        actor: str,
        reason: str,
        expected_version: int,
        confirm_environment: bool = False,
    ) -> None:
        preview = self.preview(edge_id)
        if (
            action in {"accept", "override"}
            and preview["environment_confirmation_required"]
            and not confirm_environment
        ):
            raise DceError(
                ErrorCode.REVIEW_REQUIRED,
                "Environment relationship needs explicit human confirmation.",
            )
        if action in {"accept", "override"} and preview["edge"]["stale"]:
            raise DceError(
                ErrorCode.REVIEW_REQUIRED,
                "Stale relationship must be rediscovered before acceptance.",
            )
        self.catalog.review(
            edge_id, action=action, actor=actor, reason=reason, expected_version=expected_version
        )
