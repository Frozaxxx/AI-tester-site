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
    "/console-error": """<!doctype html><meta charset="utf-8"><h1>Консоль</h1>
<script>console.error("Не удалось загрузить корзину")</script>""",
    "/api-error": """<!doctype html><meta charset="utf-8"><h1>API</h1>
<script>fetch("/api/cart")</script>""",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        """Отдаёт тестовую страницу, 500 для сломанного API и 404 для остального."""
        if self.path == "/api/cart":
            self._send(500, "Internal Server Error")
        elif self.path in PAGES:
            self._send(200, PAGES[self.path])
        else:
            self._send(404, "Not Found")

    def _send(self, status: int, body: str) -> None:
        """Отправляет ответ с HTML."""
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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
