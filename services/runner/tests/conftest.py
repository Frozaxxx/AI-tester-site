import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

PAGES = {
    "/": """<!doctype html><meta charset="utf-8"><title>Магазин</title>
<h1>Каталог</h1>
<input name="q" placeholder="Поиск">
<select name="sort">
  <option value="cheap">Дешевле</option><option value="new">Новинки</option>
</select>
<label><input type="checkbox" name="stock"> В наличии</label>
<button onclick="document.getElementById('cart').textContent='Добавлено'">В корзину</button>
<p id="cart"></p>
<a href="/missing">Сломанная ссылка</a>""",
    "/js-error": """<!doctype html><meta charset="utf-8"><h1>JS</h1>
<script>undefinedFunction()</script>""",
    "/page/?path=/": """<!doctype html><meta charset="utf-8"><title>Проверка URL</title>
<script>throw new Error("Smoke page loaded")</script>""",
    "/walk/?path=/": """<!doctype html><script>console.error('Ошибка на старте')</script>
<a href="/walk-next#top">Дальше</a><a href="/walk-next#footer">Тот же адрес</a>
<a href="/missing">Сломанная ссылка</a><a href="/secret" download>Загрузить</a>
<a href="https://example.com/">Другой сайт</a>""",
    "/walk-next": """<!doctype html><script>throw new Error('Ошибка на второй странице')</script>
<a href="/walk/?path=/">На старт</a><a href="/walk-last">Детали</a>""",
    "/walk-last": "<!doctype html><h1>Детали</h1>",
    "/walk-last?from=news": "<!doctype html><h1>Детали</h1>",
    "/long-link": """<!doctype html><meta charset="utf-8">
<a href="/walk-last?from=news">Пресс-релиз для обучающихся и родителей о мероприятиях,
изменениях в расписании и дополнительной информации на следующую неделю</a>""",
    "/school-check": """<!doctype html><meta charset="utf-8"><h1>Школа</h1>
<a href="/school-check">Главная</a><a href="https://example.com/maps">Внешняя карта</a>
<button id="headSearchCollapseOpen" onclick="this.textContent='Поиск открыт'">Поиск</button>
<button id="blocked" style="pointer-events:none">Недоступная кнопка</button>""",
    "/console-error": """<!doctype html><meta charset="utf-8"><h1>Консоль</h1>
<script>console.error("Не удалось загрузить корзину")</script>""",
    "/unload-policy": """<!doctype html><meta charset="utf-8"><h1>Политика unload</h1>
<script>window.addEventListener("unload", () => {});</script>""",
    "/api-error": """<!doctype html><meta charset="utf-8"><h1>API</h1>
<script>fetch("/api/cart")</script>""",
    "/external-link": """<!doctype html><meta charset="utf-8">
<a href="https://example.com/">Партнёры</a>""",
    "/spam": """<!doctype html><meta charset="utf-8"><h1>Спам</h1>
<script>for (let i = 0; i < 200; i++) console.error("ошибка " + i)</script>""",
    "/secret": "SECRET",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        """Отдаёт тестовые страницы, ошибку API, редирект во внутреннюю сеть и 404."""
        if self.path == "/third-party-image":
            self._send(
                200, f'<img src="http://localhost:{self.server.server_address[1]}/denied.png">'
            )
        elif self.path == "/own-image":
            self._send(200, '<img src="/denied.png">')
        elif self.path == "/denied.png":
            self._send(403, "Forbidden")
        elif self.path == "/api/cart":
            self._send(500, "Internal Server Error")
        elif self.path == "/redirect-internal":
            self.send_response(302)
            self.send_header("Location", f"http://localhost:{self.server.server_address[1]}/secret")
            self.end_headers()
        elif self.path in PAGES:
            self._send(200, PAGES[self.path])
        else:
            self._send(404, "Not Found")

    def _send(self, status: int, body: str) -> None:
        """Отправляет ответ с HTML."""
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if self.path == "/unload-policy":
            self.send_header("Permissions-Policy", "unload=()")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args) -> None:
        """Не засоряет вывод тестов логами запросов."""


@pytest.fixture(scope="session")
def site_url() -> Iterator[str]:
    """Поднимает локальный тестовый сайт на свободном порту."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
