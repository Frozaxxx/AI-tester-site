# AI-tester-site

AI-агент, который тестирует сайты в браузере. Он проходит пользовательские сценарии, сам исследует сайт, находит баги и сохраняет каждый найденный баг как воспроизводимый Playwright-тест, который потом гоняется без LLM.

## Статус

Проект в разработке.

## Структура

```
demo_shop/          демо-магазин с заложенными багами, полигон для агента
proto/              gRPC-контракты между сервисами
services/
  gateway/          REST для фронтенда, проверка JWT
  auth/             пользователи и токены
  projects/         сайты, сценарии, тестовые аккаунты
  runs/             прогоны, шаги, найденные баги, сгенерированные тесты
  runner/           браузер и LLM-агент
```

Внутри сервиса слои DDD:

```
app/
  domain/           сущности и бизнес-правила, без SQLAlchemy и gRPC
  application/      сценарии использования
  infrastructure/   база данных, очереди, внешние клиенты
  api/              gRPC-обработчики
tests/
```

## Стек

Python, Playwright, FastAPI, LangGraph, PostgreSQL, RabbitMQ, Redis, MinIO, Docker.

## Ключ для JWT

Сервис auth подписывает токены RSA-ключом. Ключ в git не хранится, создай его один раз:

```
openssl genrsa -out services/auth/keys/jwt_private.pem 2048
```

## Запуск базы и миграций

```
cp .env.example .env
docker compose up -d
pip install "sqlalchemy[asyncio]" asyncpg alembic pydantic-settings
cd services/runs
alembic upgrade head
```

То же для `services/auth` и `services/projects`. Базы: auth на порту 5432, projects на 5433, runs на 5434. Новая миграция после изменения моделей:

```
alembic revision --autogenerate -m "что изменилось"
```
