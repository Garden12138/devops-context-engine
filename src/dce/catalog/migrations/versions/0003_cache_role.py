"""Downgrade authority, preserve all resource/edge/approval/history rows."""

from alembic import op

from dce.catalog.schema import catalog_metadata

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    catalog_metadata.create(connection)
    connection.execute(
        catalog_metadata.insert(),
        [
            {"key": "role", "value": "resource_cache_and_history"},
            {"key": "relationship_authority", "value": "host_project_context"},
            {"key": "legacy_tools", "value": "retained_revision_1.1"},
        ],
    )


def downgrade() -> None:
    raise RuntimeError("Restore the pre-migration backup; downgrade does not discard metadata.")
