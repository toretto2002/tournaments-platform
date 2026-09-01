"""Configurazione del servizio, letta da variabili d'ambiente / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    APP_NAME: str
    app_env: str = "local"
    log_level: str = "info"
    PORT: int
    DATABASE_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_CONSUMER_GROUP: str

    # --- Sicurezza / JWT (EdDSA - Ed25519) ---
    jwt_private_key_path: str = "keys/jwt_ed25519_private.pem"
    jwt_public_key_path: str = "keys/jwt_ed25519_public.pem"
    jwt_issuer: str = "identity"
    jwt_kid: str = "identity-ed25519-1"  # key id, deve combaciare col JWKS
    access_token_ttl_seconds: int = 1800  # 30 minuti


@lru_cache
def get_settings() -> Settings:
    return Settings()
