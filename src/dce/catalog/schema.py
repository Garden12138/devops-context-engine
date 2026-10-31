from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)

metadata = MetaData()

entities = Table(
    "entities",
    metadata,
    Column("id", String, primary_key=True),
    Column("source_instance", String, nullable=False),
    Column("kind", String, nullable=False),
    Column("external_id", String, nullable=False),
    Column("attributes", JSON, nullable=False),
    Column("version", Integer, nullable=False),
    Column("deleted", Boolean, nullable=False, default=False),
    Column("first_seen", String, nullable=False),
    Column("last_verified", String, nullable=False),
    UniqueConstraint("source_instance", "kind", "external_id"),
)

snapshots = Table(
    "snapshots",
    metadata,
    Column("id", String, primary_key=True),
    Column("source_instance", String, nullable=False),
    Column("resource_key", String, nullable=False),
    Column("kind", String, nullable=False),
    Column("version", String, nullable=False),
    Column("observed_at", String, nullable=False),
    Column("last_verified", String, nullable=False),
    Column("metadata", JSON, nullable=False),
)

evidence = Table(
    "evidence",
    metadata,
    Column("id", String, primary_key=True),
    Column("snapshot_id", ForeignKey("snapshots.id"), nullable=False),
    Column("source_instance", String, nullable=False),
    Column("locator", String, nullable=False),
    Column("version", String, nullable=False),
    Column("observed_at", String, nullable=False),
    Column("summary", String, nullable=False),
)

edges = Table(
    "edges",
    metadata,
    Column("id", String, primary_key=True),
    Column("source_id", ForeignKey("entities.id"), nullable=False),
    Column("target_id", ForeignKey("entities.id"), nullable=False),
    Column("relation", String, nullable=False),
    Column("observed_status", String, nullable=False),
    Column("status", String, nullable=False),
    Column("evidence_ids", JSON, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("version", Integer, nullable=False),
    Column("human_decision", String),
    Column("conflict", Boolean, nullable=False, default=False),
    Column("stale", Boolean, nullable=False, default=False),
    Column("deleted", Boolean, nullable=False, default=False),
    Column("valid_from", String, nullable=False),
    Column("last_verified", String, nullable=False),
    Column("valid_until", String),
    UniqueConstraint("source_id", "target_id", "relation"),
)

scans = Table(
    "scan_runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("scope", String, nullable=False),
    Column("status", String, nullable=False),
    Column("started_at", String, nullable=False),
    Column("finished_at", String),
    Column("error_code", String),
    Column("summary", JSON, nullable=False),
    Column("anomalies", JSON, nullable=False),
)

members = Table(
    "scope_members",
    metadata,
    Column("scope", String, primary_key=True),
    Column("entity_id", ForeignKey("entities.id"), primary_key=True),
    Column("scan_id", ForeignKey("scan_runs.id"), nullable=False),
    Column("active", Boolean, nullable=False),
)

edge_members = Table(
    "edge_scope_members",
    metadata,
    Column("scope", String, primary_key=True),
    Column("edge_id", ForeignKey("edges.id"), primary_key=True),
    Column("scan_id", ForeignKey("scan_runs.id"), nullable=False),
    Column("active", Boolean, nullable=False),
)

approvals = Table(
    "approvals",
    metadata,
    Column("id", String, primary_key=True),
    Column("edge_id", ForeignKey("edges.id"), nullable=False),
    Column("action", String, nullable=False),
    Column("actor", String, nullable=False),
    Column("reason", String, nullable=False),
    Column("timestamp", String, nullable=False),
    Column("before", JSON, nullable=False),
    Column("after", JSON, nullable=False),
)

audit_log = Table(
    "audit",
    metadata,
    Column("id", String, primary_key=True),
    Column("resource_id", String, nullable=False),
    Column("event", String, nullable=False),
    Column("timestamp", String, nullable=False),
    Column("details", JSON, nullable=False),
)

entity_history = Table(
    "entity_history",
    metadata,
    Column("entity_id", ForeignKey("entities.id"), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("attributes", JSON, nullable=False),
    Column("deleted", Boolean, nullable=False),
    Column("recorded_at", String, nullable=False),
)

edge_history = Table(
    "edge_history",
    metadata,
    Column("edge_id", ForeignKey("edges.id"), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("recorded_at", String, nullable=False),
)
