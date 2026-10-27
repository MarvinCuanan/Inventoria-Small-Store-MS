"""Domain objects for authenticated people and validated stock levels."""
from __future__ import annotations

from abc import ABC, abstractmethod

from core.errors import ValidationError
from core.security import verify_password


class PasswordCredentials:
    def __init__(self, password_hash: str):
        self._password_hash = password_hash

    @property
    def password_hash(self) -> str:
        return self._password_hash

    def verifies(self, password: str) -> bool:
        return verify_password(password, self.password_hash)


class Person(ABC):
    def __init__(self, user_id: int, username: str):
        self._user_id = user_id
        self._username = username

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @abstractmethod
    def visible_records(self, records: list[dict]) -> list[dict]:
        """Return the records this person is allowed to see."""


class Admin(Person):
    def visible_records(self, records: list[dict]) -> list[dict]:
        return records


class Staff(Person):
    def visible_records(self, records: list[dict]) -> list[dict]:
        return [record for record in records if record["user_id"] == self.user_id]


def person_for(user: dict) -> Person:
    person_type = Admin if user["role"] == "Admin" else Staff
    return person_type(user["user_id"], user["username"])


class StockLevel:
    """Encapsulates a non-negative stock quantity."""

    def __init__(self, quantity: int):
        self.quantity = quantity

    @property
    def quantity(self) -> int:
        return self._quantity

    @quantity.setter
    def quantity(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValidationError("Stock quantity must be a non-negative whole number.")
        self._quantity = value

    def increase(self, amount: int) -> int:
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValidationError("Stock increase must be a positive whole number.")
        self.quantity += amount
        return self.quantity

    def decrease(self, amount: int) -> int:
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValidationError("Stock decrease must be a positive whole number.")
        if amount > self.quantity:
            raise ValidationError("Stock cannot be reduced below zero.")
        self.quantity -= amount
        return self.quantity
