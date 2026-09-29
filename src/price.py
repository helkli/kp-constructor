"""Прайс услуг. ЕДИНСТВЕННЫЙ источник формирования цен в коде.

Правило AGENTS.md: любая генерация цен — только из прайса через этот модуль,
модель не имеет права придумывать суммы.
"""
from __future__ import annotations


def format_price(price) -> str:
    """Форматирует число с разделением разрядов пробелами: 12000 -> '12 000'."""
    if price is None:
        return "цена уточняется"
    price = float(price)
    if price == int(price):
        return f"{int(price):,}".replace(",", " ")
    return f"{price:,.2f}".replace(",", " ")


def price_number_label(price, unit: str = "") -> str:
    """Готовая строка цены: '12 000 ₽/мес' или 'цена уточняется'."""
    if price is None:
        return "цена уточняется"
    label = f"{format_price(price)} ₽"
    if unit:
        label += f" / {unit}"
    return label


def pricing_rows(services) -> list[dict]:
    """Список строк для таблицы «Состав работ и стоимость» (для КП, предпросмотра и PDF)."""
    rows = []
    for s in services:
        rows.append(
            {
                "name": s["name"],
                "unit": s.get("unit") or "",
                "price": s.get("price"),
                "price_text": price_number_label(s.get("price"), s.get("unit") or ""),
            }
        )
    return rows


def pricing_block(rows: list[dict], budget: str = "") -> str:
    """Текстовый блок цен, который код добавляет в раздел «Предлагаемые услуги»."""
    lines = ["СОСТАВ РАБОТ И СТОИМОСТЬ:"]
    for row in rows:
        lines.append(f"\u2022 {row['name']} — {row['price_text']}")
    if budget and budget.strip():
        lines.append(f"\u2022 Ориентировочный бюджет клиента: {budget.strip()}")
    return "\n".join(lines)