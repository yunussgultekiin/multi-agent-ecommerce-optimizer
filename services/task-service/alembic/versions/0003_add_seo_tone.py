from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("tasks", sa.Column("seo_tone", sa.String(length=64), nullable=True))

def downgrade() -> None:
    op.drop_column("tasks", "seo_tone")
