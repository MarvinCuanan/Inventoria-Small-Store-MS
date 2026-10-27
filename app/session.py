"""Holds the currently logged-in user and answers permission questions."""
from dataclasses import dataclass
from typing import Optional

from .errors import PermissionDenied


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    username: str
    role_name: str
    permissions: frozenset


class Session:
    _user: Optional[CurrentUser] = None

    @classmethod
    def start(cls, user: CurrentUser) -> None:
        cls._user = user

    @classmethod
    def end(cls) -> None:
        cls._user = None

    @classmethod
    def current(cls) -> Optional[CurrentUser]:
        return cls._user

    @classmethod
    def can(cls, permission: str) -> bool:
        return cls._user is not None and permission in cls._user.permissions

    @classmethod
    def require(cls, permission: str) -> CurrentUser:
        if cls._user is None:
            raise PermissionDenied("Please log in first.")
        if permission not in cls._user.permissions:
            raise PermissionDenied("You do not have permission to do that.")
        return cls._user
