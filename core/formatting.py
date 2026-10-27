"""Small display helpers shared by controllers and screens."""
import csv
from decimal import Decimal

from config import CURRENCY


def money(value) -> str:
    return f"{CURRENCY}{Decimal(str(value or 0)):,.2f}"


def stock_status(stock: int, threshold: int, active: bool = True) -> str:
    if not active:
        return "Inactive"
    if stock <= 0:
        return "Out of stock"
    if stock <= threshold:
        return "Low"
    return "OK"


def product_label(name: str, specification: str | None) -> str:
    detail = (specification or "").strip() or "Specification not entered"
    return f"{name} — {detail}"


def short_dt(value) -> str:
    return str(value)[:16] if value else "-"


def write_csv(path: str, headers: list, rows: list) -> None:
    """UTF-8 with BOM so Excel shows the peso sign correctly."""
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
