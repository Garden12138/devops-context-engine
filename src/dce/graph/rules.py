import re
from typing import Any

from dce.discovery.fixture import Builder
from dce.graph.model import DiscoveryResult, Edge, Entity, Evidence


def _words(value: Any) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", str(value).lower())) - {"demo", "template", "common"}


def suggestions(graph: DiscoveryResult) -> DiscoveryResult:
    """Return additional relationships; observed graph is never promoted semantically."""
    b = Builder()
    entities = {entity.id: entity for entity in graph.entities}
    evidence = {item.id: item for item in graph.evidence}
    modules: dict[str, list[tuple[Entity, Edge]]] = {}
    for edge in graph.edges:
        if edge.relation == "contains_module" and edge.target_id in entities:
            modules.setdefault(edge.source_id, []).append((entities[edge.target_id], edge))
    extra_edges = []
    extra_evidence = []
    for edge in graph.edges:
        if edge.relation != "declares_build_job" or edge.target_id not in entities:
            continue
        job = entities[edge.target_id]
        for module, containment in modules.get(edge.source_id, []):
            if module.attributes.get("path") in job.attributes.get("module_paths", []):
                extra_edges.append(
                    Edge(
                        source_id=module.id,
                        target_id=job.id,
                        relation="declares_module_input",
                        status="observed_verified",
                        confidence=1,
                        evidence_ids=sorted(set(edge.evidence_ids + containment.evidence_ids)),
                    )
                )
    candidate_count = 0
    for business in graph.entities:
        if business.kind not in {"business_project", "product"}:
            continue
        for module, containment in (item for group in modules.values() for item in group):
            if candidate_count >= 50:
                b.result.warnings.append("CANDIDATE_LIMIT_REACHED")
                break
            refs = [reference for reference in containment.evidence_ids if reference in evidence]
            if not refs:
                continue
            basis = evidence[refs[0]]
            clue = _words(business.attributes.get("name", "")) & _words(
                module.attributes.get("path", "")
            )
            score = min(0.35 + len(clue) * 0.1, 0.69) if clue else 0.1
            item = Evidence(
                snapshot_id=basis.snapshot_id,
                source_instance=basis.source_instance,
                locator=f"rules/semantic/{business.id}/{module.id}",
                version=basis.version,
                summary="Name overlap is a candidate clue only."
                if clue
                else "No verified business mapping; module is unresolved.",
            )
            extra_evidence.append(item)
            extra_edges.append(
                Edge(
                    source_id=business.id,
                    target_id=module.id,
                    relation="implements",
                    status="candidate" if clue else "unresolved",
                    confidence=score,
                    evidence_ids=sorted(set(refs + [item.id])),
                )
            )
            candidate_count += 1
    b.result.edges = extra_edges
    b.result.evidence = extra_evidence
    return b.result


def provider_summary(graph: DiscoveryResult) -> dict[str, Any]:
    """No resource names, paths, URLs, raw config or untrusted descriptions cross this boundary."""
    allowed = {
        "repository",
        "module",
        "business_project",
        "product",
        "bug",
        "stack",
        "service",
        "image",
        "build_job",
        "environment",
        "endpoint",
        "swarm",
        "compose_service",
    }
    return {
        "schema_version": "1.0",
        "resources": [
            {"id": entity.id, "kind": entity.kind if entity.kind in allowed else "resource"}
            for entity in graph.entities[:200]
        ],
        "evidence_ids": [item.id for item in graph.evidence[:200]],
        "omitted_resources": max(0, len(graph.entities) - 200),
    }
