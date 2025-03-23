from typing import ClassVar, Generic, Optional, Union, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpRequest
from pydantic import BaseModel
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSetMixin

from .core import process_query_params
from .exceptions import QueryParamsError
from .typing import ErrorDict, ErrorList, ModelType, QParamsTypeCl, QueryParamsModelMap


class QueryParamsMixin(Generic[QParamsTypeCl]):
    """
    Mixin to add query parameter validation to Django/DRF views.

    Generic Parameters:
        QParamsTypeCl: A Pydantic BaseModel subclass that defines the query parameters structure.

    Attributes:
        query_params_model: The Pydantic model class to use for validation.
        query_params: The validated query parameters instance.
    """

    query_params_model: Optional[type[QParamsTypeCl]] = None
    query_params: Optional[QParamsTypeCl] = None

    @staticmethod
    def _validate_model(model: Union[BaseModel, object]) -> bool:
        """
        Validate that the provided model is a Pydantic BaseModel subclass.

        Args:
            model: The model class to validate

        Returns:
            bool: True if valid, False otherwise
        """
        return model is not None and isinstance(model, type) and issubclass(model, BaseModel)

    @staticmethod
    def format_pydantic_errors_for_django(errors: list[ErrorList]) -> ErrorDict:
        """
        Convert Pydantic validation errors to Django-compatible format.

        Args:
            errors: List of Pydantic error dictionaries

        Returns:
            Dict mapping field names to lists of error messages
        """
        django_errors: dict = {}

        for error in errors:
            field_name = error.get("loc", ("",))[0]  # Get field name from the location tuple
            message = error.get("msg", "Validation error")

            if field_name not in django_errors:
                django_errors[field_name] = []
            django_errors[field_name].append(message)

        return django_errors

    @staticmethod
    def format_pydantic_errors_for_drf(errors: list[ErrorList]) -> ErrorDict:
        """
        Convert Pydantic validation errors to DRF-compatible format.

        Args:
            errors: List of Pydantic error dictionaries

        Returns:
            Dict mapping field names to lists of error messages
        """
        drf_errors: dict = {}

        for error in errors:
            field_name = error.get("loc", ("",))[0]  # Get field name from the location tuple
            message = error.get("msg", "Validation error")

            if field_name not in drf_errors:
                drf_errors[field_name] = []
            drf_errors[field_name].append(message)

        return drf_errors

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> APIView:
        """
        Process query params before view method execution.

        Args:
            request: The HTTP request
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            The result of the parent dispatch method

        Raises:
            DjangoValidationError or DRFValidationError on validation failure
        """

        if self.query_params_model:
            if not self._validate_model(self.query_params_model):
                if isinstance(self, (APIView, ViewSetMixin)):
                    raise DRFValidationError(
                        {"query_params_model": ["Must be a Pydantic BaseModel subclass."]},
                    )
                raise DjangoValidationError(
                    {"query_params_model": ["Must be a Pydantic BaseModel subclass."]},
                )

            try:
                self.query_params = process_query_params(request, self.query_params_model)
            except QueryParamsError as e:
                if isinstance(self, (APIView, ViewSetMixin)):
                    # Format errors specifically for DRF
                    drf_errors = self.format_pydantic_errors_for_drf(e.detail)
                    raise DRFValidationError(drf_errors) from e
                # Django needs a specific format
                django_errors = self.format_pydantic_errors_for_django(e.detail)
                raise DjangoValidationError(django_errors) from e
        return super().dispatch(request, *args, **kwargs)  # type: ignore


class ViewSetQueryParamsMixin(QueryParamsMixin[QParamsTypeCl]):
    """
    Extended mixin for ViewSets supporting action-specific models.

    Generic Parameters:
        QParamsTypeCl: A Pydantic BaseModel subclass that defines the query parameters structure.

    Attributes:
        query_params_models: Dictionary mapping action names to Pydantic model classes.
        default_query_params_model: Default model to use when no action-specific model is found.
    """

    query_params_models: ClassVar[Optional[dict[str, ModelType]]] = None
    default_query_params_model: ClassVar[Optional[ModelType]] = None

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the query_params_models attribute.
        """
        self.init_query_params_models(
            query_params_models=self.query_params_models,
            default_query_params_model=self.default_query_params_model,
        )
        super().__init__(*args, **kwargs)

    @classmethod
    def init_query_params_models(
        cls,
        query_params_models: Optional[QueryParamsModelMap] = None,
        default_query_params_model: Optional[type[BaseModel]] = None,
    ) -> None:
        """
        Initialize the query_params_models attribute.

        Args:
            query_params_models: Dictionary mapping action names to Pydantic model classes.
            default_query_params_model: Default model to use when no action-specific model is found.
        """
        cls.query_params_models = query_params_models or {}
        cls.default_query_params_model = default_query_params_model

    def probe_action(self) -> Optional[str]:
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

    def get_query_params_model(self) -> Optional[ModelType]:
        """
        Get the appropriate model for the current action.

        Returns:
            The Pydantic model class for the current action or None

        Raises:
            DRFValidationError when an invalid model is specified
        """
        action = self.probe_action()
        if not action:
            return self.default_query_params_model

        if self.query_params_models is None:
            return self.default_query_params_model

        model = self.query_params_models.get(
            action,
            self.default_query_params_model,
        )

        if model and not self._validate_model(model):
            raise DRFValidationError(
                {
                    f"query_params_models[{action}]": [
                        "Must be a Pydantic BaseModel subclass.",
                    ],
                },
            )

        return cast(Optional[ModelType], model)

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> APIView:
        """
        Override query_params_model with action-specific model.

        Args:
            request: The HTTP request
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            The result of the parent dispatch method
        """
        model = self.get_query_params_model()
        self.query_params_model = model
        return super().dispatch(request, *args, **kwargs)  # type: ignore
