import json
from pathlib import Path
from typing import Any

from dce.common.errors import DceError, ErrorCode
from dce.discovery.snapshots import compare_services, stack_runtime
from dce.graph.model import DiscoveryResult, Edge, Entity, Evidence, Snapshot, fingerprint
from dce.parsers.metadata import image


class Builder:
    def __init__(self) -> None:
        self.result = DiscoveryResult()
        self.entities: dict[str, Entity] = {}
        self.edges: dict[str, Edge] = {}

    def entity(self, source: str, kind: str, external_id: object, **attrs: Any) -> Entity:
        entity = Entity(
            source_instance=source, kind=kind, external_id=str(external_id), attributes=attrs
        )
        self.entities[entity.id] = entity
        return entity

    def snapshot(self, source: str, resource: str, kind: Any, metadata: dict[str, Any]) -> Snapshot:
        snapshot = Snapshot(
            source_instance=source,
            resource_key=resource,
            kind=kind,
            version=fingerprint(metadata),
            metadata=metadata,
        )
        self.result.snapshots.append(snapshot)
        return snapshot

    def link(
        self,
        source: Entity,
        target: Entity,
        relation: str,
        snapshot: Snapshot,
        locator: str,
        *,
        status: Any = "observed_verified",
        confidence: float = 1,
    ) -> None:
        evidence = Evidence(
            snapshot_id=snapshot.id,
            source_instance=snapshot.source_instance,
            locator=locator,
            version=snapshot.version,
            summary=relation,
        )
        self.result.evidence.append(evidence)
        edge = Edge(
            source_id=source.id,
            target_id=target.id,
            relation=relation,
            status=status,
            confidence=confidence,
            evidence_ids=[evidence.id],
        )
        if edge.id in self.edges:
            edge.evidence_ids = sorted(set(self.edges[edge.id].evidence_ids + edge.evidence_ids))
        self.edges[edge.id] = edge

    def image_entity(self, reference: str) -> Entity:
        # OCI identities are independent of GitLab/Portainer IDs.
        registry = reference.split("/", 1)[0] if "/" in reference else "docker.io"
        return self.entity(
            f"oci:{fingerprint(registry)[:16]}", "image", reference, **image(reference)
        )

    def finish(self) -> DiscoveryResult:
        self.result.entities = list(self.entities.values())
        self.result.edges = list(self.edges.values())
        self.result.evidence = list({e.id: e for e in self.result.evidence}.values())
        return self.result


def load_fixture(path: Path) -> dict[str, Any]:
    try:
        if path.stat().st_size > 5_000_000:
            raise ValueError
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or data.get("synthetic") is not True:
            raise ValueError
        return data
    except (OSError, ValueError, RecursionError):
        raise DceError(
            ErrorCode.INVALID_PAYLOAD, "Expected bounded synthetic discovery fixture."
        ) from None


def discover_fixture(path: Path) -> DiscoveryResult:
    data = load_fixture(path)
    try:
        return normalize_fixture(data)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise DceError(
            ErrorCode.INVALID_PAYLOAD, "Invalid synthetic discovery structure."
        ) from None


