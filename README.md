# AI Tester

Scout запускает браузерные проверки сайтов. Раннер открывает страницу в Chromium, сохраняет ошибки и шаги, затем собирает из них Playwright-тест.

## Запуск

Скопируйте `.env.example` в `.env`. Задайте пароли PostgreSQL, Redis и RabbitMQ и вставьте RSA-ключ в `AUTH_JWT_PRIVATE_KEY` целиком, в кавычках.

```sh
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048
docker compose up -d --build
```

Откройте **http://localhost:8000**, создайте аккаунт и вставьте URL в поле «Ссылка на страницу». Можно указать конкретный путь и параметры запроса. Используйте сайт, на котором у вас есть разрешение на автоматические проверки.

По умолчанию раннер открывает указанную страницу и записывает ошибки загрузки, JavaScript и консоли. Для сценариев с LLM можно настроить GigaChat или OpenRouter через `.env.example`. При использовании сертификата GigaChat укажите папку в `GIGACHAT_CA_DIR`.

## Как устроено

Scout написан на React и TypeScript. FastAPI gateway раздаёт интерфейс и передаёт запросы сервисам auth, projects и runs по gRPC.

RabbitMQ будит раннер. Он забирает прогон из PostgreSQL через `ClaimRun` и продлевает аренду в Redis. Если раннер пропадает, runs обычно освобождает слот в течение 35 секунд после последнего heartbeat. Отчёт и промежуточные шаги остаются доступны.

[Схема и детали восстановления](docs/architecture.md) · [Результаты проверок](docs/validation.md)

## Разработка

Docker сам собирает интерфейс. При запуске gateway из исходников соберите интерфейс заранее.

```sh
npm --prefix frontend ci
npm --prefix frontend run build
```

Тесты каждого сервиса запускаются командой `uv run --locked pytest -q` из его каталога. REST API описан на **http://localhost:8000/docs**.
