class AppError(Exception):
    """A problem the user can understand and fix (validation, permission, business rule)."""


class ValidationError(AppError):
    """Invalid input or a violated business rule."""


class PermissionDenied(AppError):
    """The current user is not allowed to perform an action."""


class DatabaseError(AppError):
    """A database connection or query failed."""
