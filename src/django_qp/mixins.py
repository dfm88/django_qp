from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Generic

from pydantic import BaseModel

from .core import create_error_response, process_query_params
from .exceptions import QueryParamsError
from .internal_typing import ErrorList, QParamsTypeCl

if TYPE_CHECKING:
    from django.http import HttpRequest, JsonResponse


class QueryParamsMixinView(Generic[QParamsTypeCl]):
    """
    Mixin to add query parameter validation to Django/DRF views.

    Generic Parameters:
        QParamsTypeCl: A Pydantic BaseModel subclass that defines the query parameters structure.

    Attributes:
        validated_params_model: The Pydantic model class to use for validation.
        validated_params: The validated query parameters instance.
        error_status_code: HTTP status code to use for validation errors (default: 422).
        error_title: Title to include in error responses (default: "Validation Error").
        field_error_messages: Dict mapping field names to custom error messages.
        field_error_status_codes: Dict mapping field names to custom HTTP status codes.
    """

    validated_params_model: type[QParamsTypeCl] | None = None
    validated_params: QParamsTypeCl | None = None

    # Customizable error response settings
    error_status_code: int = 422
    error_title: str = "Validation Error"
    field_error_messages: ClassVar[dict[str, dict[str, str]] | None] = None
    field_error_status_codes: ClassVar[dict[str, int] | None] = None

    def get_query_params_class(self, action: str | None) -> type[QParamsTypeCl] | None:
        """
        Get the query parameters model class.
        Override this method to provide dynamic model selection based on request or other factors.

        Returns:
            The Pydantic model class for query parameters validation or None
        """
        return self.validated_params_model

    @staticmethod
    def _validate_model(model: BaseModel | object) -> bool:
        """
        Validate that the provided model is a Pydantic BaseModel subclass.

        Args:
            model: The model class to validate

        Returns:
            bool: True if valid, False otherwise
        """
        return model is not None and isinstance(model, type) and issubclass(model, BaseModel)

    def create_error_response(self, errors: list[ErrorList]) -> JsonResponse:
        """
        Create an error response for validation failures.

        Always returns a JsonResponse because this runs inside dispatch(),
        before DRF's content negotiation pipeline sets up renderers.
        A plain JsonResponse works in both Django and DRF contexts.

        Args:
            errors: List of Pydantic error dictionaries

        Returns:
            Django JsonResponse with error details
        """
        return create_error_response(
            errors=errors,
            error_title=self.error_title,
            error_status_code=self.error_status_code,
            is_drf=False,
            field_error_messages=self.field_error_messages,
            field_error_status_codes=self.field_error_status_codes,
        )

    def probe_action(self) -> str | None:
        """
        Determine the current action based on request method and action_map.
        """
        # If action is already set, use it
        if hasattr(self, "action") and self.action:
            return self.action

        # Try to determine action from action_map and request method
        if hasattr(self, "action_map") and hasattr(self, "request"):
            method = self.request.method.lower()
            return self.action_map.get(method)

        # Fallback to the method name
        if hasattr(self, "request"):
            return self.request.method.lower()

        return None

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        """
        Process query params before view method execution.

        Args:
            request: The HTTP request
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            The result of the parent dispatch method or an error response
        """
        action = self.probe_action()
        validated_params_model = self.get_query_params_class(action=action)

        if validated_params_model:
            if not self._validate_model(validated_params_model):
                return self.create_error_response(
                    [
                        {
                            "loc": ("validated_params_model",),
                            "msg": "Must be a Pydantic BaseModel subclass.",
                            "type": "validation_error",
                            "input": validated_params_model,
                        },
                    ],
                )
            try:
                self.validated_params = process_query_params(request, validated_params_model)
            except QueryParamsError as e:
                return self.create_error_response(e.detail)

        return super().dispatch(request, *args, **kwargs)  # type: ignore
