import pytest

from app.domain.entities import Action
from app.domain.exceptions import ActionError
from app.domain.services import is_internal_ip, is_same_site, same_site_url, validate_action


@pytest.mark.parametrize(
    "action",
    [
        Action(name="rm"),
        Action(name="click"),
        Action(name="fill", locator="input"),
        Action(name="goto"),
        Action(name="wait", value="abc"),
        Action(name="wait", value="60000"),
    ],
)
def test_invalid_actions(action: Action) -> None:
    """Неизвестное действие или действие без нужных данных не выполняется."""
    with pytest.raises(ActionError):
        validate_action(action)


def test_valid_actions() -> None:
    """Корректные действия проходят проверку."""
    for action in (
        Action(name="goto", value="/"),
        Action(name="click", locator="text=Купить"),
        Action(name="press", value="Enter"),
        Action(name="wait", value="500"),
    ):
        validate_action(action)


def test_same_site_url() -> None:
    """Относительные адреса достраиваются, а уход на чужой сайт запрещён."""
    base = "https://shop.example.com"
    assert same_site_url(base, "/cart") == "https://shop.example.com/cart"
    assert same_site_url(base, "https://shop.example.com/a") == "https://shop.example.com/a"
    for target in ("https://evil.example.com", "//evil.example.com/x", "javascript:alert(1)"):
        with pytest.raises(ActionError):
            same_site_url(base, target)


@pytest.mark.parametrize(
    ("ip", "internal"),
    [
        ("127.0.0.1", True),
        ("10.1.2.3", True),
        ("169.254.169.254", True),
        ("::1", True),
        ("8.8.8.8", False),
        ("garbage", True),
    ],
)
def test_internal_ips(ip: str, internal: bool) -> None:
    """Локальные и служебные адреса считаются внутренними."""
    assert is_internal_ip(ip) is internal


@pytest.mark.parametrize(
    ("url", "same"),
    [
        ("https://shop.example.com/cart", True),
        ("https://www.shop.example.com/", True),
        ("https://api.shop.example.com/", True),
        ("https://example.com/", False),
        ("https://evilshop.example.com/", False),
        ("https://shop.example.com.evil.com/", False),
    ],
)
def test_same_site(url: str, same: bool) -> None:
    """Свой сайт, его www и поддомены считаются одним сайтом, а похожие чужие нет."""
    assert is_same_site("https://shop.example.com", url) is same
