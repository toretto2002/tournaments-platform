"""Test unitari per l'hashing delle password (Argon2id).

Non richiedono DB ne' chiavi JWT.
"""

from app.domain.security import hash_password, verify_password


def test_hash_password_differs_from_plain() -> None:
    hashed = hash_password("Sup3rSecret!")
    assert hashed != "Sup3rSecret!"


def test_verify_password_correct_plain_returns_true() -> None:
    hashed = hash_password("Sup3rSecret!")
    assert verify_password("Sup3rSecret!", hashed) is True


def test_verify_password_wrong_plain_returns_false() -> None:
    hashed = hash_password("Sup3rSecret!")
    assert verify_password("WrongPassword!", hashed) is False


def test_hash_password_uses_random_salt() -> None:
    first = hash_password("Sup3rSecret!")
    second = hash_password("Sup3rSecret!")
    assert first != second
