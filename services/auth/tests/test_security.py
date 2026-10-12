import uuid

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import settings
from app.domain.exceptions import UnauthorizedError
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)


def test_password_hash() -> None:
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_long_cyrillic_password() -> None:
    password = "я" * 128
    assert verify_password(password, hash_password(password))


def test_broken_hash_is_not_an_error() -> None:
    assert not verify_password("secret123", "not-a-hash")


def test_access_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    access = create_access_token(user_id)
    payload = decode_access_token(access.token)
    assert payload["sub"] == str(user_id)
    assert payload["jti"] == access.jti
    assert "email" not in payload


def test_token_signed_by_another_key_is_rejected() -> None:
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    payload = {
        "sub": "1",
        "jti": "x",
        "exp": 9999999999,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "type": "access",
    }
    with pytest.raises(UnauthorizedError):
        decode_access_token(jwt.encode(payload, other_pem, algorithm=settings.jwt_algorithm))


def test_refresh_token() -> None:
    token, token_hash = new_refresh_token()
    assert hash_refresh_token(token) == token_hash != token
