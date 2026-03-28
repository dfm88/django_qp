from typing import Generic, TypeVar

from django.http import HttpRequest
from pydantic import BaseModel
from pydantic_core import ErrorDetails

# Type variable for Pydantic models
QParamsTypeCl = TypeVar("QParamsTypeCl", bound=BaseModel)
# Type alias for model type
ModelType = type[QParamsTypeCl]


# Enhanced HttpRequest type with validated_params
class EnhancedHttpRequest(HttpRequest, Generic[QParamsTypeCl]):
    validated_params: QParamsTypeCl


# Type for error details
ErrorList = ErrorDetails

# Type for error dictionaries
ErrorDict = dict[str, list[str]]

# Type for query params models mapping
QueryParamsModelMap = dict[str, type[BaseModel]]
