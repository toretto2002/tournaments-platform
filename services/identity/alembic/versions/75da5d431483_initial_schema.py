"""initial schema

Migration manuale (non autogenerate): crea l'enum Postgres nativo
user_role_enum e le tabelle users, user_roles (da docs/schema_er_tornei_v1.dbml,
sezione [IDENTITY]) piu' refresh_tokens e outbox (infrastruttura interna al
servizio identity, non presenti nel DBML).

Revision ID: 75da5d431483
Revises:
Create Date: 2026-09-01 00:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "75da5d431483"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False: la creazione/drop del tipo e' gestita esplicitamente
# sotto (prima della tabella che lo usa in upgrade, dopo il drop table in
# downgrade), invece di lasciarla come side-effect implicito di create_table.
user_role_enum = postgresql.ENUM("PLAYER", "ORGANIZER", name="user_role_enum", create_type=False)


def upgrade() -> None:
    # 1) Enum nativo Postgres, PRIMA di qualunque tabella che lo referenzia.
    user_role_enum.create(op.get_bind(), checkfirst=True)

    # 2) users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # 3) user_roles — ruoli globali (PLAYER, ORGANIZER); CAPTAIN e' contestuale
    #    al team in un altro servizio, non modellato qui.
    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_user_roles_user_id_users"),
            nullable=False,
        ),
        sa.Column("role", user_role_enum, nullable=False),
    )
    op.create_unique_constraint("uq_user_roles_user_id_role", "user_roles", ["user_id", "role"])

    # 4) refresh_tokens — infrastruttura interna al servizio (non nel DBML).
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_refresh_tokens_user_id_users"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # 5) outbox — infrastruttura interna al servizio (non nel DBML), con
    #    indice su published_at per il polling del relay verso Kafka.
    op.create_table(
        "outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_published_at", "outbox", ["published_at"])


def downgrade() -> None:
    op.drop_index("ix_outbox_published_at", table_name="outbox")
    op.drop_table("outbox")

    op.drop_table("refresh_tokens")

    op.drop_constraint("uq_user_roles_user_id_role", "user_roles", type_="unique")
    op.drop_table("user_roles")

    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_table("users")

    # Enum droppato per ultimo, dopo la tabella che lo usa.
    user_role_enum.drop(op.get_bind(), checkfirst=True)
