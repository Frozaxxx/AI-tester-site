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

## Запуск базы и миграций

```
docker compose up -d postgres
pip install "sqlalchemy[asyncio]" asyncpg alembic
cd services/runs
alembic upgrade head
```

То же для `services/auth` и `services/projects`. Новая миграция после изменения моделей:

```
alembic revision --autogenerate -m "что изменилось"
```
