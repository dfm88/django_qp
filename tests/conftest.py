"""Test fixtures, mock views, and Pydantic models for django-qp tests."""

import sys
from pathlib import Path
from typing import Any, ClassVar, cast

from django.http import HttpRequest, HttpResponse
from django.views import View
from pydantic import BaseModel, Field

from django_qp import EnhancedHttpRequest
from django_qp._compat import HAS_DRF
from django_qp.decorators import validate_query_params
from django_qp.mixins import QueryParamsMixinView

# Add the project root directory to the Python path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))


# Test Pydantic models
class MockParams(BaseModel):
    """Mock Pydantic model for testing."""

    name: str
    age: int = Field(ge=0)
    tags: list[str] | None = None


class MockParams2(MockParams):
    """Extended mock params for testing method-specific validation."""


class GetQueryParams(BaseModel):
    """Mock Pydantic model for GET requests."""

    filter: str
    sort_by: str | None = None


class PostQueryParams(BaseModel):
    """Mock Pydantic model for POST requests."""

    data: str
    priority: int = Field(ge=1, le=5)


class MockViewSetParams(BaseModel):
    """Mock Pydantic model for testing."""

    sort: str
    page: int = Field(ge=1)


class NotPydanticModel:
    """Mock class that is not a Pydantic model."""

    name: str
    age: int


# Test Views
class MockBasicDjangoView(QueryParamsMixinView[MockParams], View):
    """Mock implementation of a basic Django view with query parameter validation."""

    def get_query_params_class(self, action: str | None) -> type[MockParams] | None:
        """Return MockParams for GET, MockParams2 for POST."""
        if action == "get":
            return MockParams
        elif action == "post":
            return MockParams2
        return None

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Mock implementation of a Django view get method."""
        params: MockParams | None = self.validated_params
        assert isinstance(params, MockParams)
        return HttpResponse(f"name={params.name}, age={params.age}")

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Mock implementation of a Django view post method."""
        params: MockParams | None = self.validated_params
        assert isinstance(params, MockParams2)
        return HttpResponse(f"name={params.name}, age={params.age}, tags={params.tags}")


@validate_query_params(MockParams)
def function_view(request: EnhancedHttpRequest[MockParams]) -> HttpResponse:
    """Mock implementation of a function-based view."""
    params = request.validated_params
    return HttpResponse(f"name={params.name}, age={params.age}")


# Method-specific validation test views
@validate_query_params(
    {
        "get": GetQueryParams,
        "post": PostQueryParams,
        "": MockParams,  # Default fallback
    },
)
def method_specific_view(request: HttpRequest) -> HttpResponse:
    """Handle requests with method-specific validation models."""
    if request.method == "GET":
        params = request.validated_params  # Type hint not ideal here because it depends on method
        return HttpResponse(f"filter={params.filter}, sort_by={params.sort_by or 'default'}")
    elif request.method == "POST":
        params = request.validated_params
        return HttpResponse(f"data={params.data}, priority={params.priority}")
    else:
        params = request.validated_params
        return HttpResponse(f"name={params.name}, age={params.age}")


