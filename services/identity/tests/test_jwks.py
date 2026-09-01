"""Test unitari per il documento JWKS pubblico.

Usano la fixture `test_settings` (vedi conftest.py): chiavi effimere in
tmp_path, nessuna dipendenza da keys/ reali o dal .env di sviluppo.
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.config import get_settings
from app.domain import security


def test_build_jwks_structure(test_settings: None) -> None:
    jwks = security.build_jwks()
    settings = get_settings()

    assert list(jwks.keys()) == ["keys"]
    assert len(jwks["keys"]) == 1

    key = jwks["keys"][0]
    assert key["kty"] == "OKP"
    assert key["crv"] == "Ed25519"
    assert key["kid"] == settings.jwt_kid
    assert key["use"] == "sig"
    assert key["alg"] == "EdDSA"
    assert key["x"]


def test_build_jwks_x_reconstructs_public_key(test_settings: None) -> None:
    jwks = security.build_jwks()
    x = jwks["keys"][0]["x"]

    # x e' base64url senza padding: reintegriamolo prima di decodificare.
    padding = "=" * (-len(x) % 4)
    raw = base64.urlsafe_b64decode(x + padding)
    reconstructed = Ed25519PublicKey.from_public_bytes(raw)

    expected_raw = security.load_public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    assert raw == expected_raw
    assert (
        reconstructed.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        == expected_raw
    )
