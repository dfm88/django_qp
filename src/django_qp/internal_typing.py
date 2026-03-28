"""Internal type definitions for django-qp."""

from typing import Generic, TypeVar

from django.http import HttpRequest
from pydantic import BaseModel
from pydantic_core import ErrorDetails

# Type variable for Pydantic models
QParamsTypeCl = TypeVar("QParamsTypeCl", bound=BaseModel)


# Enhanced HttpRequest type with validated_params
class EnhancedHttpRequest(HttpRequest, Generic[QParamsTypeCl]):
    """HttpRequest with a typed `validated_params` attribute."""

    validated_params: QParamsTypeCl


# Type for error details
ErrorList = ErrorDetails

# Type for error dictionaries
ErrorDict = dict[str, list[str]]
