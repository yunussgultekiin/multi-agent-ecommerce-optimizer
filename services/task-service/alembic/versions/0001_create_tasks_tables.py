from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

task_status_enum = sa.Enum(
    "pending", "running", "completed", "failed", "cancelled",
    name="taskstatus",
)


def upgrade() -> None:
    task_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "running", "completed", "failed", "cancelled",
                name="taskstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("input_url", sa.String(), nullable=False),
        sa.Column("keywords", ARRAY(sa.String()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"])

    op.create_table(
        "analysisresults",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("result", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_analysisresults_task_id", "analysisresults", ["task_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_analysisresults_task_id", table_name="analysisresults")
    op.drop_table("analysisresults")

    op.drop_index("ix_tasks_created_at", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_user_id", table_name="tasks")
    op.drop_table("tasks")

    task_status_enum.drop(op.get_bind(), checkfirst=True)
