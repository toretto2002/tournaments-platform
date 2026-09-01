"""Modelli SQLAlchemy del servizio identity.

Importati qui in modo che app.db.Base.metadata li conosca (usato da Alembic
per l'autogenerate e da eventuali create_all in test).
"""

from app.models.user import Outbox, RefreshToken, User, UserRole, UserRoleEnum

__all__ = ["Outbox", "RefreshToken", "User", "UserRole", "UserRoleEnum"]
