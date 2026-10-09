"""Настройки сервиса из переменных окружения."""

import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/auth"
)
