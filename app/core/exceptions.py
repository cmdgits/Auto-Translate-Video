class AppError(Exception):
    """Base application exception."""


class DependencyError(AppError):
    """Raised when an external dependency is missing."""


class ConfigurationError(AppError):
    """Raised when runtime configuration is invalid."""


class ProcessError(AppError):
    """Raised when a pipeline step fails."""


class JobCancelledError(AppError):
    """Raised when a job is cancelled by the user."""
