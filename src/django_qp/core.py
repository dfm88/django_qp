from __future__ import annotations

import types
from typing import TYPE_CHECKING, Any, Union, get_args, get_origin

from django.http import HttpRequest, JsonResponse
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from ._compat import HAS_DRF
from .exceptions import QueryParamsError

if TYPE_CHECKING:
    from .internal_typing import ErrorDict, ErrorList, QParamsTypeCl


def contains_list_type(annotation: type | None) -> bool:
    """
    Recursively check if a type annotation contains a list type at any level.
    Handles nested unions and complex type hierarchies.

    Args:
        annotation: Type annotation to check

    Returns:
        bool: True if the annotation contains a list type, False otherwise
    """
    # Check if it's directly a list
    if not annotation:
        return False

    origin = get_origin(annotation)
    if origin is list:
        return True

    # Check if it's a union (Union or |)
    if origin in (
        Union,
        types.UnionType,
    ) or isinstance(origin, types.UnionType):
        for arg in get_args(annotation):
            if contains_list_type(arg):
                return True

    return False


def _extract_request_data(request: HttpRequest) -> dict[str, Any]:
    """
    Extract query parameters from a request.

    Args:
        request: The HTTP request object

    Returns:
        A dictionary of query parameters
    """
    return request.GET.dict()


def process_query_params(
    request: HttpRequest,
    model: type[QParamsTypeCl],
) -> QParamsTypeCl:
    """
    Process and validate query parameters using a Pydantic model.

    Args:
        request: Django/DRF HTTP request
        model: Pydantic model class for validation

    Returns:
        Validated Pydantic model instance

    Raises:
        QueryParamsError: When validation fails
        TypeError: When model is not a Pydantic BaseModel subclass
    """

    if not isinstance(model, type) or not issubclass(model, BaseModel):
        raise TypeError("model must be a Pydantic BaseModel subclass")

    # Get query params and request body data based on request type and method
    query_dict = _extract_request_data(request)

    try:
        # Convert comma-separated strings to lists for list fields
        processed_dict = {}
        for field_name, value in query_dict.items():
            field = model.model_fields.get(field_name)
            if field and contains_list_type(annotation=field.annotation):
                # Only split string values, not actual lists
                if isinstance(value, str):
                    processed_dict[field_name] = value.split(",")
                else:
                    processed_dict[field_name] = value
            else:
                processed_dict[field_name] = value

        # Validate with Pydantic (with better error context)
        return model(**processed_dict)
    except PydanticValidationError as e:
        raise QueryParamsError(e.errors()) from e


def format_pydantic_errors(
    errors: list[ErrorList],
    field_error_messages: dict[str, dict[str, str]] | None = None,
) -> ErrorDict:
    """
    Convert Pydantic validation errors to a standardized format with optional custom messages.

    Args:
        errors: List of Pydantic error dictionaries
        field_error_messages: Dict mapping field names to dicts of error type -> message

    Returns:
        Dict mapping field names to lists of error messages
    """
    formatted_errors: dict[str, list[str]] = {}

    for error in errors:
        field_name = str(error.get("loc", ("",))[0])
        error_type = str(error.get("type", ""))
        default_message = error.get("msg", "Validation error")

        # Check for custom error message
        custom_message = None
        if field_error_messages:
            field_messages = field_error_messages.get(field_name, {})
            custom_message = field_messages.get(error_type) or field_messages.get("__all__")

        message = custom_message or default_message

        if field_name not in formatted_errors:
            formatted_errors[field_name] = []
        formatted_errors[field_name].append(message)

    return formatted_errors


def get_status_code_for_error(
    errors: list[ErrorList],
    default_status_code: int,
    field_error_status_codes: dict[str, int] | None = None,
) -> int:
    """
    Determine the appropriate HTTP status code for validation errors.

    When multiple fields have errors, only the first error's field determines
    the status code.

    Args:
        errors: List of Pydantic error dictionaries
        default_status_code: Default HTTP status code to use
        field_error_status_codes: Dict mapping field names to status codes

    Returns:
        HTTP status code to use for the error response
    """
    if not errors or not field_error_status_codes:
        return default_status_code

    field_name = str(errors[0].get("loc", ("",))[0])
    return field_error_status_codes.get(field_name, default_status_code)


def create_error_response(
    errors: list[ErrorList],
    error_title: str = "Validation Error",
    error_status_code: int = 422,
    is_drf: bool = False,
    field_error_messages: dict[str, dict[str, str]] | None = None,
    field_error_status_codes: dict[str, int] | None = None,
) -> JsonResponse | Any:
    """
    Create an appropriate error response for Django or DRF.

    Args:
        errors: List of Pydantic error dictionaries
        error_title: Title to include in error response
        error_status_code: Default HTTP status code to use
        is_drf: Whether to return a DRF Response
        field_error_messages: Dict mapping field names to custom error messages
        field_error_status_codes: Dict mapping field names to custom HTTP status codes

    Returns:
        Either a DRF Response or Django JsonResponse with error details

    Raises:
        ImportError: When is_drf=True but djangorestframework is not installed
    """
    status_code = get_status_code_for_error(
        errors,
        error_status_code,
        field_error_status_codes,
    )

    formatted_errors = format_pydantic_errors(errors, field_error_messages)

    response_data = {
        "title": error_title,
        "detail": "Invalid query parameters",
        "errors": formatted_errors,
    }

    if is_drf:
        if not HAS_DRF:
            raise ImportError(
                "djangorestframework is required for DRF responses. "
                "Install it with: pip install django-qp[drf]",
            )
        from rest_framework.response import Response

        return Response(response_data, status=status_code)

    return JsonResponse(response_data, status=status_code)


def is_drf_request(request: HttpRequest) -> bool:
    """
    Determine if a request is a DRF request or a standard Django request.

    Uses isinstance check against DRF's Request class when DRF is available.

    Args:
        request: The HTTP request

    Returns:
        True if it's a DRF request, False otherwise
    """
    if HAS_DRF:
        from rest_framework.request import Request as DRFRequest

        return isinstance(request, DRFRequest)
    return False
