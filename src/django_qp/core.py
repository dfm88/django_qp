"""Core validation engine for django-qp query parameter processing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.http import HttpRequest, HttpResponse, JsonResponse

from ._compat import HAS_DRF
from .backends import get_backend
from .exceptions import QueryParamsError

if TYPE_CHECKING:
    from django.http import QueryDict


def _extract_request_data(request: HttpRequest) -> QueryDict | dict[str, Any]:
    """Extract query parameters from a request.

    Returns the raw QueryDict to preserve multi-value keys.
    Replace this function to customize parameter extraction.

    Args:
        request: The HTTP request object

    Returns:
        A QueryDict or dict of query parameters
    """
    return request.GET


def process_query_params(
    request: HttpRequest,
    model: type,
) -> Any:  # noqa: ANN401
    """Process and validate query parameters using a model.

    Auto-detects the validation backend based on the model type
    (pydantic BaseModel or msgspec Struct).

    Args:
        request: Django/DRF HTTP request
        model: Model class for validation (BaseModel or Struct)

    Returns:
        Validated model instance

    Raises:
        QueryParamsError: When validation fails
        TypeError: When model type is not supported by any backend
    """
    backend = get_backend(model)
    list_fields = backend.get_list_fields(model)

    query_dict = _extract_request_data(request)

    # Convert list-typed fields using getlist() for multi-value support
    processed_dict: dict[str, Any] = {}
    for field_name, value in query_dict.items():
        if field_name in list_fields:
            # Use getlist() if available (QueryDict), otherwise wrap scalar
            if hasattr(query_dict, "getlist"):
                values = query_dict.getlist(field_name)
            else:
                values = value if isinstance(value, list) else [value]
            # Comma-split each element, then flatten
            expanded: list[Any] = []
            for v in values:
                if isinstance(v, str):
                    expanded.extend(v.split(","))
                else:
                    expanded.append(v)
            processed_dict[field_name] = expanded
        else:
            processed_dict[field_name] = value

    try:
        return backend.validate(model, processed_dict)
    except Exception as e:
        raise QueryParamsError(e) from e


def create_error_response(
    exc: Exception,
    error_title: str = "Validation Error",
    error_status_code: int = 422,
    *,
    is_drf: bool = False,
    model: type | None = None,
    field_error_messages: dict[str, dict[str, str]] | None = None,
    field_error_status_codes: dict[str, int] | None = None,
) -> HttpResponse:
    """Create an appropriate error response for Django or DRF.

    Args:
        exc: The QueryParamsError wrapping the backend exception.
        error_title: Title to include in error response
        error_status_code: Default HTTP status code to use
        is_drf: Whether to return a DRF Response
        model: The model class (used to resolve the backend for error formatting)
        field_error_messages: Dict mapping field names to custom error messages
        field_error_status_codes: Dict mapping field names to custom HTTP status codes

    Returns:
        Either a DRF Response or Django JsonResponse with error details

    Raises:
        ImportError: When is_drf=True but djangorestframework is not installed
    """
    # Get the original backend exception from QueryParamsError
    original_exc = exc.original_exception if isinstance(exc, QueryParamsError) else exc

    if model is not None:
        backend = get_backend(model)
        formatted_errors, status_code = backend.format_errors(
            original_exc,
            field_error_messages,
            field_error_status_codes,
            error_status_code,
        )
    else:
        formatted_errors = [{"field": "", "type": "validation_error", "msg": str(original_exc)}]
        status_code = error_status_code

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
    """Determine if a request is a DRF request or a standard Django request.

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
