from typing import TypeVar

from pydantic import BaseModel
from pydantic_core import ErrorDetails

# Type variable for Pydantic models
QParamsTypeCl = TypeVar("QParamsTypeCl", bound=BaseModel)
# Type alias for model type
ModelType = type[QParamsTypeCl]

# Type for error details
ErrorList = ErrorDetails

# Type for error dictionaries
ErrorDict = dict[str, list[str]]

# Type for query params models mapping
QueryParamsModelMap = dict[str, type[BaseModel]]
