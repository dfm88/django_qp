"""Internal type definitions for django-qp."""

from __future__ import annotations

from typing import Generic, TypeVar

from django.http import HttpRequest

# At runtime, bound to object; under TYPE_CHECKING, could narrow to BaseModel | Struct
QParamsTypeCl = TypeVar("QParamsTypeCl")


class EnhancedHttpRequest(HttpRequest, Generic[QParamsTypeCl]):
    """HttpRequest with a typed `validated_params` attribute."""

    validated_params: QParamsTypeCl
