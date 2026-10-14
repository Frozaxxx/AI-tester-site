import uuid
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos import Credentials, Tokens
from app.application.repos import RefreshTokenRepository, UserRepository
from app.application.services import blacklist, login_attempts
from app.config import settings
from app.domain.entities import RefreshToken, User
from app.domain.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    UnauthorizedError,
    ValidationError,
)
from app.domain.services import (
    PASSWORD_MAX_LENGTH,
    create_user,
    ensure_active,
    normalize_email,
    revoke,
    validate_password,
)
from app.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    decode_access_token,
    hash_password_async,
    hash_refresh_token,
    new_refresh_token,
    verify_password_async,
)


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        redis: Redis,
    ) -> None:
        self._session = session
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._redis = redis

    async def register(self, credentials: Credentials) -> User:
        """Регистрирует пользователя, если email ещё не занят."""
        email = normalize_email(credentials.email)
        validate_password(credentials.password)
        if await self._user_repo.get_by_email(email) is not None:
            raise EmailAlreadyExistsError

        user = create_user(email, await hash_password_async(credentials.password))
        await self._user_repo.add(user)
        await self._session.commit()
        return user

    async def login(self, credentials: Credentials) -> Tokens:
        """Проверяет email и пароль и выдаёт пару токенов."""
        try:
            email = normalize_email(credentials.email)
        except ValidationError:
            raise InvalidCredentialsError from None
        if len(credentials.password) > PASSWORD_MAX_LENGTH:
            raise InvalidCredentialsError

        await login_attempts.register_attempt(self._redis, email)

        user = await self._user_repo.get_by_email(email)
        password_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
        password_ok = await verify_password_async(credentials.password, password_hash)
        if user is None or not password_ok:
            raise InvalidCredentialsError

        await login_attempts.reset(self._redis, email)
        tokens = await self._issue_tokens(user)
        await self._session.commit()
        return tokens

    async def refresh(self, refresh_token: str | None) -> Tokens:
        """Выдаёт новую пару токенов, а при повторном использовании токена отзывает все сессии."""
        if not refresh_token:
            raise UnauthorizedError
        token = await self._token_repo.get_by_hash(hash_refresh_token(refresh_token))
        if token is None:
            raise UnauthorizedError

        now = datetime.now(UTC)
        if token.revoked_at is not None:
            await self._token_repo.revoke_all(token.user_id, now)
            await self._session.commit()
            raise UnauthorizedError("Токен уже использован, войдите заново")
        ensure_active(token, now)

        user = await self._user_repo.get(token.user_id)
        if user is None:
            raise UnauthorizedError

        revoke(token, now)
        await self._token_repo.save(token)
        tokens = await self._issue_tokens(user)
        await self._session.commit()
        return tokens

    async def logout(self, refresh_token: str | None, access_token: str | None) -> None:
        """Отзывает refresh-токен и добавляет access-токен в чёрный список."""
        now = datetime.now(UTC)
        if refresh_token:
            token = await self._token_repo.get_by_hash(hash_refresh_token(refresh_token))
            if token is not None:
                revoke(token, now)
                await self._token_repo.save(token)
                await self._session.commit()
        if access_token:
            try:
                payload = decode_access_token(access_token)
            except UnauthorizedError:
                return
            expires_at = datetime.fromtimestamp(payload["exp"], UTC)
            await blacklist.revoke_token(self._redis, payload["jti"], expires_at)

    async def get_user(self, user_id: str) -> User:
        """Возвращает пользователя по id из токена, который уже проверил gateway."""
        user = await self._user_repo.get(_parse_user_id(user_id))
        if user is None:
            raise UnauthorizedError
        return user

    async def _issue_tokens(self, user: User) -> Tokens:
        """Создаёт новую пару токенов и сохраняет refresh-токен в базе."""
        raw, token_hash = new_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
        await self._token_repo.add(
            RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
        )
        return Tokens(
            user=user,
            access=create_access_token(user.id),
            refresh_token=raw,
            refresh_expires_at=expires_at,
        )


def _parse_user_id(sub: str) -> uuid.UUID:
    """Превращает строку из токена в UUID пользователя."""
    try:
        return uuid.UUID(sub)
    except ValueError:
        raise UnauthorizedError from None
