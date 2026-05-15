from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE seotone AS ENUM ('samimi', 'profesyonel', 'premium'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    ))
    op.add_column(
        "tasks",
        sa.Column(
            "seo_tone",
            sa.Enum("samimi", "profesyonel", "premium", name="seotone", create_type=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("tasks", "seo_tone")
    op.execute(sa.text("DROP TYPE IF EXISTS seotone"))
