"""Application-level exceptions. The UI shows their message to the user."""


class AppError(Exception):
    """Base class for errors that are safe to show to the user."""


class ValidationError(AppError):
    """Bad input or a business rule was broken."""


class AuthError(AppError):
    """Login failed."""


class PermissionDenied(AppError):
    """The current user is not allowed to do this."""


class DatabaseError(AppError):
    """MySQL is unreachable or a query failed."""
