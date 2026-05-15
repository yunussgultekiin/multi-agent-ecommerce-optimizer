from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from typing import Sequence, Union

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.drop_column("tasks", "input_url")
    op.drop_column("tasks", "keywords")
    op.add_column(
        "tasks", sa.Column("payload", JSONB(), nullable=False, server_default="{}")
    )
    op.add_column("tasks", sa.Column("error_message", sa.String(), nullable=True))
    op.alter_column("tasks", "payload", server_default=None)

def downgrade() -> None:
    op.drop_column("tasks", "error_message")
    op.drop_column("tasks", "payload")
    op.add_column("tasks", sa.Column("keywords", sa.ARRAY(sa.String()), nullable=True))
    op.add_column(
        "tasks", sa.Column("input_url", sa.String(), nullable=False, server_default="")
    )
    op.alter_column("tasks", "input_url", server_default=None)
