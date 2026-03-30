"""Tests for Django and DRF view integration with query parameter validation."""

from typing import Any

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import Client
from django.views import View

from django_qp._compat import HAS_DRF, HAS_PYDANTIC
from django_qp.mixins import QueryParamsMixinView

if HAS_DRF:
    from rest_framework.response import Response
    from rest_framework.test import APIClient
    from rest_framework.views import APIView

drf_required = pytest.mark.skipif(not HAS_DRF, reason="DRF not installed")
pydantic_required = pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic not installed")

if HAS_PYDANTIC:
    from conftest import MockParams

    class BasicDjangoView(QueryParamsMixinView[MockParams], View):
        """Basic Django view with query parameter validation."""

        validated_params_model = MockParams

        def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            """Handle GET request and return user details."""
            params = self.validated_params
            return HttpResponse(f"name={params.name}, age={params.age}")


if HAS_PYDANTIC and HAS_DRF:

    class BasicDRFView(QueryParamsMixinView, APIView):
        """Basic DRF view with query parameter validation."""

        validated_params_model = MockParams

        def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
            """Handle GET request and return user details in JSON format."""
            params = self.validated_params
            return Response(
                {
                    "name": params.name,
                    "age": params.age,
                    "tags": params.tags,
                },
            )


@pydantic_required
@pytest.mark.django_db
class TestDjangoViews:
    """Test Django views with query parameter validation."""

    @pytest.mark.parametrize(
        "http_method",
        [
            "get",
            "post",
        ],
    )
    def test_valid_params(self, client: Client, http_method: str) -> None:
        """Test Django view with valid query parameters."""
        response = getattr(client, http_method)(
            "/test/?name=John&age=25&tags=python,django",
        )
        assert response.status_code == 200
        assert "name=John, age=25" in response.content.decode()

    def test_invalid_params(self, client: Client) -> None:
        """Test Django view with invalid query parameters."""
        response = client.get("/test/", {"name": "John", "age": "invalid"})
        assert response.status_code == 422
        assert "error" in response.content.decode()

    def test_missing_required_param(self, client: Client) -> None:
        """Test Django view with missing required query parameter."""
        response = client.get("/test/", {"age": "25"})
        assert response.status_code == 422
        assert "error" in response.content.decode()


@pytest.mark.skipif(not HAS_PYDANTIC or not HAS_DRF, reason="pydantic and DRF required")
@pytest.mark.django_db
class TestDRFViews:
    """Test DRF view with valid query parameters."""

    def test_valid_params(self) -> None:
        """Test DRF view with valid query parameters."""
        client = APIClient()
        response = client.get(
            "/api/test/",
            {"name": "John", "age": "25", "tags": "python,django"},
        )
        assert response.status_code == 200
        assert response.data["name"] == "John"
        assert response.data["age"] == 25
        assert response.data["tags"] == ["python", "django"]

    def test_invalid_params(self) -> None:
        """Test DRF view with invalid query parameters."""
        client = APIClient()
        response = client.get(
            "/api/test/",
            {"name": "John", "age": "invalid"},
        )
        assert response.status_code == 422
        assert "error" in response.content.decode()

    def test_missing_required_param(self) -> None:
        """Test DRF view with missing required query parameter."""
        client = APIClient()
        response = client.get("/api/test/", {"age": "25"})
        assert response.status_code == 422
        assert "error" in response.content.decode()


