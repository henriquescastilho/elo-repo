class ServiceError(Exception):
    """Base exception for service errors."""


class ProviderError(ServiceError):
    """Raised when a downstream provider fails."""
