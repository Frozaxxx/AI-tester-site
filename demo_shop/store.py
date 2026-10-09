"""Хранилище демо-магазина в памяти. Для полигона база не нужна."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: int  # в рублях
    description: str


@dataclass
class Store:
    products: list[Product] = field(default_factory=list)

    def product(self, product_id: int) -> Product | None:
        return next((p for p in self.products if p.id == product_id), None)


_CATALOG = [
    ("Ноутбук Pro 14", 89990, "Лёгкий ноутбук для работы и учёбы."),
    ("Ноутбук Air 13", 64990, "Тонкий и тихий, 18 часов автономности."),
    ('Монитор 27" 4K', 32990, "IPS-матрица, USB-C с зарядкой."),
    ('Монитор 24" FHD', 12990, "Для офиса и дома."),
    ("Клавиатура механическая", 7490, "Тактильные переключатели, подсветка."),
    ("Клавиатура беспроводная", 3990, "Тихие клавиши, Bluetooth."),
    ("Мышь игровая", 4590, "Сенсор 26000 DPI."),
    ("Мышь офисная", 1290, "Бесшумные клики."),
    ("Наушники с шумоподавлением", 19990, "До 30 часов работы."),
    ("Наушники-вкладыши", 6990, "Влагозащита IPX4."),
    ("Веб-камера 1080p", 3490, "Автофокус и два микрофона."),
    ("Микрофон USB", 8990, "Кардиоидная направленность."),
    ("SSD 1 ТБ", 7990, "NVMe, до 7000 МБ/с."),
    ("SSD 2 ТБ", 13990, "NVMe, до 7000 МБ/с."),
    ("Внешний диск 4 ТБ", 9990, "USB 3.2."),
    ("Флешка 128 ГБ", 990, "USB-C и USB-A."),
    ("Роутер Wi-Fi 6", 6490, "Mesh, до 3 Гбит/с."),
    ("Док-станция USB-C", 11990, "Два монитора, Ethernet, зарядка."),
    ("Подставка для ноутбука", 2490, "Алюминий, регулируемый наклон."),
    ("Коврик для мыши XL", 1490, "900×400 мм."),
    ("Кабель USB-C 2 м", 790, "100 Вт, 10 Гбит/с."),
    ("Зарядка 65 Вт", 2990, "GaN, три порта."),
    ("Колонка портативная", 5490, "Стерео, 12 часов."),
]


def seed_store() -> Store:
    products = [
        Product(id=i, name=name, price=price, description=desc)
        for i, (name, price, desc) in enumerate(_CATALOG, start=1)
    ]
    return Store(products=products)
