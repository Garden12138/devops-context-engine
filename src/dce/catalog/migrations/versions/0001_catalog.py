"""Initial catalog schema."""

from alembic import op

from dce.catalog.schema import metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    metadata.create_all(
        op.get_bind(),
        tables=[
            t
            for t in metadata.sorted_tables
            if t.name
            in {
                "entities",
                "snapshots",
                "evidence",
                "edges",
                "scan_runs",
                "scope_members",
                "edge_scope_members",
                "approvals",
                "audit",
            }
        ],
    )


def downgrade() -> None:
    raise RuntimeError("Catalog downgrade is unsupported; restore a local backup.")