if HAS_DRF:
    from rest_framework.decorators import action, api_view
    from rest_framework.response import Response
    from rest_framework.views import APIView
    from rest_framework.viewsets import ViewSet

    class MockBasicDRFView(QueryParamsMixinView, APIView):
        """Mock implementation of a DRF APIView with query parameter validation."""

        validated_params_model = MockParams

        def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
            """Mock implementation of a DRF view get method."""
            params = self.validated_params
            return Response(
                {
                    "name": params.name,
                    "age": params.age,
                    "tags": params.tags,
                },
            )

    class MockViewSet(QueryParamsMixinView[MockParams | MockViewSetParams], ViewSet):
        """Mock implementation of a DRF ViewSet with method-specific validation."""

        def get_query_params_class(  # noqa: D102
            self,
            action: str | None,
        ) -> type[MockParams] | type[MockViewSetParams] | None:
            if action == "list":
                return MockViewSetParams
            elif action == "retrieve" or action == "custom_action":
                return MockParams
            elif action == "not_a_pydantic_model":
                return NotPydanticModel
            return None

        def list(self, request: HttpRequest) -> Response:
            """Mock implementation of a DRF view list method."""
            params: MockViewSetParams | None = self.validated_params
            assert isinstance(params, MockViewSetParams)
            return Response(
                {
                    "sort": params.sort,
                    "page": params.page,
                },
            )

        def retrieve(self, request: HttpRequest, pk: int | str | None = None) -> Response:
            """Mock implementation of a DRF view retrieve method."""
            params: MockParams | None = self.validated_params
            assert isinstance(params, MockParams)
            return Response(
                {
                    "name": params.name,
                    "age": params.age,
                },
            )

        @action(detail=False, methods=["get"])
        def custom_action(self, request: HttpRequest) -> Response:
            """Mock implementation of a DRF view custom action method."""
            params = self.validated_params
            return Response(
                {
                    "name": params.name,
                    "age": params.age,
                },
            )

        @action(detail=False, methods=["get"])
        def not_a_pydantic_model(self, request: HttpRequest) -> Response:
            """Mock implementation of a DRF view custom action method."""
            params = self.validated_params
            return Response(
                {
                    "name": params.name,
                    "age": params.age,
                },
            )

    class CustomErrorView(QueryParamsMixinView, APIView):
        """View to test custom error messages for validation errors."""

        validated_params_model = MockParams
        # Define custom error messages
        field_error_messages: ClassVar[dict[str, dict[str, str]]] = {
            "age": {
                "greater_than_equal": "Age must be a positive number.",
                "__all__": "Invalid age format provided.",
            },
            "name": {
                "type_error": "Please provide a valid name.",
                "__all__": "Name is required.",
            },
        }

        def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
            """Handle GET request."""
            return Response({"success": True})

    class CustomStatusView(QueryParamsMixinView, APIView):
        """View to test custom status codes for validation errors."""

        validated_params_model = MockParams
        # Define field-specific status codes
        field_error_status_codes: ClassVar[dict[str, int]] = {
            "age": 400,  # Bad request for age errors
            "name": 404,  # Not found for name errors
        }

        def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
            """Handle GET request."""
            return Response({"success": True})

    @api_view(["GET", "POST"])
    @validate_query_params(MockParams)
    def api_function_view(request: EnhancedHttpRequest[MockParams]) -> Response:
        """Mock implementation of a function-based view with DRF."""
        params = request.validated_params

        response = {
            "name": params.name,
            "age": params.age,
            "tags": params.tags,
            "method": request.method,
        }

        if request.method == "POST":
            # Handle POST request
            return Response(
                response,
            )
        elif request.method == "GET":
            # Handle GET request

            return Response(
                response,
            )
        else:
            return Response(status=405)

    # API function view with method-specific validation
    @api_view(["GET", "POST"])
    @validate_query_params(
        {
            "get": GetQueryParams,
            "post": PostQueryParams,
        },
    )
    def api_method_specific_view(request: HttpRequest) -> Response:
        """API view with method-specific validation."""
        if request.method == "GET":
            params = request.validated_params
            return Response(
                {
                    "filter": params.filter,
                    "sort_by": params.sort_by,
                    "method": request.method,
                },
            )
        elif request.method == "POST":
            params = request.validated_params
            return Response(
                {
                    "data": params.data,
                    "priority": params.priority,
                    "method": request.method,
                },
            )

    # Define a resolver function for dynamic model selection
    def dynamic_model_resolver(request: HttpRequest) -> type[BaseModel]:
        """Dynamic model resolver based on query parameters."""
        # Check if there's a specific parameter in the request that determines model
        if request.GET.get("use_post_model") == "true":
            return PostQueryParams
        return GetQueryParams

    @api_view(["GET"])
    @validate_query_params(dynamic_model_resolver)
    def dynamic_model_view(request: EnhancedHttpRequest[GetQueryParams | PostQueryParams]) -> Response:
        """View with dynamically resolved model."""
        params = request.validated_params
        if hasattr(params, "filter"):  # It's GetQueryParams
            params = cast(GetQueryParams, params)
            return Response(
                {
                    "model": "GetQueryParams",
                    "filter": params.filter,
                    "sort_by": params.sort_by,
                },
            )
        else:  # It's PostQueryParams
            params = cast(PostQueryParams, params)
            return Response(
                {
                    "model": "PostQueryParams",
                    "data": params.data,
                    "priority": params.priority,
                },
            )
