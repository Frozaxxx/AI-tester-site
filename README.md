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

cd services/runs
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
Локальные и внутренние адреса (localhost, 10.x, 192.168.x, 169.254.x и т.п.) запрещены,
чтобы агента нельзя было натравить на нашу сеть. Для демо-магазина на localhost
в своём `.env` поставь `PROJECTS_ALLOW_INTERNAL_URLS=true`.

| Ручка gateway | Что делает |
|---|---|
| `POST /api/v1/projects` | создать проект |
| `GET /api/v1/projects` | мои проекты |
| `GET /api/v1/projects/{id}` | один проект |
| `DELETE /api/v1/projects/{id}` | удалить проект вместе со сценариями |
| `POST /api/v1/projects/{id}/scenarios` | добавить сценарий |
| `GET /api/v1/projects/{id}/scenarios` | сценарии проекта |
| `DELETE /api/v1/scenarios/{id}` | удалить сценарий |

## Прогоны: gateway + runs

Прогон — один запуск агента по проекту, целиком или по одному сценарию. Runs слушает gRPC
на `:50053`. Перед запуском gateway через projects проверяет, что проект и сценарий
принадлежат пользователю. Методы раннера (шаги, баги, завершение) наружу не открыты.

| Ручка gateway | Что делает |
|---|---|
| `POST /api/v1/projects/{id}/runs` | запустить прогон, тело `{"scenario_id": ...}` необязательно |
| `GET /api/v1/projects/{id}/runs` | прогоны проекта |
| `GET /api/v1/runs/{id}` | прогон с шагами, багами и сгенерированным тестом |
| `POST /api/v1/runs/{id}/cancel` | отменить прогон |

## Раннер

Воркер, который берёт прогоны из очереди runs (самый старый, `SKIP LOCKED`, поэтому раннеров
можно запускать несколько), открывает сайт проекта в Playwright, выполняет шаги и записывает
их и найденные ошибки в runs. Пока план без LLM: открыть главную страницу и собрать ошибки
JavaScript, консоли и ответы 4xx/5xx. Внутренние адреса браузер блокирует; для демо-магазина
на localhost в своём `.env` поставь `RUNNER_ALLOW_INTERNAL_URLS=true` и
`PROJECTS_ALLOW_INTERNAL_URLS=true`.

```
cd services/runner
playwright install chromium
python -m app.main
```

После прогона раннер собирает из его шагов Playwright-тест: он повторяет шаги и падает,
если на страницах есть ошибки JavaScript, консоли или ответы 4xx/5xx. Код теста лежит в
`GET /api/v1/runs/{id}` в поле `test.code`. Запуск у себя:

```
pip install pytest-playwright
pytest test_generated.py
```

Прогон, который идёт дольше 15 минут (например, раннер упал), сервис runs сам переводит
в ошибку раз в минуту.

## Агент (LangGraph + LLM)

Раннер ведёт LLM по сайту в цикле: снимок страницы (текст и пронумерованные элементы) →
модель выбирает инструмент `act` / `report_bug` / `finish` → действие в браузере → снова снимок.
Не больше 25 шагов. Модель указывает элемент номером, а локатор строит сам раннер, поэтому
выдуманных селекторов нет. Без LLM (`RUNNER_LLM_PROVIDER=none`) раннер просто открывает
главную страницу.

GigaChat (бесплатный Freemium для физлиц):

```
RUNNER_LLM_PROVIDER=gigachat
RUNNER_GIGACHAT_CREDENTIALS=<ключ авторизации>
RUNNER_GIGACHAT_SCOPE=GIGACHAT_API_PERS
RUNNER_GIGACHAT_CA_BUNDLE_FILE=<путь к сертификату НУЦ Минцифры>
```

Сертификат «Russian Trusted Root CA» скачивается с gosuslugi.ru/crt. Его кладут вне проекта.
Есть запасной провайдер `openrouter` с бесплатными моделями (`RUNNER_OPENROUTER_API_KEY`).

Контракты между сервисами лежат в `proto/`. После их изменения перегенерируй код:

```
python proto/generate.py
```

## Оценка агента на демо-магазине

В демо-магазине (каталог, поиск, корзина, оформление заказа) специально оставлены 6 багов,
они помечены в коде комментариями `BUG`: неверная сумма корзины, повтор товара между
страницами каталога, заказ с пустыми полями, 500 на пустом поиске, ошибка JavaScript на
кнопке «В избранное», битая ссылка «Доставка и оплата».

Скрипт прогоняет агента по шести сценариям и считает, сколько известных багов он нашёл и
сколько выдал ложных срабатываний:

```
python -m demo_shop --port 8001
cd services/runner
python -m app.benchmark --site http://127.0.0.1:8001
```
