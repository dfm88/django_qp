"""Msgspec validation backend for django-qp."""

from __future__ import annotations

import re
from typing import Any

import msgspec  # type: ignore[import]
import msgspec.structs  # type: ignore[import]

from django_qp.backends import contains_list_type

# Pattern to extract field path from msgspec error messages.
# msgspec errors look like: "Expected int, got str - at `$.age`"
_FIELD_PATTERN = re.compile(r"at `\$\.(\w+)`")


class MsgspecBackend:
    """Validation backend for msgspec Struct models."""

    @staticmethod
    def is_model(model: type) -> bool:
        """Check if a class is a msgspec Struct subclass.

        Args:
            model: The class to check.

        Returns:
            True if model is a msgspec.Struct subclass.
        """
        return isinstance(model, type) and issubclass(model, msgspec.Struct)

    @staticmethod
    def get_list_fields(model: type) -> set[str]:
        """Return field names typed as list[...] from a msgspec Struct.

        Args:
            model: A msgspec.Struct subclass.

        Returns:
            Set of field names with list-type annotations.
        """
        result: set[str] = set()
        for field in msgspec.structs.fields(model):
            if contains_list_type(field.type):
                result.add(field.name)
        return result

    @staticmethod
    def validate(model: type, data: dict[str, Any]) -> Any:  # noqa: ANN401
        """Validate data by converting it to a msgspec Struct.

        Uses strict=False to allow string-to-type coercion, which is
        necessary since query parameters arrive as strings.

        Args:
            model: A msgspec.Struct subclass.
            data: Dictionary of query parameter data.

        Returns:
            A validated Struct instance.

        Raises:
            msgspec.ValidationError: When validation fails.
        """
        return msgspec.convert(data, model, strict=False)

    @staticmethod
    def format_errors(
        exc: Exception,
        field_error_messages: dict[str, dict[str, str]] | None,
        field_error_status_codes: dict[str, int] | None,
        default_status_code: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Format msgspec validation errors.

        Parses msgspec's error string to extract field names and messages.
        Msgspec errors are a single string, e.g.:
        - "Expected `int`, got `str` - at `$.age`"
        - "Object missing required field `name`"

        Args:
            exc: The msgspec.ValidationError.
            field_error_messages: Custom error message overrides per field/type.
            field_error_status_codes: Custom status code overrides per field.
            default_status_code: Default HTTP status code.

        Returns:
            Tuple of (error list, HTTP status code).
        """
        if not isinstance(exc, msgspec.ValidationError):
            raise TypeError(f"Expected msgspec.ValidationError, got {type(exc).__name__}")

        error_msg = str(exc)
        formatted: list[dict[str, Any]] = []

        field_match = _FIELD_PATTERN.search(error_msg)
        if field_match:
            field_name = field_match.group(1)
        else:
            missing_match = re.search(r"missing required field `(\w+)`", error_msg)
            field_name = missing_match.group(1) if missing_match else ""

        if "missing required field" in error_msg:
            error_type = "missing"
        elif "Expected" in error_msg:
            error_type = "type_error"
        else:
            error_type = "validation_error"

        custom_message = None
        if field_error_messages and field_name:
            field_messages = field_error_messages.get(field_name, {})
            custom_message = field_messages.get(error_type) or field_messages.get("__all__")

        formatted.append(
            {
                "field": field_name,
                "type": error_type,
                "msg": custom_message or error_msg,
            }
        )

        status_code = default_status_code
        if field_name and field_error_status_codes:
            status_code = field_error_status_codes.get(field_name, default_status_code)

        return formatted, status_code
