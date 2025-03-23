import types
from typing import Union, get_args, get_origin

from django.http import HttpRequest
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from .exceptions import QueryParamsError
from .typing import QParamsTypeCl


def contains_list_type(annotation: Union[type, None]) -> bool:
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
        types.UnionType,  # type: ignore[attr-defined]
    ) or isinstance(origin, types.UnionType):  # type: ignore[attr-defined]
        for arg in get_args(annotation):
            if contains_list_type(arg):
                return True

    return False


def process_query_params(
    request: HttpRequest,
    model: type[QParamsTypeCl],
    strict: bool = True,
) -> QParamsTypeCl:
    """
    Process and validate query parameters using a Pydantic model.

    Args:
        request: Django/DRF HTTP request
        model: Pydantic model class for validation
        strict: If True, raise error for unknown parameters

    Returns:
        Validated Pydantic model instance

    Raises:
        QueryParamsError: When validation fails
        TypeError: When model is not a Pydantic BaseModel subclass
    """

    if not isinstance(model, type) or not issubclass(model, BaseModel):
        raise TypeError("model must be a Pydantic BaseModel subclass")

    # Get query params dict based on request type
    if hasattr(request, "query_params"):  # DRF
        query_dict = request.query_params.dict()
    else:  # Django
        # Use dict() to get a simple dictionary without lists for single values
        query_dict = request.GET.dict()

    try:
        # Convert comma-separated strings to lists for list fields
        processed_dict = {}
        for field_name, value in query_dict.items():
            field = model.model_fields.get(field_name)
            if field and contains_list_type(annotation=field.annotation):
                processed_dict[field_name] = value.split(",")
            else:
                processed_dict[field_name] = value

        # Validate with Pydantic (with better error context)
        return model(**processed_dict)
    except PydanticValidationError as e:
        raise QueryParamsError(e.errors()) from e
