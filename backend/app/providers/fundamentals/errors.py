from app.core.errors import ErrorCode
from app.providers.exceptions import ProviderError


class SECDataUnavailableError(ProviderError):
    """A sanitized error for malformed or unavailable SEC responses."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            ErrorCode.SEC_DATA_UNAVAILABLE,
            message or "SEC Company Facts data is unavailable.",
            retryable=True,
            status_code=503,
        )


SECProviderUnavailableError = SECDataUnavailableError
