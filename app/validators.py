"""Input parsing/validation helpers shared by the services."""
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .errors import ValidationError

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,30}$")
MAX_PRICE = Decimal("9999999.99")


def parse_int(value, label: str, minimum: int = 1, maximum: int = 1_000_000) -> int:
    text = str(value if value is not None else "").strip()
    if not text:
        raise ValidationError(f"{label} is required.")
    if not re.fullmatch(r"\d+", text):
        raise ValidationError(f"{label} must be a whole number (no letters or decimals).")
    number = int(text)
    if number < minimum:
        raise ValidationError(f"{label} must be at least {minimum}.")
    if number > maximum:
        raise ValidationError(f"{label} must not be more than {maximum:,}.")
    return number


def parse_price(value, label: str = "Price") -> Decimal:
    text = str(value if value is not None else "").strip().replace(",", "").lstrip("\u20b1").strip()
    if not text:
        raise ValidationError(f"{label} is required.")
    try:
        price = Decimal(text)
    except InvalidOperation:
        raise ValidationError(f"{label} must be a number, for example 45 or 45.50.") from None
    if not price.is_finite():
        raise ValidationError(f"{label} must be a number, for example 45 or 45.50.")
    price = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if price <= 0:
        raise ValidationError(f"{label} must be greater than zero.")
    if price > MAX_PRICE:
        raise ValidationError(f"{label} is too large.")
    return price


def parse_date(value, label: str) -> date:
    text = str(value if value is not None else "").strip()
    if not text:
        raise ValidationError(f"{label} is required.")
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"{label} must be a valid date in YYYY-MM-DD format.") from None


def clean_name(value, label: str, max_len: int) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if not text:
        raise ValidationError(f"{label} is required.")
    if len(text) > max_len:
        raise ValidationError(f"{label} must be {max_len} characters or fewer.")
    return text
