from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus

import grpc
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as projects_router
from app.api.v1.runs import router as runs_router
from app.clients.auth import AuthClient
from app.clients.projects import ProjectsClient
from app.clients.runs import RunsClient
from app.config import settings
from app.exceptions import GatewayError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Подключается к сервисам и Redis при старте и закрывает соединения при остановке."""
    auth_channel = grpc.aio.insecure_channel(settings.auth_grpc_address)
    projects_channel = grpc.aio.insecure_channel(settings.projects_grpc_address)
    runs_channel = grpc.aio.insecure_channel(settings.runs_grpc_address)
    app.state.auth_client = AuthClient(auth_channel)
    app.state.projects_client = ProjectsClient(projects_channel)
    app.state.runs_client = RunsClient(runs_channel)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.public_key = await app.state.auth_client.get_public_key()
    yield
    await auth_channel.close()
    await projects_channel.close()
    await runs_channel.close()
    await app.state.redis.aclose()


app = FastAPI(title="AI-tester gateway", lifespan=lifespan)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(runs_router, prefix="/api/v1")


@app.exception_handler(GatewayError)
async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
    """Отдаёт ошибку клиенту в виде JSON с нужным статусом."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Отдаёт ошибку валидации в общем формате и не возвращает клиенту присланные данные."""
    fields = sorted({str(error["loc"][-1]) for error in exc.errors()})
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": f"Некорректные данные: {', '.join(fields)}",
        },
    )


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    """Сообщает, что gateway работает."""
    return {"status": "ok"}
