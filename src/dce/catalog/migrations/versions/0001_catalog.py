"""Initial catalog schema."""

from alembic import op

from dce.catalog.schema import edge_history, entity_history, metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    metadata.create_all(
        op.get_bind(),
        tables=[t for t in metadata.sorted_tables if t not in (entity_history, edge_history)],
    )


def downgrade() -> None:
    raise RuntimeError("Catalog downgrade is unsupported; restore a local backup.")
