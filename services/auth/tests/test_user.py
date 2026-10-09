import pytest

from app.domain.exceptions import DomainError
from app.domain.services.user import create_user, validate_password


def test_email_is_normalized() -> None:
    user = create_user(email="  Andrey@Example.COM ", password_hash="hash")
    assert user.email == "andrey@example.com"


@pytest.mark.parametrize("email", ["", "andrey", "andrey@", "@example.com", "a b@example.com"])
def test_invalid_email(email: str) -> None:
    with pytest.raises(DomainError):
        create_user(email=email, password_hash="hash")


@pytest.mark.parametrize("password", ["short", "x" * 129])
def test_invalid_password(password: str) -> None:
    with pytest.raises(DomainError):
        validate_password(password)


def test_valid_password() -> None:
    validate_password("secret123")
