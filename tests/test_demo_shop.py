"""Тесты демо-магазина."""

from __future__ import annotations

from fastapi.testclient import TestClient

from demo_shop.app import PER_PAGE, create_app


def client() -> TestClient:
    return TestClient(create_app())


def test_index_redirects_to_catalog() -> None:
    r = client().get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/products"


def test_catalog_pages_cover_all_products() -> None:
    c = client()
    products = c.app.state.store.products
    pages = -(-len(products) // PER_PAGE)
    html = "".join(c.get(f"/products?page={n}").text for n in range(1, pages + 1))
    assert all(f'href="/products/{p.id}"' in html for p in products)


def test_product_page() -> None:
    r = client().get("/products/16")
    assert r.status_code == 200
    assert "Флешка 128 ГБ" in r.text


def test_unknown_product_is_404() -> None:
    assert client().get("/products/999").status_code == 404
