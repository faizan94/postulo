"""Errors that the API turns into clean JSON responses instead of 500s."""


class PostuloError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class MissingAPIKeyError(PostuloError):
    status_code = 503
    code = "missing_api_key"

    def __init__(self, var_name: str) -> None:
        super().__init__(
            f"{var_name} is not set. Add it to .env, or set MOCK_MODE=true to use fake data."
        )


class UpstreamError(PostuloError):
    """Nebius or Tavily failed (auth, rate limit, timeout, bad output)."""

    status_code = 502
    code = "upstream_error"


class BadInputError(PostuloError):
    status_code = 400
    code = "bad_input"


class AuthError(PostuloError):
    """Missing, unknown or expired session token."""

    status_code = 401
    code = "unauthorized"


class NotFoundError(PostuloError):
    """The resource does not exist or belongs to another user (we don't say which)."""

    status_code = 404
    code = "not_found"
