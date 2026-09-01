"""Test unitari per la creazione/verifica dei JWT di accesso (EdDSA/Ed25519).

Usano la fixture `test_settings` (vedi conftest.py): chiavi effimere in
tmp_path, nessuna dipendenza da keys/ reali o dal .env di sviluppo.
"""

from __future__ import annotations

import time

import jwt
import pytest

from app.config import get_settings
from app.domain import security


def test_create_and_decode_round_trip(test_settings: None) -> None:
    token = security.create_access_token(sub="user-123", roles=["PLAYER"])
    claims = security.decode_token(token)

    assert claims["sub"] == "user-123"
    assert claims["roles"] == ["PLAYER"]
    assert claims["type"] == "access"
    assert "email" not in claims


def test_header_has_expected_kid_and_alg(test_settings: None) -> None:
    token = security.create_access_token(sub="user-123", roles=["PLAYER"])
    header = jwt.get_unverified_header(token)

    settings = get_settings()
    assert header["kid"] == settings.jwt_kid
    assert header["alg"] == "EdDSA"


def test_tampered_signature_is_rejected(test_settings: None) -> None:
    token = security.create_access_token(sub="user-123", roles=["PLAYER"])
    header_part, payload_part, signature_part = token.split(".")
    tampered_signature = ("A" if signature_part[0] != "A" else "B") + signature_part[1:]
    tampered_token = f"{header_part}.{payload_part}.{tampered_signature}"

    with pytest.raises(jwt.InvalidTokenError):
        security.decode_token(tampered_token)


def test_wrong_issuer_is_rejected(test_settings: None, monkeypatch: pytest.MonkeyPatch) -> None:
    token = security.create_access_token(sub="user-123", roles=["PLAYER"])

    monkeypatch.setenv("JWT_ISSUER", "someone-else")
    get_settings.cache_clear()

    with pytest.raises(jwt.InvalidTokenError):
        security.decode_token(token)


def test_expired_token_is_rejected(test_settings: None) -> None:
    settings = get_settings()
    private_key = security.load_private_key()
    now = int(time.time())
    expired_token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["PLAYER"],
            "type": "access",
            "iat": now - 3600,
            "exp": now - 1,
            "iss": settings.jwt_issuer,
            "jti": "test-jti",
        },
        private_key,
        algorithm="EdDSA",
        headers={"kid": settings.jwt_kid},
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_token(expired_token)
