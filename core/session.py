"""SessionManager - Singleton holding the logged-in user and what they are allowed to do."""
from __future__ import annotations

from datetime import datetime

from core.domain import Person, person_for
from core.errors import AppError, PermissionDenied


class SessionManager:
    _instance = None

    def __init__(self):
        self.current_user: dict | None = None
        self.permissions: set[str] = set()
        self.login_time: datetime | None = None
        self.person: Person | None = None

    @classmethod
    def get_instance(cls) -> "SessionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self, user: dict, permissions: set[str]) -> None:
        self.person = person_for(user)
        self.current_user = {key: value for key, value in user.items() if key != "password_hash"}
        self.permissions = set(permissions)
        self.login_time = datetime.now()

    def end(self) -> None:
        self.current_user, self.permissions, self.login_time, self.person = None, set(), None, None

    def is_logged_in(self) -> bool:
        return self.current_user is not None

    def is_admin(self) -> bool:
        return bool(self.current_user) and self.current_user["role"] == "Admin"

    def has_permission(self, name: str) -> bool:
        return name in self.permissions

    def require(self, name: str, action: str = "do this") -> None:
        if not self.is_logged_in():
            raise AppError("Please log in first.")
        if name not in self.permissions:
            raise PermissionDenied(f"Your role is not allowed to {action}.")
