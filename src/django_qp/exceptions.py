"""Exceptions for django-qp query parameter validation."""

from .internal_typing import ErrorList


class QueryParamsError(Exception):
    """Exception raised when query parameters validation fails.

    Attributes:
        detail: Detailed error information from Pydantic
    """

    def __init__(self, detail: list[ErrorList]) -> None:
        """Initialize with validation error details from Pydantic."""
        self.detail = detail
        super().__init__(str(detail))
