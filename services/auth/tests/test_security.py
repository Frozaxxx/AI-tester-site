import uuid
from datetime import timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.infrastructure.security.passwords import hash_password, verify_password
from app.infrastructure.security.tokens import JwtIssuer, hash_refresh_token, new_refresh_token


@pytest.fixture(scope="module")
def private_key_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


def test_password_hash() -> None:
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip(private_key_pem: str) -> None:
    issuer = JwtIssuer(private_key_pem, ttl=timedelta(minutes=15))
    user_id = uuid.uuid4()
    access = issuer.issue(user_id)
    payload = issuer.decode(access.token)
    assert payload["sub"] == str(user_id)
    assert payload["jti"] == access.jti
    assert payload["type"] == "access"
    assert "email" not in payload


def test_token_with_wrong_audience_is_rejected(private_key_pem: str) -> None:
    payload = {"sub": "1", "jti": "x", "exp": 9999999999, "iss": "ai-tester-auth", "aud": "other"}
    token = jwt.encode(payload, private_key_pem, algorithm="RS256")
    issuer = JwtIssuer(private_key_pem, ttl=timedelta(minutes=15))
    with pytest.raises(jwt.InvalidAudienceError):
        issuer.decode(token)


def test_expired_access_token(private_key_pem: str) -> None:
    issuer = JwtIssuer(private_key_pem, ttl=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        issuer.decode(issuer.issue(uuid.uuid4()).token)


def test_token_signed_by_another_key_is_rejected(private_key_pem: str) -> None:
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    forged = JwtIssuer(other_pem, ttl=timedelta(minutes=15)).issue(uuid.uuid4())
    issuer = JwtIssuer(private_key_pem, ttl=timedelta(minutes=15))
    with pytest.raises(jwt.InvalidSignatureError):
        issuer.decode(forged.token)


def test_refresh_token() -> None:
    token, token_hash = new_refresh_token()
    assert token != token_hash
    assert hash_refresh_token(token) == token_hash
    assert new_refresh_token()[0] != token
