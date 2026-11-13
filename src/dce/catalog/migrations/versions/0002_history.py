"""Version history with backfill for existing observations."""

from alembic import op
from sqlalchemy import select

from dce.catalog.schema import edge_history, edges, entities, entity_history

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    entity_history.create(connection)
    edge_history.create(connection)
    for entity in connection.execute(select(entities)).mappings():
        connection.execute(
            entity_history.insert().values(
                entity_id=entity["id"],
                version=entity["version"],
                attributes=entity["attributes"],
                deleted=entity["deleted"],
                recorded_at=entity["last_verified"],
            )
        )
    for edge in connection.execute(select(edges)).mappings():
        connection.execute(
            edge_history.insert().values(
                edge_id=edge["id"],
                version=edge["version"],
                payload=dict(edge),
                recorded_at=edge["last_verified"],
            )
        )


def downgrade() -> None:
    raise RuntimeError("Catalog downgrade is unsupported; restore a local backup.")
