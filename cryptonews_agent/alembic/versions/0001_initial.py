from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from src.db.models import EmbeddingType, SourceEnum, StringArray

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source", sa.Enum(SourceEnum), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lang", sa.String(length=5), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.Column("tickers", StringArray(), nullable=True),
        sa.Column("entities", sa.JSON(), nullable=True),
        sa.Column("topics", StringArray(), nullable=True),
        sa.Column("sentiment", sa.SmallInteger(), nullable=True),
        sa.Column("stance", sa.String(length=16), nullable=True),
        sa.Column("impact", sa.SmallInteger(), nullable=True),
        sa.Column("embedding", EmbeddingType(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_items_source_published_at",
        "items",
        ["source", "published_at"],
    )
    op.create_index("ix_items_topics", "items", ["topics"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_items_topics", table_name="items")
    op.drop_index("ix_items_source_published_at", table_name="items")
    op.drop_table("items")
