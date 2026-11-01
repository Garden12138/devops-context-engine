from pathlib import Path
from typing import Any
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Table, case, create_engine, event, func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from dce.catalog.schema import (
    approvals,
    audit_log,
    edge_history,
    edge_members,
    edges,
    entities,
    entity_history,
    evidence,
    members,
    scans,
    snapshots,
)
from dce.common.errors import DceError, ErrorCode
from dce.graph.model import DiscoveryResult, Edge, Entity, Evidence, Snapshot, now


class Catalog:
    def __init__(self, path: Path, *, revision: str = "head") -> None:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.is_symlink():
            raise DceError(ErrorCode.PERMISSION_DENIED, "Catalog path must not be a symlink.")
        if not path.exists():
            path.touch(mode=0o600)
        path.chmod(0o600)
        self.engine = create_engine("sqlite:///" + str(path.resolve()), echo=False)

        @event.listens_for(self.engine, "connect")
        def foreign_keys(connection: Any, _: Any) -> None:
            connection.execute("PRAGMA foreign_keys=ON")

        self.migrate(revision)

    def __enter__(self) -> "Catalog":
        return self

    def __exit__(self, *_: object) -> None:
        self.engine.dispose()

    def migrate(self, revision: str = "head") -> None:
        config = Config()
        config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, revision)

    @staticmethod
    def _row(connection: Connection, table: Table, key: str) -> dict[str, Any] | None:
        row = connection.execute(select(table).where(table.c.id == key)).mappings().first()
        return dict(row) if row else None

    @staticmethod
    def _upsert(connection: Connection, table: Table, data: dict[str, Any]) -> None:
        from sqlalchemy.dialects.sqlite import insert

        statement = insert(table).values(**data)
        connection.execute(statement.on_conflict_do_update(index_elements=[table.c.id], set_=data))

    @staticmethod
    def _audit(connection: Connection, resource: str, event_name: str, details: Any) -> None:
        connection.execute(
            audit_log.insert().values(
                id=str(uuid4()),
                resource_id=resource,
                event=event_name,
                timestamp=now(),
                details=details,
            )
        )

    def import_scan(self, result: DiscoveryResult, *, scope: str, complete: bool = True) -> str:
        if not scope.strip():
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Scan scope is required.")
        scan_id = str(uuid4())
        with self.engine.begin() as connection:
            connection.execute(
                scans.insert().values(
                    id=scan_id,
                    scope=scope,
                    status="running",
                    started_at=now(),
                    summary={},
                    anomalies=[],
                )
            )
        try:
            with self.engine.begin() as connection:
                self._import(connection, result, scope, scan_id, complete)
        except (SQLAlchemyError, ValueError):
            with self.engine.begin() as connection:
                connection.execute(
                    scans.update()
                    .where(scans.c.id == scan_id)
                    .values(
                        status="failed",
                        error_code=ErrorCode.INVALID_PAYLOAD.value,
                        finished_at=now(),
                    )
                )
            raise DceError(
                ErrorCode.INVALID_PAYLOAD, "Catalog import failed; batch rolled back."
            ) from None
        return scan_id

    def _import(
        self,
        connection: Connection,
        result: DiscoveryResult,
        scope: str,
        scan_id: str,
        complete: bool,
    ) -> None:
        from sqlalchemy.dialects.sqlite import insert

        timestamp = now()
        seen = set()
        for entity in result.entities:
            seen.add(entity.id)
            old = self._row(connection, entities, entity.id)
            changed = old is None or old["attributes"] != entity.attributes or old["deleted"]
            version = old["version"] + int(changed) if old else 1
            data = {
                "id": entity.id,
                **entity.model_dump(),
                "version": version,
                "deleted": False,
                "first_seen": old["first_seen"] if old else timestamp,
                "last_verified": timestamp,
            }
            self._upsert(connection, entities, data)
            if changed:
                connection.execute(
                    entity_history.insert().values(
                        entity_id=entity.id,
                        version=version,
                        attributes=entity.attributes,
                        deleted=False,
                        recorded_at=timestamp,
                    )
                )
            statement = insert(members).values(
                scope=scope, entity_id=entity.id, scan_id=scan_id, active=True
            )
            connection.execute(
                statement.on_conflict_do_update(
                    index_elements=["scope", "entity_id"], set_={"scan_id": scan_id, "active": True}
                )
            )
        for snapshot in result.snapshots:
            old = self._row(connection, snapshots, snapshot.id)
            data = {"id": snapshot.id, **snapshot.model_dump(), "last_verified": timestamp}
            if old:
                if old["metadata"] != snapshot.metadata:
                    raise ValueError("snapshot immutable conflict")
                data["observed_at"] = old["observed_at"]
            self._upsert(connection, snapshots, data)
        for item in result.evidence:
            old = self._row(connection, evidence, item.id)
            if old and any(
                old[key] != item.model_dump()[key]
                for key in ("snapshot_id", "locator", "version", "summary")
            ):
                raise ValueError("evidence immutable conflict")
            if not old:
                connection.execute(evidence.insert().values(id=item.id, **item.model_dump()))
        for edge in result.edges:
            if edge.status not in {
                "candidate",
                "unresolved",
                "observed_verified",
                "stale_candidate",
            }:
                raise ValueError("scanner cannot confirm relationships")
            if len(set(edge.evidence_ids)) != len(edge.evidence_ids):
                raise ValueError("duplicate evidence references")
            for reference in edge.evidence_ids:
                if self._row(connection, evidence, reference) is None:
                    raise ValueError("missing evidence")
            old = self._row(connection, edges, edge.id)
            changed = (
                old is None
                or old["stale"]
                or old["deleted"]
                or any(
                    old[key] != value
                    for key, value in {
                        "observed_status": edge.status,
                        "confidence": edge.confidence,
                        "evidence_ids": edge.evidence_ids,
                    }.items()
                )
            )
            data = {
                "id": edge.id,
                **edge.model_dump(),
                "observed_status": edge.status,
                "human_decision": old["human_decision"] if old else None,
                "version": old["version"] + int(changed) if old else 1,
                "conflict": bool(old and old["human_decision"] and changed),
                "stale": False,
                "deleted": False,
                "valid_from": old["valid_from"] if old else timestamp,
                "last_verified": timestamp,
                "valid_until": None,
            }
            if old and old["human_decision"]:
                data["status"] = old["status"]
                data["conflict"] |= old["conflict"]
            self._upsert(connection, edges, data)
            statement = insert(edge_members).values(
                scope=scope, edge_id=edge.id, scan_id=scan_id, active=True
            )
            connection.execute(
                statement.on_conflict_do_update(
                    index_elements=["scope", "edge_id"], set_={"scan_id": scan_id, "active": True}
                )
            )
            if changed:
                connection.execute(
                    edge_history.insert().values(
                        edge_id=edge.id,
                        version=data["version"],
                        payload=data,
                        recorded_at=timestamp,
                    )
                )
            if old and data["conflict"] and not old["conflict"]:
                self._audit(connection, edge.id, "scan_conflict", {"scan_id": scan_id})
        if complete:
            missing: Any = (
                connection.execute(
                    select(members.c.entity_id).where(
                        members.c.scope == scope, members.c.active.is_(True)
                    )
                )
                .scalars()
                .all()
            )
            for entity_id in set(missing) - seen:
                connection.execute(
                    members.update()
                    .where(members.c.scope == scope, members.c.entity_id == entity_id)
                    .values(active=False)
                )
                active = connection.execute(
                    select(func.count())
                    .select_from(members)
                    .where(members.c.entity_id == entity_id, members.c.active.is_(True))
                ).scalar_one()
                if active:
                    continue
                old_entity = self._row(connection, entities, entity_id)
                assert old_entity is not None
                version = old_entity["version"] + 1
                connection.execute(
                    entities.update()
                    .where(entities.c.id == entity_id)
                    .values(deleted=True, version=version, last_verified=timestamp)
                )
                connection.execute(
                    entity_history.insert().values(
                        entity_id=entity_id,
                        version=version,
                        attributes=old_entity["attributes"],
                        deleted=True,
                        recorded_at=timestamp,
                    )
                )
                related: Any = connection.execute(
                    select(edges.c.id).where(
                        or_(edges.c.source_id == entity_id, edges.c.target_id == entity_id)
                    )
                ).scalars()
                for edge_id in related:
                    self._expire_edge(connection, edge_id, scan_id, timestamp)
                self._audit(connection, entity_id, "source_disappeared", {"scan_id": scan_id})
            seen_edges = {edge.id for edge in result.edges}
            missing_edges: Any = (
                connection.execute(
                    select(edge_members.c.edge_id).where(
                        edge_members.c.scope == scope, edge_members.c.active.is_(True)
                    )
                )
                .scalars()
                .all()
            )
            for edge_id in set(missing_edges) - seen_edges:
                connection.execute(
                    edge_members.update()
                    .where(edge_members.c.scope == scope, edge_members.c.edge_id == edge_id)
                    .values(active=False)
                )
                active = connection.execute(
                    select(func.count())
                    .select_from(edge_members)
                    .where(edge_members.c.edge_id == edge_id, edge_members.c.active.is_(True))
                ).scalar_one()
                if not active:
                    self._expire_edge(connection, edge_id, scan_id, timestamp)
        connection.execute(
            scans.update()
            .where(scans.c.id == scan_id)
            .values(
                status="complete" if complete else "partial",
                finished_at=timestamp,
                summary={
                    "entities": len(result.entities),
                    "edges": len(result.edges),
                    "warnings": result.warnings,
                },
                anomalies=result.anomalies,
            )
        )

    def _expire_edge(self, connection: Connection, key: str, scan_id: str, timestamp: str) -> None:
        old = self._row(connection, edges, key)
        if old is None or old["stale"]:
            return
        data = {
            **old,
            "stale": True,
            "valid_until": timestamp,
            "version": old["version"] + 1,
            "conflict": bool(old["human_decision"]) or old["conflict"],
        }
        self._upsert(connection, edges, data)
        connection.execute(
            edge_history.insert().values(
                edge_id=key, version=data["version"], payload=data, recorded_at=timestamp
            )
        )
        self._audit(connection, key, "edge_source_disappeared", {"scan_id": scan_id})

    def get_entity(self, key: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = self._row(connection, entities, key)
        if row is None:
            raise DceError(ErrorCode.NOT_FOUND, "Catalog entity was not found.")
        return row

    def find(self, kind: str, key: str, source: str | None = None) -> dict[str, Any]:
        query = select(entities).where(
            entities.c.kind == kind,
            or_(entities.c.id == key, entities.c.external_id == key),
            entities.c.deleted.is_(False),
        )
        if source:
            query = query.where(entities.c.source_instance == source)
        with self.engine.connect() as connection:
            rows = connection.execute(query.limit(2)).mappings().all()
        if not rows:
            raise DceError(ErrorCode.NOT_FOUND, "Resource was not found in catalog.")
        if len(rows) > 1:
            raise DceError(
                ErrorCode.SNAPSHOT_CONFLICT, "Ambiguous resource ID; use source instance or UUID."
            )
        return dict(rows[0])

    def anomalies(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        self._page(limit, offset)
        found: list[dict[str, Any]] = []
        seen = set()
        with self.engine.connect() as connection:
            for row in connection.execute(
                select(scans)
                .where(scans.c.status == "complete")
                .order_by(scans.c.started_at.desc())
            ).mappings():
                if row["scope"] in seen or row["scope"].startswith("mapping"):
                    continue
                seen.add(row["scope"])
                found.extend(row["anomalies"])
        return {
            "items": found[offset : offset + limit],
            "more_available": len(found) > offset + limit,
            "cursor": offset + limit if len(found) > offset + limit else None,
        }

    def edge(self, key: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = self._row(connection, edges, key)
        if row is None:
            raise DceError(ErrorCode.NOT_FOUND, "Catalog edge was not found.")
        return row

    def counts(self) -> dict[str, int]:
        with self.engine.connect() as connection:
            return {
                table.name: connection.execute(select(func.count()).select_from(table)).scalar_one()
                for table in (entities, edges, evidence, snapshots)
            }

    def list_entities(
        self, *, kind: str | None = None, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        self._page(limit, offset)
        query = select(entities).where(entities.c.deleted.is_(False))
        if kind:
            query = query.where(entities.c.kind == kind)
        with self.engine.connect() as connection:
            rows = (
                connection.execute(query.order_by(entities.c.id).offset(offset).limit(limit + 1))
                .mappings()
                .all()
            )
        return {
            "items": [dict(row) for row in rows[:limit]],
            "more_available": len(rows) > limit,
            "cursor": offset + limit if len(rows) > limit else None,
        }

    @staticmethod
    def _page(limit: int, offset: int) -> None:
        if not 1 <= limit <= 100 or offset < 0:
            raise DceError(
                ErrorCode.INVALID_PAYLOAD, "Page limit must be 1..100; offset nonnegative."
            )

    def history(self, key: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(entity_history)
                    .where(entity_history.c.entity_id == key)
                    .order_by(entity_history.c.version)
                ).mappings()
            ]

    def edge_versions(self, key: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(edge_history)
                    .where(edge_history.c.edge_id == key)
                    .order_by(edge_history.c.version)
                ).mappings()
            ]

    def get_evidence(self, keys: list[str]) -> list[dict[str, Any]]:
        if len(keys) > 100:
            raise DceError(
                ErrorCode.INVALID_PAYLOAD, "Evidence query is limited to 100 references."
            )
        with self.engine.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(evidence).where(evidence.c.id.in_(keys)).order_by(evidence.c.id)
                ).mappings()
            ]

    def snapshot(self, key: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = self._row(connection, snapshots, key)
        if row is None:
            raise DceError(ErrorCode.NOT_FOUND, "Snapshot was not found.")
        return row

    def list_edges(
        self, *, status: str | None = None, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        self._page(limit, offset)
        query = select(edges).where(edges.c.deleted.is_(False))
        if status:
            query = query.where(edges.c.status == status)
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    query.order_by(
                        edges.c.stale,
                        edges.c.conflict,
                        case(
                            (edges.c.status == "confirmed", 0),
                            (edges.c.status == "observed_verified", 1),
                            (edges.c.status == "candidate", 2),
                            else_=3,
                        ),
                        edges.c.confidence.desc(),
                        edges.c.id,
                    )
                    .offset(offset)
                    .limit(limit + 1)
                )
                .mappings()
                .all()
            )
        return {
            "items": [dict(row) for row in rows[:limit]],
            "more_available": len(rows) > limit,
            "cursor": offset + limit if len(rows) > limit else None,
        }

    def scan_status(self, *, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        self._page(limit, offset)
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    select(scans)
                    .order_by(scans.c.started_at.desc())
                    .limit(limit + 1)
                    .offset(offset)
                )
                .mappings()
                .all()
            )
        return {"items": [dict(row) for row in rows[:limit]], "more_available": len(rows) > limit}

    def get_scan(self, key: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = self._row(connection, scans, key)
        if row is None:
            raise DceError(ErrorCode.NOT_FOUND, "Scan was not found.")
        return row

    def pending_reviews(self) -> int:
        with self.engine.connect() as connection:
            return int(
                connection.execute(
                    select(func.count())
                    .select_from(edges)
                    .where(
                        edges.c.status.in_(["candidate", "unresolved"]),
                        edges.c.stale.is_(False),
                        edges.c.deleted.is_(False),
                    )
                ).scalar_one()
            )

    def trace(
        self, key: str, *, direction: str = "both", max_depth: int = 2, limit: int = 20
    ) -> dict[str, Any]:
        if (
            direction not in {"in", "out", "both"}
            or not 0 <= max_depth <= 5
            or not 1 <= limit <= 100
        ):
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid trace direction/depth/limit.")
        self.get_entity(key)
        found: dict[str, dict[str, Any]] = {}
        frontier, visited = {key}, {key}
        more = False
        with self.engine.connect() as connection:
            for _ in range(max_depth):
                predicates = []
                if direction in {"out", "both"}:
                    predicates.append(edges.c.source_id.in_(frontier))
                if direction in {"in", "both"}:
                    predicates.append(edges.c.target_id.in_(frontier))
                rows = (
                    connection.execute(
                        select(edges)
                        .where(or_(*predicates), edges.c.deleted.is_(False))
                        .order_by(edges.c.id)
                        .limit(limit + 1)
                    )
                    .mappings()
                    .all()
                )
                following: set[str] = set()
                for row in rows:
                    if row["id"] not in found:
                        if len(found) == limit:
                            more = True
                            break
                        found[row["id"]] = dict(row)
                    following.update((row["source_id"], row["target_id"]))
                frontier = following - visited
                visited.update(following)
                if not frontier or more:
                    break
        return {
            "resource": key,
            "edges": list(found.values()),
            "more_available": more,
            "direction": direction,
            "max_depth": max_depth,
        }

    def read_graph(self) -> DiscoveryResult:
        with self.engine.connect() as connection:
            return DiscoveryResult(
                entities=[
                    Entity.model_validate(dict(row))
                    for row in connection.execute(
                        select(entities).where(entities.c.deleted.is_(False))
                    ).mappings()
                ],
                snapshots=[
                    Snapshot.model_validate(dict(row))
                    for row in connection.execute(select(snapshots)).mappings()
                ],
                evidence=[
                    Evidence.model_validate(dict(row))
                    for row in connection.execute(select(evidence)).mappings()
                ],
                edges=[
                    Edge.model_validate({**dict(row), "status": row["observed_status"]})
                    for row in connection.execute(
                        select(edges).where(edges.c.stale.is_(False), edges.c.deleted.is_(False))
                    ).mappings()
                ],
            )

    def review(
        self, key: str, *, action: str, actor: str, reason: str, expected_version: int | None = None
    ) -> None:
        if (
            action not in {"accept", "reject", "revoke", "override"}
            or not actor.strip()
            or not reason.strip()
        ):
            raise DceError(
                ErrorCode.REVIEW_REQUIRED, "Explicit human action, actor and reason required."
            )
        with self.engine.begin() as connection:
            old = self._row(connection, edges, key)
            if old is None:
                raise DceError(ErrorCode.NOT_FOUND, "Catalog edge was not found.")
            if expected_version is not None and old["version"] != expected_version:
                raise DceError(
                    ErrorCode.SNAPSHOT_CONFLICT, "Review version changed; refresh preview."
                )
            data = {
                **old,
                "status": {
                    "accept": "confirmed",
                    "override": "confirmed",
                    "reject": "rejected",
                    "revoke": old["observed_status"],
                }[action],
                "human_decision": None if action == "revoke" else action,
                "conflict": False,
                "version": old["version"] + 1,
            }
            self._upsert(connection, edges, data)
            connection.execute(
                edge_history.insert().values(
                    edge_id=key, version=data["version"], payload=data, recorded_at=now()
                )
            )
            review_id = str(uuid4())
            connection.execute(
                approvals.insert().values(
                    id=review_id,
                    edge_id=key,
                    action=action,
                    actor=actor,
                    reason=reason,
                    timestamp=now(),
                    before=old,
                    after=data,
                )
            )
            self._audit(
                connection,
                key,
                f"review_{action}",
                {"review_id": review_id, "actor": actor, "reason": reason},
            )

    def record_mapping_run(self, status: str, suggested: int) -> str:
        scan_id = str(uuid4())
        with self.engine.begin() as connection:
            connection.execute(
                scans.insert().values(
                    id=scan_id,
                    scope="mapping-ai",
                    status="complete" if status in {"ok", "disabled"} else "failed",
                    started_at=now(),
                    finished_at=now(),
                    summary={"ai_status": status, "suggested": suggested},
                    anomalies=[],
                )
            )
        return scan_id

    def reviews(self, key: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(approvals)
                    .where(approvals.c.edge_id == key)
                    .order_by(approvals.c.timestamp)
                ).mappings()
            ]

    def audit(self, key: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(audit_log)
                    .where(audit_log.c.resource_id == key)
                    .order_by(audit_log.c.timestamp)
                ).mappings()
            ]
