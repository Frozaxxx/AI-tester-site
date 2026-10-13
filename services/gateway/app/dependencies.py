from typing import Annotated

from fastapi import Cookie, Depends, Request
from redis.asyncio import Redis

from app.clients.auth import AuthClient
from app.clients.projects import ProjectsClient
from app.security import verify_access_token

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def get_auth_client(request: Request) -> AuthClient:
    """Возвращает клиент сервиса auth."""
    return request.app.state.auth_client


def get_projects_client(request: Request) -> ProjectsClient:
    """Возвращает клиент сервиса projects."""
    return request.app.state.projects_client


def get_redis(request: Request) -> Redis:
    """Возвращает клиент Redis."""
    return request.app.state.redis


AuthClientDep = Annotated[AuthClient, Depends(get_auth_client)]
ProjectsClientDep = Annotated[ProjectsClient, Depends(get_projects_client)]
RedisDep = Annotated[Redis, Depends(get_redis)]
AccessCookie = Annotated[str | None, Cookie(alias=ACCESS_COOKIE)]
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


async def get_current_user_id(
    request: Request, redis: RedisDep, access_token: AccessCookie = None
) -> str:
    """Проверяет access-куку и возвращает id пользователя."""
    return await verify_access_token(access_token, request.app.state.public_key, redis)


CurrentUserId = Annotated[str, Depends(get_current_user_id)]
