"""Демо-магазин: полигон для AI-тестировщика.

Обычный маленький интернет-магазин на FastAPI и Jinja. Позже в него будут
заложены баги, которые агент должен найти.
"""

from __future__ import annotations

import math
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from demo_shop.store import Store, seed_store

PER_PAGE = 6

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def create_app() -> FastAPI:
    store: Store = seed_store()
    app = FastAPI(title="Demo Shop", docs_url=None, redoc_url=None)
    app.state.store = store

    def render(request: Request, name: str, status_code: int = 200, **ctx) -> HTMLResponse:
        return templates.TemplateResponse(request, name, ctx, status_code=status_code)

    @app.get("/")
    def index() -> RedirectResponse:
        return RedirectResponse("/products", status_code=303)

    @app.get("/products", response_class=HTMLResponse)
    def products(request: Request, page: int = 1) -> HTMLResponse:
        total_pages = max(1, math.ceil(len(store.products) / PER_PAGE))
        page = min(max(page, 1), total_pages)
        start = (page - 1) * PER_PAGE
        items = store.products[start : start + PER_PAGE]
        return render(request, "products.html", products=items, page=page, total_pages=total_pages)

    @app.get("/products/{product_id}", response_class=HTMLResponse)
    def product(request: Request, product_id: int) -> HTMLResponse:
        item = store.product(product_id)
        if item is None:
            raise HTTPException(404, "Товар не найден")
        return render(request, "product.html", product=item)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
