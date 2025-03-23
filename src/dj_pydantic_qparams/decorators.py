from functools import wraps
from typing import Callable

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpRequest, HttpResponse

from .core import process_query_params
from .exceptions import QueryParamsError
from .typing import QParamsTypeCl


def validate_query_params(
    model: type[QParamsTypeCl],
    strict: bool = True,
) -> Callable:
    """
    Decorator for adding query parameter validation to function-based views.
    """

    def decorator(view_func: Callable) -> Callable:
        """
        Decorator function that wraps the view function to add query parameter validation.
        """

        @wraps(view_func)
        def wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            """
            Wrapper function that processes and validates query parameters.
            """
            try:
                query_params = process_query_params(
                    request,
                    model,
                    strict=strict,
                )
                setattr(request, "query_params", query_params)  # noqa: B010
            except QueryParamsError as e:
                raise DjangoValidationError(e.detail) from e
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
