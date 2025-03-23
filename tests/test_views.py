# tests/test_views.py

import pytest
from conftest import MockParams
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpRequest, HttpResponse
from django.views import View
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from dj_pydantic_qparams.decorators import validate_query_params
from dj_pydantic_qparams.mixins import QueryParamsMixin


class BasicDjangoView(QueryParamsMixin, View):
    """Basic Django view with query parameter validation."""

    query_params_model = MockParams

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Handle GET request and return user details."""
        params = self.query_params
        return HttpResponse(f"name={params.name}, age={params.age}")


class BasicDRFView(QueryParamsMixin, APIView):
    """Basic DRF view with query parameter validation."""

    query_params_model = MockParams

    def get(self, request: HttpRequest, *args, **kwargs) -> Response:
        """Handle GET request and return user details in JSON format."""
        params = self.query_params
        return Response(
            {
                "name": params.name,
                "age": params.age,
                "tags": params.tags,
            },
        )


@validate_query_params(MockParams)
def function_view(request: HttpRequest) -> HttpResponse:
    """Handle GET request and return user details."""
    params = request.query_params
    return HttpResponse(f"name={params.name}, age={params.age}")


@pytest.mark.django_db
class TestDjangoViews:
    def test_valid_params(self, client: APIClient) -> None:
        """Test Django view with valid query parameters."""
        response = client.get(
            "/test/",
            {"name": "John", "age": "25", "tags": "python,django"},
        )
        assert response.status_code == 200
        assert "name=John, age=25" in response.content.decode()

    def test_invalid_params(self, client: APIClient) -> None:
        """Test Django view with invalid query parameters."""
        with pytest.raises(DjangoValidationError):
            client.get("/test/", {"name": "John", "age": "invalid"})

    def test_missing_required_param(self, client: APIClient) -> None:
        """Test Django view with missing required query parameter."""
        with pytest.raises(DjangoValidationError):
            client.get("/test/", {"age": "25"})


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
        with pytest.raises(DRFValidationError):
            _ = client.get(
                "/api/test/",
                {"name": "John", "age": "invalid"},
            )

    def test_missing_required_param(self) -> None:
        """Test DRF view with missing required query parameter."""
        client = APIClient()
        with pytest.raises(DRFValidationError):
            _ = client.get("/api/test/", {"age": "25"})


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
        with pytest.raises(DRFValidationError):
            _ = client.get(
                "/api/items/",
                {"sort": "name", "page": "invalid"},
            )

    def test_retrieve_valid_params(self) -> None:
        """Test ViewSet retrieve method with valid query parameters"""
        client = APIClient()
        response = client.get(
            "/api/items/1/",
            {"name": "John", "age": "25"},
        )
        assert response.status_code == 200
        assert response.data["name"] == "John"
        assert response.data["age"] == 25


def test_function_view_valid_params(client: APIClient) -> None:
    """Test function-based view with valid query parameters."""
    response = client.get(
        "/test-func/",
        {"name": "John", "age": "25"},
    )
    assert response.status_code == 200
    assert "name=John, age=25" in response.content.decode()


def test_function_view_invalid_params(client: APIClient) -> None:
    """Test function-based view with invalid query parameters."""
    with pytest.raises(DjangoValidationError):
        client.get("/test-func/", {"name": "John", "age": "invalid"})