def normalize_fixture(data: dict[str, Any]) -> DiscoveryResult:
    b = Builder()
    sources = {item["kind"]: item["id"] for item in data["source_instances"]}
    git, port, zen = sources["gitlab"], sources["portainer"], sources["zentao"]
    deployment = data["gitlab"]["deployment_repo"]
    repo = b.entity(
        git,
        "repository",
        deployment["id"],
        role="deployment",
        path=deployment["path"],
        default_branch=deployment["default_branch"],
    )
    current = [
        {"name": s["name"], "image": image(s["image"])["reference"]}
        for s in deployment["compose_services"]
    ]
    git_snapshot = b.snapshot(
        git,
        repo.id,
        "git_current",
        {
            "services": current,
            "ref": deployment["default_branch"],
            "path": deployment["compose_file"],
            "version_verification": "synthetic",
        },
    )
    for spec in current:
        service = b.entity(
            git, "compose_service", f"{deployment['id']}:{spec['name']}", name=spec["name"]
        )
        img = b.image_entity(spec["image"])
        b.link(repo, service, "declares_service", git_snapshot, f"services/{spec['name']}")
        b.link(service, img, "declares_image", git_snapshot, f"services/{spec['name']}/image")
    for source in data["gitlab"]["source_repos"]:
        source_repo = b.entity(git, "repository", source["id"], role="source", path=source["path"])
        snapshot = b.snapshot(git, source_repo.id, "repository", {"modules": source["modules"]})
        for name in source["modules"]:
            module = b.entity(git, "module", f"{source['id']}:{name}", path=name)
            b.link(source_repo, module, "contains_module", snapshot, f"modules/{name}")
    endpoint = data["portainer"]["endpoint"]
    endpoint_entity = b.entity(
        port, "endpoint", endpoint["id"], current_swarm_id=endpoint["current_swarm_id"]
    )
    swarm = b.entity(port, "swarm", endpoint["current_swarm_id"], endpoint_id=endpoint["id"])
    runtime = [
        {"name": s["name"], "namespace": s["namespace"], "image": image(s["image"])["reference"]}
        for s in data["portainer"]["runtime_services"]
    ]
    for original in data["portainer"]["stacks"]:
        # Fixture schema has a single endpoint. Live adapters must supply EndpointId.
        stack = {"endpoint_id": endpoint["id"], **original}
        observed = stack_runtime(stack, endpoint, runtime)
        entity = b.entity(
            port,
            "stack",
            stack["id"],
            name=stack["name"],
            swarm_id=stack["swarm_id"],
            endpoint_id=endpoint["id"],
            state=observed["status"],
            environment="unresolved",
            health="unknown",
        )
        saved = stack.get("saved_compose_services")
        if saved is not None:
            saved = [{"name": s["name"], "image": image(s["image"])["reference"]} for s in saved]
        saved_snapshot = b.snapshot(
            port,
            entity.id,
            "portainer_saved",
            {
                "services": saved or [],
                "service_count": stack["saved_service_count"],
                "incomplete": saved is None,
                "ref": stack["git_branch"],
                "path": stack["compose_file"],
            },
        )
        b.link(endpoint_entity, entity, "records_stack", saved_snapshot, "EndpointId")
        if stack["git_repo"] == deployment["path"]:
            b.link(entity, repo, "declares_repository", saved_snapshot, "GitConfig/repository")
        if saved is not None:
            diff = compare_services(current, saved)
            if diff["status"] == "config_drift_candidate":
                b.result.anomalies.append(
                    {
                        "stack_id": entity.id,
                        **diff,
                        "snapshot_ids": [git_snapshot.id, saved_snapshot.id],
                    }
                )
        else:
            b.result.warnings.append(f"SAVED_CONFIG_INCOMPLETE:{entity.id}")
        if observed["status"] == "stale_candidate":
            b.result.anomalies.append(
                {"stack_id": entity.id, "status": "stale_candidate", "reason": observed["reason"]}
            )
            continue
        selected = observed["services"]
        snapshot = b.snapshot(
            port,
            entity.id,
            "swarm_runtime",
            {
                "services": selected,
                "swarm_id": endpoint["current_swarm_id"],
                "namespace": observed["namespace"],
            },
        )
        b.link(endpoint_entity, swarm, "observes_swarm", snapshot, "DockerInfo/Swarm/Cluster/ID")
        b.link(swarm, entity, "observes_stack_namespace", snapshot, "Services/Labels/Namespace")
        for spec in selected:
            service = b.entity(
                port,
                "service",
                f"{endpoint['id']}:{spec['name']}",
                name=spec["name"],
                namespace=spec["namespace"],
                health="unknown",
            )
            img = b.image_entity(spec["image"])
            b.link(entity, service, "runs_service", snapshot, f"Spec/Labels/{spec['name']}")
            b.link(service, img, "observes_image_reference", snapshot, f"Spec/Image/{spec['name']}")
    for project in data["zentao"]["projects"]:
        b.entity(
            zen,
            "business_project",
            project["id"],
            name=project["name"],
            product_id=project["product_id"],
        )
    for bug in data["zentao"]["bugs"]:
        b.entity(
            zen,
            "bug",
            bug["id"],
            title=bug["title"],
            project_id=bug["project_id"],
            product_id=bug["product_id"],
        )
    for entity in b.entities.values():
        if entity.kind == "image" and entity.attributes["version_uncertain"]:
            b.result.anomalies.append(
                {
                    "image_id": entity.id,
                    "status": "version_uncertain",
                    "mutable_tag": entity.attributes["mutable_tag"],
                }
            )
    return b.finish()
