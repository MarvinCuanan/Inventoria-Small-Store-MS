"""Input validation helpers (the 'Validator' utility from the UML class diagram)."""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_USERNAME = re.compile(r"^[A-Za-z0-9_.]{3,30}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DIGITS = re.compile(r"^\d+$")


class Validator:
    @staticmethod
    def is_empty(value) -> bool:
        return value is None or str(value).strip() == ""

    @staticmethod
    def is_valid_username(value: str) -> bool:
        return bool(_USERNAME.match(value or ""))

    @staticmethod
    def is_valid_email(value: str) -> bool:
        return bool(_EMAIL.match(value or ""))

    @staticmethod
    def passwords_match(password: str, confirm: str) -> bool:
        return password == confirm

    @staticmethod
    def parse_price(text) -> Decimal | None:
        """'1,250.5' -> Decimal('1250.50'); None when invalid or negative."""
        cleaned = str(text or "").replace("₱", "").replace(",", "").strip()
        try:
            value = Decimal(cleaned)
        except InvalidOperation:
            return None
        if not value.is_finite() or value < 0 or value > Decimal("99999999.99"):
            return None
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def parse_int(text, minimum: int = 0, maximum: int = 2_000_000_000) -> int | None:
        cleaned = str(text or "").strip()
        if not _DIGITS.match(cleaned):
            return None
        value = int(cleaned)
        return value if minimum <= value <= maximum else None

    @staticmethod
    def parse_date(text) -> date | None:
        try:
            return datetime.strptime(str(text or "").strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def is_valid_date_range(start: date | None, end: date | None) -> bool:
        return start is None or end is None or start <= end
