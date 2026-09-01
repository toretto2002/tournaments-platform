"""Fixture condivise per i test del servizio identity."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.config import get_settings
from app.domain import security


def _write_ephemeral_keypair(directory: Path) -> tuple[Path, Path]:
    """Genera una coppia Ed25519 effimera e la scrive come PEM in `directory`."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_path = directory / "test_jwt_ed25519_private.pem"
    public_path = directory / "test_jwt_ed25519_public.pem"

    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_path, public_path


@pytest.fixture
def test_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Isola Settings su una coppia di chiavi JWT effimera (tmp_path).

    NON dipende da keys/ reali ne' dal .env di sviluppo: tutti i campi
    obbligatori di Settings sono valorizzati esplicitamente via env var, cosi'
    che Settings() sia costruibile indipendentemente da un .env presente sul
    filesystem.
    """
    private_path, public_path = _write_ephemeral_keypair(tmp_path)

    monkeypatch.setenv("APP_NAME", "identity-test")
    monkeypatch.setenv("PORT", "8001")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    monkeypatch.setenv("KAFKA_CONSUMER_GROUP", "identity-test")
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", str(private_path))
    monkeypatch.setenv("JWT_PUBLIC_KEY_PATH", str(public_path))
    monkeypatch.setenv("JWT_ISSUER", "identity-test")
    monkeypatch.setenv("JWT_KID", "identity-test-kid")
    monkeypatch.setenv("ACCESS_TOKEN_TTL_SECONDS", "1800")

    get_settings.cache_clear()
    security.load_private_key.cache_clear()
    security.load_public_key.cache_clear()

    yield

    get_settings.cache_clear()
    security.load_private_key.cache_clear()
    security.load_public_key.cache_clear()
