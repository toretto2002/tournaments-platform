"""Endpoint pubblico JWKS: espone la chiave pubblica per la verifica dei JWT.

Nessuna autenticazione richiesta: e' il documento che i verificatori (altri
servizi, gateway) usano per validare la firma EdDSA dei JWT emessi da identity.
"""

from typing import Any

from fastapi import APIRouter

from app.domain.security import build_jwks

router = APIRouter(tags=["jwks"])


@router.get("/.well-known/jwks.json")
async def get_jwks() -> dict[str, Any]:
    """Ritorna il documento JWKS pubblico."""
    return build_jwks()
