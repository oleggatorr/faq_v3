from __future__ import annotations


class ServiceError(Exception):
    """Base class for domain/service errors."""


class NotFound(ServiceError):
    pass


class Conflict(ServiceError):
    pass


class PermissionDenied(ServiceError):
    pass


class ValidationFailed(ServiceError):
    pass

