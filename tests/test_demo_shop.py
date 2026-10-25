"""Тесты демо-магазина: обычные сценарии работают, а специально оставленные баги на месте."""

from __future__ import annotations

from fastapi.testclient import TestClient

from demo_shop.app import PER_PAGE, create_app


def client() -> TestClient:
    """Создаёт клиент к свежему магазину; 500 возвращается ответом, а не исключением."""
    return TestClient(create_app(), raise_server_exceptions=False)


def add(c: TestClient, product_id: int, quantity: int = 1) -> None:
    """Добавляет товар в корзину."""
    c.post("/cart/add", data={"product_id": product_id, "quantity": quantity})


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
    assert "Флешка 128 ГБ" in r.text and "В корзину" in r.text


def test_unknown_product_is_404() -> None:
    assert client().get("/products/999").status_code == 404


def test_search_finds_products() -> None:
    r = client().get("/search", params={"q": "ноутбук"})
    assert r.status_code == 200 and "Ноутбук Pro 14" in r.text and "Мышь" not in r.text


def test_cart_and_checkout_flow() -> None:
    c = client()
    add(c, 16)
    cart = c.get("/cart").text
    assert "Флешка 128 ГБ" in cart and "Итого: 990 ₽" in cart and "Корзина (1)" in cart
    r = c.post(
        "/checkout",
        data={"name": "Иван", "email": "ivan@example.com", "address": "Тюмень"},
        follow_redirects=False,
    )
    assert r.headers["location"] == "/orders/1"
    assert "Заказ №1 оформлен" in c.get("/orders/1").text
    assert "Корзина пуста" in c.get("/cart").text


def test_checkout_with_empty_cart_redirects() -> None:
    assert client().get("/checkout", follow_redirects=False).status_code == 303


def test_bug_cart_total_ignores_quantity() -> None:
    c = client()
    add(c, 16, quantity=3)
    cart = c.get("/cart").text
    assert "2 970 ₽" in cart and "Итого: 990 ₽" in cart


def test_bug_empty_search_is_500() -> None:
    assert client().get("/search", params={"q": ""}).status_code == 500


def test_bug_checkout_accepts_empty_form() -> None:
    c = client()
    add(c, 16)
    r = c.post("/checkout", data={"name": "", "email": "", "address": ""}, follow_redirects=False)
    assert r.headers["location"] == "/orders/1"


def test_bug_pagination_repeats_product() -> None:
    c = client()
    last_on_first = c.app.state.store.products[PER_PAGE - 1]
    assert f'href="/products/{last_on_first.id}"' in c.get("/products?page=2").text


def test_bug_broken_delivery_link() -> None:
    c = client()
    assert 'href="/delivery"' in c.get("/products").text
    assert c.get("/delivery").status_code == 404


def test_bug_favorites_button_calls_missing_function() -> None:
    assert 'onclick="addToFavorites(' in client().get("/products/1").text
