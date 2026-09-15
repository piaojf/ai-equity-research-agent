from app.core.errors import ErrorCode


class ProviderError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool = False,
        status_code: int = 503,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status_code = status_code


class InvalidTickerError(ProviderError):
    def __init__(self, ticker: str) -> None:
        super().__init__(
            ErrorCode.INVALID_TICKER,
            f"Ticker '{ticker}' is not supported by the configured provider.",
            status_code=400,
        )


class ProviderConfigurationError(ProviderError):
    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.CONFIGURATION_ERROR, message, status_code=503)


class ProviderTimeoutError(ProviderError):
    def __init__(self, provider: str) -> None:
        super().__init__(
            ErrorCode.PROVIDER_TIMEOUT,
            f"Provider '{provider}' timed out.",
            retryable=True,
            status_code=504,
        )


class ProviderRateLimitError(ProviderError):
    def __init__(self, provider: str) -> None:
        super().__init__(
            ErrorCode.PROVIDER_RATE_LIMIT,
            f"Provider '{provider}' rate limit was exceeded.",
            retryable=True,
            status_code=429,
        )


class ProviderUnavailableError(ProviderError):
    def __init__(self, provider: str, message: str | None = None) -> None:
        super().__init__(
            ErrorCode.MARKET_DATA_UNAVAILABLE,
            message or f"Provider '{provider}' is unavailable.",
            retryable=True,
            status_code=503,
        )
