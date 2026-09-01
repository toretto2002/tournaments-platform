"""Modelli SQLAlchemy 2.0 (Mapped/mapped_column) del servizio identity.

Fedeli allo schema in docs/schema_er_tornei_v1.dbml (sezione [IDENTITY]) per
users e user_roles. refresh_tokens e outbox sono infrastruttura interna al
servizio (non presenti nel DBML).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRoleEnum(str, enum.Enum):
    """Valori dell'enum Postgres nativo user_role_enum.

    CAPTAIN non e' presente di proposito: e' contestuale al team (vedi
    team_members.is_captain nel servizio team-roster), non un ruolo globale.
    """

    PLAYER = "PLAYER"
    ORGANIZER = "ORGANIZER"


class User(Base):
    """Utente unico della piattaforma."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list["UserRole"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")


class UserRole(Base):
    """Ruoli GLOBALI assegnati a un utente (PLAYER, ORGANIZER)."""

    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role: Mapped[UserRoleEnum] = mapped_column(
        # create_type=False: la creazione/drop del tipo Postgres nativo
        # user_role_enum e' gestita esplicitamente dalle migration Alembic.
        SQLEnum(UserRoleEnum, name="user_role_enum", create_type=False),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="roles")


class RefreshToken(Base):
    """Refresh token emessi per un utente. Infrastruttura interna al servizio."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class Outbox(Base):
    """Tabella outbox per il relay eventi verso Kafka. Infrastruttura interna al servizio."""

    __tablename__ = "outbox"
    __table_args__ = (Index("ix_outbox_published_at", "published_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
