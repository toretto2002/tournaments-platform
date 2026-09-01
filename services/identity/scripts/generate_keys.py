"""Genera la coppia di chiavi Ed25519 per la firma dei JWT (EdDSA).

Scrive la chiave privata in formato PEM PKCS8 (non cifrata) e la chiave
pubblica in formato PEM SubjectPublicKeyInfo, nei path configurati in
app.config.Settings (JWT_PRIVATE_KEY_PATH / JWT_PUBLIC_KEY_PATH). Le chiavi
NON vengono mai generate a runtime dal servizio: questo script va lanciato
manualmente (una volta per ambiente) prima di avviare identity.

Uso:
    uv run python scripts/generate_keys.py [--force]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Permette `uv run python scripts/generate_keys.py` dalla root del servizio
# (services/identity), dove app/ non e' altrimenti sul sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402


def generate_keys(force: bool = False) -> None:
    settings = get_settings()
    private_path = Path(settings.jwt_private_key_path)
    public_path = Path(settings.jwt_public_key_path)

    if not force and (private_path.exists() or public_path.exists()):
        print(
            f"[generate_keys] Chiavi gia' presenti ({private_path} / {public_path}): "
            "NON sovrascritte. Usa --force per rigenerarle."
        )
        return

    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)

    print(f"[generate_keys] Chiave privata scritta in: {private_path.resolve()}")
    print(f"[generate_keys] Chiave pubblica scritta in: {public_path.resolve()}")
    print(f"[generate_keys] kid configurato (JWT_KID): {settings.jwt_kid}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sovrascrive le chiavi esistenti, se presenti.",
    )
    args = parser.parse_args()
    generate_keys(force=args.force)


if __name__ == "__main__":
    main()
