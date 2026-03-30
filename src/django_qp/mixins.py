"""Mixin for adding query parameter validation to class-based views."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, ClassVar, Generic

from .backends import get_backend
from .core import create_error_response, process_query_params
from .exceptions import QueryParamsError
from .internal_typing import QParamsTypeCl

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class QueryParamsMixinView(Generic[QParamsTypeCl]):
    """Mixin to add query parameter validation to Django/DRF views.

    Generic Parameters:
        QParamsTypeCl: A model type (pydantic BaseModel or msgspec Struct)
            that defines the query parameters structure.

    Attributes:
        validated_params_model: The model class to use for validation.
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

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        """Validate that the mixin appears before View in the MRO.

        Raises:
            TypeError: If the mixin comes after django.views.View in the MRO,
                which would cause dispatch() to skip validation.
        """
        super().__init_subclass__(**kwargs)

        from django.views import View

        mro = cls.__mro__
        mixin_pos = None
        view_pos = None

        for i, klass in enumerate(mro):
            if klass is QueryParamsMixinView:
                mixin_pos = i
            if klass is View:
                view_pos = i

        if mixin_pos is not None and view_pos is not None and mixin_pos > view_pos:
            raise TypeError(
                f"{cls.__name__} has incorrect inheritance order. "
                f"QueryParamsMixinView must come before {View.__name__} in base classes.\n"
                f"  Correct:   class {cls.__name__}(QueryParamsMixinView, ...View)\n"
                f"  Incorrect: class {cls.__name__}(...View, QueryParamsMixinView)",
            )

    def get_query_params_class(self, action: str | None) -> type[QParamsTypeCl] | None:
        """Get the query parameters model class.

        Override this method to provide dynamic model selection based on request or other factors.

        Returns:
            The model class for query parameters validation or None
        """
        return self.validated_params_model

    @staticmethod
    def _validate_model(model: object) -> bool:
        """Validate that the provided model is supported by a validation backend.

        Args:
            model: The model class to validate

        Returns:
            bool: True if a backend supports this model, False otherwise
        """
        if model is None or not isinstance(model, type):
            return False
        try:
            get_backend(model)
            return True
        except TypeError:
            return False

    def _create_error_response(self, exc: Exception, model: type | None = None) -> HttpResponse:
        """Create an error response for validation failures.

        Always returns a JsonResponse because this runs inside dispatch(),
        before DRF's content negotiation pipeline sets up renderers.
        A plain JsonResponse works in both Django and DRF contexts.

        Args:
            exc: The QueryParamsError or other exception.
            model: The model class (used to resolve the backend for error formatting).

        Returns:
            Django HttpResponse with error details
        """
        return create_error_response(
            exc,
            error_title=self.error_title,
            error_status_code=self.error_status_code,
            is_drf=False,
            model=model,
            field_error_messages=self.field_error_messages,
            field_error_status_codes=self.field_error_status_codes,
        )

    def probe_action(self) -> str | None:
        """Determine the current action based on request method and action_map."""
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

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        """Process query params before view method execution.

        Supports both sync and async views. Validation is always synchronous
        (reads request.GET + backend validation). For async views, wraps the entire
        dispatch flow in a coroutine so Django's ASGI handler can await it.

        Args:
            request: The HTTP request
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            The result of the parent dispatch method or an error response.
            Returns a coroutine when the view is async (view_is_async=True).
        """
        is_async = getattr(self.__class__, "view_is_async", False)

        if is_async:
            return self._async_dispatch(request, *args, **kwargs)

        return self._sync_dispatch(request, *args, **kwargs)

    def _sync_dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        """Synchronous dispatch path: validate params then delegate to super().

        Args:
            request: The HTTP request
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            The response from the parent dispatch method or an error response.
        """
        action = self.probe_action()
        validated_params_model = self.get_query_params_class(action=action)

        if validated_params_model:
            if not self._validate_model(validated_params_model):
                return self._create_error_response(
                    ValueError(
                        f"{validated_params_model.__name__} is not supported by any validation backend.",
                    ),
                )
            try:
                self.validated_params = process_query_params(request, validated_params_model)
            except QueryParamsError as e:
                return self._create_error_response(e, model=validated_params_model)

        return super().dispatch(request, *args, **kwargs)  # type: ignore

    async def _async_dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        """Asynchronous dispatch path: validate params then call the parent dispatch.

        Validation itself is synchronous (reads request.GET + backend validation), but
        the entire method is a coroutine so Django's ASGI handler can await it
        and error responses are returned correctly.

        For DRF views, this method bypasses DRF's own dispatch and calls the
        handler directly, awaiting it when it is a coroutine. This is required
        because DRF 3.x dispatch() is sync-only and calls finalize_response on
        whatever the handler returns — including un-awaited coroutines.

        Args:
            request: The HTTP request
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            The response from the view handler or an error response.
        """
        from ._compat import HAS_DRF

        action = self.probe_action()
        validated_params_model = self.get_query_params_class(action=action)

        if validated_params_model:
            if not self._validate_model(validated_params_model):
                return self._create_error_response(
                    ValueError(
                        f"{validated_params_model.__name__} is not supported by any validation backend.",
                    ),
                )
            try:
                self.validated_params = process_query_params(request, validated_params_model)
            except QueryParamsError as e:
                return self._create_error_response(e, model=validated_params_model)

        if HAS_DRF:
            from rest_framework.views import APIView

            if isinstance(self, APIView):
                return await self._async_drf_dispatch(request, *args, **kwargs)

        response = super().dispatch(request, *args, **kwargs)  # type: ignore

        if inspect.iscoroutine(response):
            return await response

        return response

    async def _async_drf_dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        """Async-aware DRF dispatch: replicates APIView.dispatch() with await support.

        DRF's dispatch() is synchronous and does not await async handlers.
        This method replicates its logic but awaits the handler when it returns
        a coroutine, before passing the response to finalize_response().

        Args:
            request: The HTTP request (Django HttpRequest, not yet DRF Request)
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            The finalized DRF response.
        """
        from rest_framework.views import APIView

        # Replicate DRF APIView.dispatch() with async handler support
        self.args = args  # type: ignore[attr-defined]
        self.kwargs = kwargs  # type: ignore[attr-defined]
        drf_request = self.initialize_request(request, *args, **kwargs)  # type: ignore[attr-defined]
        self.request = drf_request  # type: ignore[attr-defined]
        self.headers = self.default_response_headers  # type: ignore[attr-defined]

        try:
            self.initial(drf_request, *args, **kwargs)  # type: ignore[attr-defined]

            if drf_request.method.lower() in APIView.http_method_names:
                handler = getattr(
                    self,
                    drf_request.method.lower(),
                    self.http_method_not_allowed,  # type: ignore[attr-defined]
                )
            else:
                handler = self.http_method_not_allowed  # type: ignore[attr-defined]

            response = handler(drf_request, *args, **kwargs)  # type: ignore[misc]
            if inspect.iscoroutine(response):
                response = await response

        except Exception as exc:
            response = self.handle_exception(exc)  # type: ignore[attr-defined]

        self.response = self.finalize_response(drf_request, response, *args, **kwargs)  # type: ignore[attr-defined]
        return self.response  # type: ignore[attr-defined]
