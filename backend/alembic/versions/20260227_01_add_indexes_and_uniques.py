"""add indexes and unique constraints for ingestion and query hotspots

Revision ID: 20260227_01
Revises:
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260227_01"
down_revision = None
branch_labels = None
depends_on = None


def _assert_no_duplicates(bind, table: str) -> None:
    duplicate_query = sa.text(
        f"""
        SELECT platform, external_id, COUNT(*) AS c
        FROM {table}
        GROUP BY platform, external_id
        HAVING COUNT(*) > 1
        LIMIT 1
        """
    )
    has_duplicate = bind.execute(duplicate_query).first()
    if has_duplicate:
        raise RuntimeError(
            f"Duplicate rows found in {table} for (platform, external_id). "
            "Backfill/cleanup duplicates before running this migration."
        )


def upgrade() -> None:
    bind = op.get_bind()

    # Safety checks before creating unique constraints.
    _assert_no_duplicates(bind, "posts")
    _assert_no_duplicates(bind, "comments")

    with op.batch_alter_table("posts") as batch_op:
        batch_op.create_index(
            "ix_posts_topic_created_utc", ["topic_id", "created_utc"], unique=False
        )
        batch_op.create_unique_constraint(
            "uq_posts_platform_external_id", ["platform", "external_id"]
        )

    with op.batch_alter_table("comments") as batch_op:
        batch_op.create_index(
            "ix_comments_topic_created_utc", ["topic_id", "created_utc"], unique=False
        )
        batch_op.create_unique_constraint(
            "uq_comments_platform_external_id", ["platform", "external_id"]
        )

    with op.batch_alter_table("classifications") as batch_op:
        batch_op.create_index("ix_classifications_stance", ["stance"], unique=False)
        batch_op.create_unique_constraint(
            "uq_classifications_comment_id", ["comment_id"]
        )

    with op.batch_alter_table("daily_stats") as batch_op:
        batch_op.create_index("ix_daily_stats_topic_date", ["topic_id", "date"])


def downgrade() -> None:
    with op.batch_alter_table("daily_stats") as batch_op:
        batch_op.drop_index("ix_daily_stats_topic_date")

    with op.batch_alter_table("classifications") as batch_op:
        batch_op.drop_constraint("uq_classifications_comment_id", type_="unique")
        batch_op.drop_index("ix_classifications_stance")

    with op.batch_alter_table("comments") as batch_op:
        batch_op.drop_constraint("uq_comments_platform_external_id", type_="unique")
        batch_op.drop_index("ix_comments_topic_created_utc")

    with op.batch_alter_table("posts") as batch_op:
        batch_op.drop_constraint("uq_posts_platform_external_id", type_="unique")
        batch_op.drop_index("ix_posts_topic_created_utc")
