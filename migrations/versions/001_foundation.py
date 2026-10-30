"""Immutable evidence, durable jobs and versioned research artifacts."""

from pathlib import Path
from alembic import op

revision = "001"
down_revision = None


def upgrade():
    # Driver SQL permits PostgreSQL-specific FTS/vector DDL in a readable migration.
    op.get_bind().exec_driver_sql(Path("migrations/schema.sql").read_text())


def downgrade():
    raise RuntimeError("Destructive downgrade disabled; restore a reviewed backup instead")
