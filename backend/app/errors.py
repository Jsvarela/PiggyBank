class DomainError(Exception):
    """Regla de negocio violada (422)."""


class NotFound(DomainError):
    """404."""


class Conflict(DomainError):
    """409."""
