"""Backend abstraction layer for validation engines."""

from __future__ import annotations

import types
from typing import Any, Protocol, Union, get_args, get_origin

from django_qp._compat import HAS_MSGSPEC, HAS_PYDANTIC


class ValidationBackend(Protocol):
    """Protocol defining the interface for validation backends.

    Each backend must implement these static methods to support
    field introspection, validation, and error formatting.
    """

    @staticmethod
    def is_model(model: type) -> bool:
        """Check if a class belongs to this backend.

        Args:
            model: The class to check.

        Returns:
            True if the class is a valid model for this backend.
        """
        ...

    @staticmethod
    def get_list_fields(model: type) -> set[str]:
        """Return field names typed as list[...], for comma-split logic.

        Args:
            model: The model class to inspect.

        Returns:
            Set of field names that have list-type annotations.
        """
        ...

    @staticmethod
    def validate(model: type, data: dict[str, Any]) -> Any:  # noqa: ANN401
        """Validate data against the model, return validated instance.

        Args:
            model: The model class to validate against.
            data: Dictionary of query parameter data.

        Returns:
            A validated model instance.

        Raises:
            QueryParamsError: When validation fails.
        """
        ...

    @staticmethod
    def format_errors(
        exc: Exception,
        field_error_messages: dict[str, dict[str, str]] | None,
        field_error_status_codes: dict[str, int] | None,
        default_status_code: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Format errors in native style, apply customizations.

        Args:
            exc: The backend-specific validation exception.
            field_error_messages: Custom error message overrides per field/type.
            field_error_status_codes: Custom HTTP status code overrides per field.
            default_status_code: Default HTTP status code for errors.

        Returns:
            Tuple of (formatted error list, HTTP status code).
        """
        ...


def contains_list_type(annotation: type | None) -> bool:
    """Recursively check if a type annotation contains a list type.

    Handles nested unions and complex type hierarchies.

    Args:
        annotation: Type annotation to check.

    Returns:
        True if the annotation contains a list type, False otherwise.
    """
    if not annotation:
        return False

    origin = get_origin(annotation)
    if origin is list:
        return True

    if origin in (
        Union,
        types.UnionType,
    ) or isinstance(origin, types.UnionType):
        for arg in get_args(annotation):
            if contains_list_type(arg):
                return True

    return False


# Registry of available backends (populated at import time)
_backends: list[type[ValidationBackend]] = []

if HAS_MSGSPEC:
    from django_qp.backends.msgspec_backend import MsgspecBackend

    _backends.append(MsgspecBackend)

if HAS_PYDANTIC:
    from django_qp.backends.pydantic_backend import PydanticBackend

    _backends.append(PydanticBackend)


def get_backend(model: type) -> type[ValidationBackend]:
    """Auto-detect the appropriate backend for a model class.

    Tries each registered backend's is_model() and returns the first match.

    Args:
        model: The model class to find a backend for.

    Returns:
        The backend class that supports the given model type.

    Raises:
        TypeError: If no backend supports the model type.
    """
    for backend in _backends:
        if backend.is_model(model):
            return backend

    installed = []
    if HAS_PYDANTIC:
        installed.append("pydantic.BaseModel")
    if HAS_MSGSPEC:
        installed.append("msgspec.Struct")

    raise TypeError(
        f"No validation backend found for {model.__name__}. "
        f"Model must be a subclass of: {', '.join(installed)}",
    )
