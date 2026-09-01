"""Primitive di sicurezza riutilizzabili: hashing password, JWT (EdDSA), JWKS.

Layer puro e testabile in isolamento: non dipende dal DB ne' da FastAPI.

- Password: Argon2id via argon2-cffi.
- JWT: firma/verifica EdDSA (Ed25519) via PyJWT + cryptography.
- Le chiavi Ed25519 sono file PEM su disco (path in Settings), MAI generate a
  runtime: vedi scripts/generate_keys.py.
"""

from __future__ import annotations

import base64
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from app.config import get_settings

_password_hasher = PasswordHasher()


# ---------------------------------------------------------------------------
# Password hashing (Argon2id)
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Calcola l'hash Argon2id della password in chiaro."""
    return _password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una password contro il suo hash Argon2id.

    Ritorna False su mismatch, non solleva mai eccezioni al chiamante.
    """
    try:
        return _password_hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False


# ---------------------------------------------------------------------------
# Caricamento chiavi Ed25519 (con cache)
# ---------------------------------------------------------------------------


class KeyMaterialNotFoundError(RuntimeError):
    """Sollevato quando i file di chiave JWT configurati non esistono su disco."""


def _read_key_file(path_str: str) -> bytes:
    path = Path(path_str)
    if not path.exists():
        raise KeyMaterialNotFoundError(
            f"Chiave JWT non trovata in '{path}'. "
            "Generala con: uv run python scripts/generate_keys.py"
        )
    return path.read_bytes()


@lru_cache
def load_private_key() -> Ed25519PrivateKey:
    """Carica (con cache) la chiave privata Ed25519 usata per firmare i JWT."""
    settings = get_settings()
    pem_bytes = _read_key_file(settings.jwt_private_key_path)
    key = serialization.load_pem_private_key(pem_bytes, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise KeyMaterialNotFoundError(
            f"Il file '{settings.jwt_private_key_path}' non contiene una chiave Ed25519."
        )
    return key


@lru_cache
def load_public_key() -> Ed25519PublicKey:
    """Carica (con cache) la chiave pubblica Ed25519 usata per verificare i JWT."""
    settings = get_settings()
    pem_bytes = _read_key_file(settings.jwt_public_key_path)
    key = serialization.load_pem_public_key(pem_bytes)
    if not isinstance(key, Ed25519PublicKey):
        raise KeyMaterialNotFoundError(
            f"Il file '{settings.jwt_public_key_path}' non contiene una chiave Ed25519."
        )
    return key


# ---------------------------------------------------------------------------
# JWT (EdDSA / Ed25519)
# ---------------------------------------------------------------------------


def create_access_token(sub: str, roles: list[str]) -> str:
    """Crea un access token JWT firmato EdDSA per l'utente `sub` con i ruoli dati.

    NON include l'email nei claim: solo sub (user id), roles, type, iat, exp,
    iss e jti.
    """
    settings = get_settings()
    private_key = load_private_key()

    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": sub,
        "roles": roles,
        "type": "access",
        "iat": now,
        "exp": now + settings.access_token_ttl_seconds,
        "iss": settings.jwt_issuer,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(
        claims,
        private_key,
        algorithm="EdDSA",
        headers={"kid": settings.jwt_kid},
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decodifica e verifica un JWT: firma (EdDSA), issuer e scadenza.

    Solleva jwt.InvalidTokenError (o una sua sottoclasse, es.
    jwt.ExpiredSignatureError, jwt.InvalidIssuerError, jwt.InvalidSignatureError)
    se il token non e' valido: il chiamante puo' gestirla con un except
    jwt.InvalidTokenError.
    """
    settings = get_settings()
    public_key = load_public_key()

    return jwt.decode(
        token,
        public_key,
        algorithms=["EdDSA"],
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "iat", "iss", "sub"]},
    )


# ---------------------------------------------------------------------------
# JWKS
# ---------------------------------------------------------------------------


def _b64url_no_padding(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def build_jwks() -> dict[str, Any]:
    """Costruisce il documento JWKS pubblico per la chiave Ed25519 corrente."""
    settings = get_settings()
    public_key = load_public_key()

    raw_public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    return {
        "keys": [
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "x": _b64url_no_padding(raw_public_bytes),
                "use": "sig",
                "alg": "EdDSA",
                "kid": settings.jwt_kid,
            }
        ]
    }
