"""Pydantic validation backend for django-qp."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from django_qp.backends import contains_list_type


class PydanticBackend:
    """Validation backend for pydantic BaseModel models."""

    @staticmethod
    def is_model(model: type) -> bool:
        """Check if a class is a pydantic BaseModel subclass.

        Args:
            model: The class to check.

        Returns:
            True if model is a pydantic.BaseModel subclass.
        """
        return isinstance(model, type) and issubclass(model, BaseModel)

    @staticmethod
    def get_list_fields(model: type) -> set[str]:
        """Return field names typed as list[...] from a pydantic model.

        Args:
            model: A pydantic BaseModel subclass.

        Returns:
            Set of field names with list-type annotations.
        """
        result: set[str] = set()
        for field_name, field_info in model.model_fields.items():  # type: ignore[attr-defined]
            if contains_list_type(field_info.annotation):
                result.add(field_name)
        return result

    @staticmethod
    def validate(model: type, data: dict[str, Any]) -> Any:  # noqa: ANN401
        """Validate data by constructing a pydantic model.

        Args:
            model: A pydantic BaseModel subclass.
            data: Dictionary of query parameter data.

        Returns:
            A validated BaseModel instance.

        Raises:
            PydanticValidationError: When validation fails.
        """
        return model(**data)

    @staticmethod
    def format_errors(
        exc: Exception,
        field_error_messages: dict[str, dict[str, str]] | None,
        field_error_status_codes: dict[str, int] | None,
        default_status_code: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Format pydantic validation errors, preserving native structure.

        Each error dict contains the original pydantic keys (loc, type, msg, input)
        plus a top-level 'field' key for uniform access.

        Args:
            exc: The PydanticValidationError.
            field_error_messages: Custom error message overrides per field/type.
            field_error_status_codes: Custom status code overrides per field.
            default_status_code: Default HTTP status code.

        Returns:
            Tuple of (error list, HTTP status code).
        """
        if not isinstance(exc, PydanticValidationError):
            raise TypeError(f"Expected PydanticValidationError, got {type(exc).__name__}")

        raw_errors = exc.errors()
        formatted: list[dict[str, Any]] = []

        for error in raw_errors:
            field_name = str(error.get("loc", ("",))[0])
            error_type = str(error.get("type", ""))
            default_message = error.get("msg", "Validation error")

            custom_message = None
            if field_error_messages:
                field_messages = field_error_messages.get(field_name, {})
                custom_message = field_messages.get(error_type) or field_messages.get("__all__")

            formatted.append(
                {
                    "field": field_name,
                    "loc": error.get("loc", ()),
                    "type": error_type,
                    "msg": custom_message or default_message,
                    "input": error.get("input"),
                }
            )

        status_code = default_status_code
        if formatted and field_error_status_codes:
            first_field = formatted[0]["field"]
            status_code = field_error_status_codes.get(first_field, default_status_code)

        return formatted, status_code
