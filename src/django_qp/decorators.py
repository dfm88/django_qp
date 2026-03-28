import functools
from collections.abc import Mapping
from typing import Any, Callable, Dict, Optional, Type, Union, cast, overload

from django.http import HttpRequest
from pydantic import BaseModel

from .core import create_error_response, is_drf_request, process_query_params
from .exceptions import QueryParamsError
from .internal_typing import EnhancedHttpRequest, QParamsTypeCl

# Type for model resolver functions
ModelResolver = Callable[[HttpRequest], Optional[Type[BaseModel]]]
# Type for method-specific model mappings
MethodModelMap = Mapping[str, Type[BaseModel]]
# Combined type for model parameter
ModelArg = Union[Type[BaseModel], MethodModelMap, ModelResolver]

# Define ViewFunc type for better readability
ViewFunc = Callable[[HttpRequest], Any]
EnhancedViewFunc = Callable[[EnhancedHttpRequest[QParamsTypeCl]], Any]


def _get_model_for_request(
    model_arg: ModelArg,
    request: HttpRequest,
) -> Optional[Type[BaseModel]]:
    """
    Resolve the appropriate model for the current request.

    Args:
        model_arg: Single model, method->model mapping, or model resolver callable
        request: The HTTP request

    Returns:
        The appropriate Pydantic model class or None
    """
    # Case 1: Single model for all methods
    if isinstance(model_arg, type) and issubclass(model_arg, BaseModel):
        return model_arg

    # Case 2: Method-to-model mapping dictionary
    elif isinstance(model_arg, dict):
        # Get method name and convert to uppercase
        method = request.method and request.method.lower()
        # Try to get a model specifically for this method
        model = model_arg.get(method)
        if model is not None:
            return model
        # Fall back to default model if available (empty string key)
        return model_arg.get("")

    # Case 3: Callable resolver function
    elif callable(model_arg):
        return model_arg(request)

    return None


@overload
def validate_query_params(
    model: Type[QParamsTypeCl],
    error_status_code: int = 422,
    error_title: str = "Validation Error",
    field_error_messages: Optional[Dict[str, Dict[str, str]]] = None,
    field_error_status_codes: Optional[Dict[str, int]] = None,
) -> Callable[[ViewFunc], Callable[[HttpRequest], Any]]: ...


@overload
def validate_query_params(
    model: MethodModelMap,
    error_status_code: int = 422,
    error_title: str = "Validation Error",
    field_error_messages: Optional[Dict[str, Dict[str, str]]] = None,
    field_error_status_codes: Optional[Dict[str, int]] = None,
) -> Callable[[ViewFunc], Callable[[HttpRequest], Any]]: ...


@overload
def validate_query_params(
    model: ModelResolver,
    error_status_code: int = 422,
    error_title: str = "Validation Error",
    field_error_messages: Optional[Dict[str, Dict[str, str]]] = None,
    field_error_status_codes: Optional[Dict[str, int]] = None,
) -> Callable[[ViewFunc], Callable[[HttpRequest], Any]]: ...


def validate_query_params(
    model: ModelArg,
    error_status_code: int = 422,
    error_title: str = "Validation Error",
    field_error_messages: Optional[Dict[str, Dict[str, str]]] = None,
    field_error_status_codes: Optional[Dict[str, int]] = None,
) -> Callable[[ViewFunc], Callable]:
    """
    Decorator to validate query parameters using Pydantic models.

    Args:
        model: Either:
            - A single Pydantic model class
            - A dict mapping HTTP methods to model classes (use "" for default)
            - A callable that takes a request and returns a model class
        error_status_code: HTTP status code to use for validation errors (default: 422)
        error_title: Title to include in error responses (default: "Validation Error")
        field_error_messages: Dict mapping field names to custom error messages
        field_error_status_codes: Dict mapping field names to custom HTTP status codes

    Returns:
        Decorator function that validates query parameters based on request method

    Note:
        The decorated view receives a request with a `validated_params` attribute.
        To get proper type hints in your view, import and use EnhancedHttpRequest:

        ```python
        from django_qp import EnhancedHttpRequest

        @validate_query_params(MyModel)
        def my_view(request: EnhancedHttpRequest[MyModel]):
            # Type checker now knows this is available
            params = request.validated_params
        ```
    """
    field_error_messages = field_error_messages or {}
    field_error_status_codes = field_error_status_codes or {}

    def decorator(view_func: ViewFunc) -> Callable:
        @functools.wraps(view_func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            # Check if we're in a DRF context
            is_drf = is_drf_request(request)

            # Get the appropriate model for this request
            resolved_model = _get_model_for_request(model, request)

            if resolved_model is None:
                # No model specified for this method
                return view_func(request, *args, **kwargs)

            try:
                params = process_query_params(request, resolved_model)
                # Attach validated params to request for easy access
                # Use the specific model type for better type checking
                enhanced_request = cast(EnhancedHttpRequest, request)
                enhanced_request.validated_params = params
                return view_func(request, *args, **kwargs)
            except QueryParamsError as e:
                return create_error_response(
                    errors=e.detail,
                    error_title=error_title,
                    error_status_code=error_status_code,
                    is_drf=is_drf,
                    field_error_messages=field_error_messages,
                    field_error_status_codes=field_error_status_codes,
                )

        return cast(Callable, wrapper)

    return decorator
