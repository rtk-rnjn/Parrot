import aiohttp

__all__ = (
    "APIException",
    "AuthenticationRequired",
)


class APIException(Exception):
    def __init__(self, *, response: aiohttp.ClientResponse, status_code: int) -> None:
        self.response = response
        self.status_code = status_code
        super().__init__(self.status_code)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} status_code={self.status_code}>"

    def __str__(self) -> str:
        return f"HTTP Status: {self.status_code}"


class AuthenticationRequired(Exception):
    """An exception to be raised when authentication is required to use this endpoint."""