@pytest.mark.skipif(not HAS_PYDANTIC or not HAS_DRF, reason="pydantic and DRF required")
@pytest.mark.django_db
class TestViewSets:
    """Test ViewSets with various query parameters."""

    def test_list_valid_params(self) -> None:
        """Test ViewSet list method with valid query parameters."""
        client = APIClient()
        response = client.get(
            "/api/items/",
            {"sort": "name", "page": "1"},
        )
        assert response.status_code == 200
        assert response.data["sort"] == "name"
        assert response.data["page"] == 1

    def test_list_invalid_params(self) -> None:
        """Test ViewSet list method with invalid query parameters."""
        client = APIClient()
        response = client.get(
            "/api/items/",
            {"sort": "name", "page": "invalid"},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["title"] == "Validation Error"
        assert data["detail"] == "Invalid query parameters"
        page_errors = [e for e in data["errors"] if e["field"] == "page"]
        assert len(page_errors) == 1
        assert "valid integer" in page_errors[0]["msg"]

    def test_retrieve_valid_params(self) -> None:
        """Test ViewSet retrieve method with valid query parameters."""
        client = APIClient()
        response = client.get(
            "/api/items/1/",
            {"name": "John", "age": "25"},
        )
        assert response.status_code == 200
        assert response.data["name"] == "John"
        assert response.data["age"] == 25

    def test_custom_action_valid_params(self) -> None:
        """Test ViewSet custom action with valid query parameters."""
        client = APIClient()
        response = client.get(
            "/api/items/custom_action/",
            {"name": "John", "age": "25"},
        )
        assert response.status_code == 200
        assert response.data["name"] == "John"
        assert response.data["age"] == 25

    def test_custom_action_invalid_params(self) -> None:
        """Test ViewSet custom action with invalid query parameters."""
        client = APIClient()
        response = client.get(
            "/api/items/custom_action/",
            {"name": "John", "age": "invalid"},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["title"] == "Validation Error"
        assert data["detail"] == "Invalid query parameters"
        age_errors = [e for e in data["errors"] if e["field"] == "age"]
        assert len(age_errors) == 1
        assert "valid integer" in age_errors[0]["msg"]

    def test_not_a_pydantic_model(self) -> None:
        """Test ViewSet with a non-supported model type."""
        client = APIClient()
        response = client.get(
            "/api/items/not_a_pydantic_model/",
            {"name": "John", "age": "25"},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["title"] == "Validation Error"
        assert data["detail"] == "Invalid query parameters"
        assert any("not supported by any validation backend" in e["msg"] for e in data["errors"])


@pytest.mark.skipif(not HAS_PYDANTIC or not HAS_DRF, reason="pydantic and DRF required")
@pytest.mark.parametrize(
    "method",
    [
        "get",
        "post",
    ],
)
def test_api_function_view_valid_params(client: Client, method: str) -> None:
    """Test API function-based view with valid query parameters with a single model."""
    api_client = APIClient()
    response = getattr(api_client, method)(
        "/api/test-func/?name=John&age=25",
    )
    assert response.status_code == 200
    assert response.data["name"] == "John"
    assert response.data["age"] == 25
    assert response.data["method"] == method.upper()


@pytest.mark.skipif(not HAS_PYDANTIC or not HAS_DRF, reason="pydantic and DRF required")
@pytest.mark.parametrize(
    "method",
    [
        "get",
        "post",
    ],
)
def test_api_function_view_invalid_params(client: Client, method: str) -> None:
    """Test API function-based view with invalid query parameters with a single model."""
    api_client = APIClient()
    response = getattr(api_client, method)(
        "/api/test-func/?name=John&age=invalid",
    )
    assert response.status_code == 422
    data = response.json()
    assert data["title"] == "Validation Error"
    assert data["detail"] == "Invalid query parameters"
    age_errors = [e for e in data["errors"] if e["field"] == "age"]
    assert len(age_errors) == 1
    assert "valid integer" in age_errors[0]["msg"]


@pytest.mark.skipif(not HAS_PYDANTIC or not HAS_DRF, reason="pydantic and DRF required")
@pytest.mark.django_db
class TestCustomErrorHandling:
    """Test custom error handling and status codes."""

    def test_custom_error_messages(self) -> None:
        """Test view with custom error messages."""
        # Test with invalid age
        client = APIClient()
        response = client.get("/custom-errors/", {"name": "John", "age": "-5"})
        assert response.status_code == 422
        result = response.json()
        assert "errors" in result
        age_errors = [e for e in result["errors"] if e["field"] == "age"]
        assert len(age_errors) >= 1
        assert age_errors[0]["msg"] == "Age must be a positive number."

        # Test with invalid type
        response = client.get("/custom-errors/", {"name": "John", "age": "invalid"})
        assert response.status_code == 422
        result = response.json()
        age_errors = [e for e in result["errors"] if e["field"] == "age"]
        assert len(age_errors) >= 1
        assert age_errors[0]["msg"] == "Invalid age format provided."

    def test_custom_status_codes(self) -> None:
        """Test view with custom status codes."""
        # Register the view

        # Test with age error - should return 400
        client = APIClient()
        response = client.get("/custom-status/", {"name": "John", "age": "invalid"})
        assert response.status_code == 400

        # Test with name error - should return 404
        response = client.get("/custom-status/", {"age": "25"})
        assert response.status_code == 404


# Test classes for method-specific validation
@pydantic_required
class TestMethodSpecificViews:
    """Test views with method-specific validation."""

    def test_get_method_validation(self, client: Client) -> None:
        """Test GET request with method-specific validation."""
        response = client.get("/method-specific/?filter=active&sort_by=name")
        assert response.status_code == 200
        assert "filter=active, sort_by=name" in response.content.decode()

    def test_post_method_validation(self, client: Client) -> None:
        """Test POST request with method-specific validation."""
        response = client.post("/method-specific/?data=test_data&priority=3")
        assert response.status_code == 200
        assert "data=test_data, priority=3" in response.content.decode()

    def test_get_method_validation_error(self, client: Client) -> None:
        """Test GET request with invalid parameters."""
        response = client.get("/method-specific/?invalid=param")
        assert response.status_code == 422
        error_data = response.json()
        field_names = [e["field"] for e in error_data["errors"]]
        assert "filter" in field_names

    def test_post_method_validation_error(self, client: Client) -> None:
        """Test POST request with invalid parameters."""
        response = client.post("/method-specific/?data=test&priority=10")
        assert response.status_code == 422
        error_data = response.json()
        field_names = [e["field"] for e in error_data["errors"]]
        assert "priority" in field_names

    def test_fallback_method_validation(self, client: Client) -> None:
        """Test fallback to default model for unmapped methods."""
        response = client.put("/method-specific/?name=John&age=25")
        assert response.status_code == 200
        assert "name=John, age=25" in response.content.decode()


@pytest.mark.skipif(not HAS_PYDANTIC or not HAS_DRF, reason="pydantic and DRF required")
class TestApiMethodSpecificViews:
    """Test API views with method-specific validation."""

    def test_get_method_validation(self) -> None:
        """Test GET request with method-specific validation."""
        client = APIClient()
        response = client.get("/api/method-specific/?filter=active&sort_by=name")
        assert response.status_code == 200
        data = response.json()
        assert data["filter"] == "active"
        assert data["sort_by"] == "name"
        assert data["method"] == "GET"

    def test_post_method_validation(self) -> None:
        """Test POST request with method-specific validation."""
        # Ensure proper content type is set for DRF to parse the data correctly
        client = APIClient()
        response = client.post(
            "/api/method-specific/?data=test_data&priority=3",
            format="json",  # This ensures DRF properly parses the request body
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == "test_data"
        assert data["priority"] == 3
        assert data["method"] == "POST"

    def test_get_method_validation_error(self) -> None:
        """Test GET request with invalid parameters."""
        client = APIClient()
        response = client.get("/api/method-specific/?sort_by=name")  # Missing required 'filter'
        assert response.status_code == 422
        error_data = response.json()
        field_names = [e["field"] for e in error_data["errors"]]
        assert "filter" in field_names


@pytest.mark.skipif(not HAS_PYDANTIC or not HAS_DRF, reason="pydantic and DRF required")
class TestDynamicModelResolver:
    """Test views with dynamically resolved models."""

    def test_default_model_resolution(self) -> None:
        """Test default model resolution."""
        client = APIClient()
        response = client.get("/api/dynamic-model/?filter=active&sort_by=name")
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "GetQueryParams"
        assert data["filter"] == "active"

    def test_dynamic_model_resolution(self) -> None:
        """Test dynamic model resolution based on request parameters."""
        client = APIClient()
        response = client.get("/api/dynamic-model/?use_post_model=true&data=test_data&priority=3")
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "PostQueryParams"
        assert data["data"] == "test_data"

    def test_dynamic_model_validation_error(self) -> None:
        """Test validation error with dynamically resolved model."""
        client = APIClient()
        response = client.get("/api/dynamic-model/?use_post_model=true&data=test_data&priority=10")
        assert response.status_code == 422
        error_data = response.json()
        field_names = [e["field"] for e in error_data["errors"]]
        assert "priority" in field_names


class TestMROEnforcement:
    """Test that QueryParamsMixinView enforces correct MRO order."""

    def test_mro_correct_order_no_error(self) -> None:
        """Mixin before View in bases should not raise."""

        class GoodView(QueryParamsMixinView, View):
            pass

    def test_mro_wrong_order_raises_typeerror(self) -> None:
        """View before mixin in bases should raise TypeError at class definition."""
        with pytest.raises(TypeError, match="incorrect inheritance order"):

            class BadView(View, QueryParamsMixinView):
                pass

    @drf_required
    def test_mro_wrong_order_drf_apiview(self) -> None:
        """APIView before mixin should raise TypeError."""
        from rest_framework.views import APIView

        with pytest.raises(TypeError, match="incorrect inheritance order"):

            class BadDRFView(APIView, QueryParamsMixinView):
                pass

    def test_mro_intermediate_mixin_no_error(self) -> None:
        """Mixin without any View in bases should not raise."""

        class IntermediateMixin(QueryParamsMixinView):
            pass
