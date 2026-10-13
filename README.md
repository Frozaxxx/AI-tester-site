# AI-tester-site

AI-агент, который тестирует сайты в браузере. Он проходит пользовательские сценарии, сам исследует сайт, находит баги и сохраняет каждый найденный баг как воспроизводимый Playwright-тест, который потом гоняется без LLM.

## Статус

Проект в разработке.

## Структура

```
demo_shop/          демо-магазин с заложенными багами, полигон для агента
proto/              gRPC-контракты между сервисами
services/
  gateway/          единственная точка входа: REST, куки, проверка JWT
  auth/             пользователи и токены
  projects/         сайты, сценарии, тестовые аккаунты
  runs/             прогоны, шаги, найденные баги, сгенерированные тесты
  runner/           браузер и LLM-агент
```

Внутри сервиса слои DDD (на примере auth):

```
app/
  domain/
    entities.py       сущности (dataclass)
    services.py       бизнес-правила
    exceptions.py     ошибки со статусом ответа
  application/
    repos.py          интерфейсы репозиториев
    dtos.py           схемы запросов и ответов
    services/         сценарии: регистрация, вход, обновление токенов, выход
  infra/
    database/         models.py, mappers.py, repos/
    redis.py
  api/servicer.py     gRPC-обработчики
  grpc_gen/           код из proto (генерируется)
  security.py         пароли и токены
  main.py
tests/
```

## Стек

Python, Playwright, FastAPI, LangGraph, PostgreSQL, RabbitMQ, Redis, MinIO, Docker.

## Секреты

Все секреты лежат в `.env`, он в git не попадает. Образец — `.env.example`.
RSA-ключ для подписи JWT: выполни `openssl genrsa 2048` и вставь вывод целиком
в `AUTH_JWT_PRIVATE_KEY` в кавычках.

## Запуск базы и миграций

```
cp .env.example .env
docker compose up -d
pip install "sqlalchemy[asyncio]" asyncpg alembic pydantic-settings argon2-cffi "pyjwt[crypto]" redis fastapi "uvicorn[standard]" grpcio grpcio-tools
cd services/runs
alembic upgrade head
```

То же для `services/auth` и `services/projects`. Базы: auth на порту 5432, projects на 5433, runs на 5434. Новая миграция после изменения моделей:

```
alembic revision --autogenerate -m "что изменилось"
```

## Авторизация: gateway + auth

```
браузер --HTTP + куки--> gateway (:8000) --gRPC--> auth (:50051) --> Postgres, Redis
```

Gateway — единственная точка входа: ставит куки и проверяет JWT публичным ключом,
не обращаясь к auth. Auth наружу не открыт и слушает только gRPC.

Запуск (каждый сервис в своём терминале):

```
cd services/auth
alembic upgrade head
python -m app.main

cd services/projects
alembic upgrade head
python -m app.main

cd services/gateway
uvicorn app.main:app --port 8000
```

Документация ручек: http://localhost:8000/docs

| Ручка gateway | Что делает |
|---|---|
| `POST /api/v1/auth/register` | регистрация |
| `POST /api/v1/auth/login` | вход, ставит куки `access_token` и `refresh_token` |
| `POST /api/v1/auth/refresh` | новая пара токенов по refresh-куке |
| `POST /api/v1/auth/logout` | выход: refresh отзывается в базе, access попадает в чёрный список Redis |
| `GET /api/v1/auth/me` | текущий пользователь |

## Проекты: gateway + projects

Проект — сайт, который тестирует агент (название и адрес). Сценарий — задание агенту
обычным текстом. Projects слушает gRPC на `:50052`, gateway передаёт ему id пользователя из токена.
Чужие проекты и сценарии отдаются как 404.

| Ручка gateway | Что делает |
|---|---|
| `POST /api/v1/projects` | создать проект |
| `GET /api/v1/projects` | мои проекты |
| `GET /api/v1/projects/{id}` | один проект |
| `DELETE /api/v1/projects/{id}` | удалить проект вместе со сценариями |
| `POST /api/v1/projects/{id}/scenarios` | добавить сценарий |
| `GET /api/v1/projects/{id}/scenarios` | сценарии проекта |
| `DELETE /api/v1/scenarios/{id}` | удалить сценарий |

Контракты между сервисами лежат в `proto/`. После их изменения перегенерируй код:

```
python proto/generate.py
```
