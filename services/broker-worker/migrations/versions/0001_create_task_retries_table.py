from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from typing import Sequence, Union

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "task_retries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", sa.String(255), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(1000), nullable=True),
        sa.Column(
            "next_retry_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_task_retries_task_id", "task_retries", ["task_id"])

def downgrade() -> None:
    op.drop_index("ix_task_retries_task_id", table_name="task_retries")
    op.drop_table("task_retries")
