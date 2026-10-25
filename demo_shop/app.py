from __future__ import annotations

import math
import secrets
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from demo_shop.store import Store, seed_store

PER_PAGE = 6
CART_COOKIE = "cart_id"

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def create_app() -> FastAPI:
    """Создаёт приложение демо-магазина с каталогом в памяти и специально оставленными багами."""
    store: Store = seed_store()
    app = FastAPI(title="Demo Shop", docs_url=None, redoc_url=None)
    app.state.store = store

    def cart_id(request: Request) -> str:
        """Возвращает id корзины из куки или новый, если куки ещё нет."""
        return request.cookies.get(CART_COOKIE) or secrets.token_urlsafe(16)

    def render(request: Request, name: str, status_code: int = 200, **ctx) -> HTMLResponse:
        """Отрисовывает HTML-шаблон и сохраняет id корзины в куке."""
        current = cart_id(request)
        ctx["cart_count"] = sum(store.cart(current).values())
        response = templates.TemplateResponse(request, name, ctx, status_code=status_code)
        response.set_cookie(CART_COOKIE, current, httponly=True, samesite="lax")
        return response

    @app.get("/")
    def index() -> RedirectResponse:
        """Перенаправляет с главной страницы в каталог."""
        return RedirectResponse("/products", status_code=303)

    @app.get("/products", response_class=HTMLResponse)
    def products(request: Request, page: int = 1) -> HTMLResponse:
        """Показывает страницу каталога."""
        total_pages = max(1, math.ceil(len(store.products) / PER_PAGE))
        page = min(max(page, 1), total_pages)
        start = (page - 1) * PER_PAGE
        # BUG pagination: со второй страницы сдвиг на один, последний товар прошлой страницы
        # повторяется первым на следующей.
        if page > 1:
            start -= 1
        items = store.products[start : start + PER_PAGE]
        return render(request, "products.html", products=items, page=page, total_pages=total_pages)

    @app.get("/products/{product_id}", response_class=HTMLResponse)
    def product(request: Request, product_id: int) -> HTMLResponse:
        """Показывает карточку товара."""
        item = store.product(product_id)
        if item is None:
            raise HTTPException(404, "Товар не найден")
        return render(request, "product.html", product=item)

    @app.get("/search", response_class=HTMLResponse)
    def search(request: Request, q: str = "") -> HTMLResponse:
        """Показывает результаты поиска по названию."""
        return render(request, "search.html", query=q, products=store.search(q.strip()))

    @app.post("/cart/add")
    def add_to_cart(
        request: Request, product_id: int = Form(), quantity: int = Form(1)
    ) -> RedirectResponse:
        """Добавляет товар в корзину и переводит в неё."""
        if store.product(product_id) is None or not 1 <= quantity <= 99:
            raise HTTPException(400, "Некорректный товар или количество")
        current = cart_id(request)
        cart = store.cart(current)
        cart[product_id] = cart.get(product_id, 0) + quantity
        response = RedirectResponse("/cart", status_code=303)
        response.set_cookie(CART_COOKIE, current, httponly=True, samesite="lax")
        return response

    @app.get("/cart", response_class=HTMLResponse)
    def cart(request: Request) -> HTMLResponse:
        """Показывает корзину с количеством, суммами по строкам и итогом."""
        current = cart_id(request)
        return render(
            request, "cart.html", lines=store.cart_lines(current), total=store.cart_total(current)
        )

    @app.post("/cart/clear")
    def clear_cart(request: Request) -> RedirectResponse:
        """Очищает корзину."""
        store.carts.pop(cart_id(request), None)
        return RedirectResponse("/cart", status_code=303)

    @app.get("/checkout", response_class=HTMLResponse, response_model=None)
    def checkout_form(request: Request) -> HTMLResponse | RedirectResponse:
        """Показывает форму оформления заказа, если корзина не пуста."""
        current = cart_id(request)
        if not store.cart(current):
            return RedirectResponse("/cart", status_code=303)
        return render(request, "checkout.html", total=store.cart_total(current))

    @app.post("/checkout")
    def checkout(
        request: Request,
        name: str = Form(""),
        email: str = Form(""),
        address: str = Form(""),
    ) -> RedirectResponse:
        """Оформляет заказ и переводит на страницу подтверждения."""
        current = cart_id(request)
        if not store.cart(current):
            return RedirectResponse("/cart", status_code=303)
        order = store.place_order(current, name, email, address)
        return RedirectResponse(f"/orders/{order.id}", status_code=303)

    @app.get("/orders/{order_id}", response_class=HTMLResponse)
    def order(request: Request, order_id: int) -> HTMLResponse:
        """Показывает подтверждение заказа."""
        if not 1 <= order_id <= len(store.orders):
            raise HTTPException(404, "Заказ не найден")
        return render(request, "order.html", order=store.orders[order_id - 1])

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """Сообщает, что магазин работает."""
        return {"status": "ok"}

    return app


app = create_app()
