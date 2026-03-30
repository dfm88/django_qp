"""Exceptions for django-qp query parameter validation."""


class QueryParamsError(Exception):
    """Exception raised when query parameters validation fails.

    Attributes:
        original_exception: The backend-specific validation error.
    """

    def __init__(self, original_exception: Exception) -> None:
        """Initialize with the original backend validation exception.

        Args:
            original_exception: The backend-specific error (e.g., PydanticValidationError,
                msgspec.ValidationError).
        """
        self.original_exception = original_exception
        super().__init__(str(original_exception))
