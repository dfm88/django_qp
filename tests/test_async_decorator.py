"""Tests for async view support in validate_query_params decorator."""

import inspect

import pytest
from django.test import AsyncClient

from django_qp._compat import HAS_DRF, HAS_PYDANTIC
from django_qp.decorators import validate_query_params

drf_required = pytest.mark.skipif(not HAS_DRF, reason="DRF not installed")
pydantic_required = pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic not installed")

pytestmark = pytest.mark.asyncio


@pydantic_required
class TestAsyncDjangoDecorator:
    """Test async Django FBVs with the decorator."""

    async def test_valid_params(self) -> None:
        """Test async FBV with valid query parameters."""
        client = AsyncClient()
        response = await client.get("/async-test-func/?name=John&age=25")
        assert response.status_code == 200
        assert "async: name=John, age=25" in response.content.decode()

    async def test_invalid_params(self) -> None:
        """Test async FBV with invalid query parameters."""
        client = AsyncClient()
        response = await client.get("/async-test-func/?name=John&age=invalid")
        assert response.status_code == 422
        error_data = response.json()
        field_names = [e["field"] for e in error_data["errors"]]
        assert "age" in field_names

    async def test_missing_required_param(self) -> None:
        """Test async FBV with missing required parameter."""
        client = AsyncClient()
        response = await client.get("/async-test-func/?age=25")
        assert response.status_code == 422
        error_data = response.json()
        field_names = [e["field"] for e in error_data["errors"]]
        assert "name" in field_names


@pydantic_required
class TestAsyncMethodSpecificDecorator:
    """Test async FBVs with method-specific model mapping."""

    async def test_get_method_validation(self) -> None:
        """Test GET request with method-specific async validation."""
        client = AsyncClient()
        response = await client.get("/async-method-specific/?filter=active&sort_by=name")
        assert response.status_code == 200
        assert "async: filter=active, sort_by=name" in response.content.decode()

    async def test_post_method_validation(self) -> None:
        """Test POST request with method-specific async validation."""
        client = AsyncClient()
        response = await client.post("/async-method-specific/?data=test_data&priority=3")
        assert response.status_code == 200
        assert "async: data=test_data, priority=3" in response.content.decode()

    async def test_get_method_validation_error(self) -> None:
        """Test GET request with invalid parameters."""
        client = AsyncClient()
        response = await client.get("/async-method-specific/?invalid=param")
        assert response.status_code == 422
        error_data = response.json()
        field_names = [e["field"] for e in error_data["errors"]]
        assert "filter" in field_names

    async def test_post_method_validation_error(self) -> None:
        """Test POST request with invalid parameters."""
        client = AsyncClient()
        response = await client.post("/async-method-specific/?data=test&priority=10")
        assert response.status_code == 422
        error_data = response.json()
        field_names = [e["field"] for e in error_data["errors"]]
        assert "priority" in field_names


@pytest.mark.skipif(not HAS_PYDANTIC or not HAS_DRF, reason="pydantic and DRF required")
@pytest.mark.filterwarnings("ignore::pytest.PytestWarning")
class TestAsyncDRFDecoratorLimitation:
    """Document that DRF's @api_view does not support async FBVs.

    DRF 3.15.2's @api_view wraps views in a synchronous WrappedAPIView.dispatch()
    that never awaits the handler coroutine. When our @validate_query_params decorates
    an async def and DRF's @api_view is applied on top, the async wrapper is lost
    because DRF re-wraps it synchronously.

    This test documents the limitation without registering a URL route (which would
    cause an unawaited coroutine RuntimeWarning at garbage collection).
    """

    def test_drf_api_view_wraps_async_view_as_sync(self) -> None:
        """DRF's @api_view strips async nature from decorated views."""
        from pydantic import BaseModel
        from rest_framework.decorators import api_view

        class Params(BaseModel):
            name: str

        @api_view(["GET"])
        @validate_query_params(Params)
        async def my_async_view(request):  # noqa: ANN001, ANN202
            pass  # pragma: no cover

        # Our decorator correctly produces an async wrapper...
        # but DRF's @api_view wraps it in a sync WrappedAPIView,
        # so the final view is no longer a coroutine function.
        assert not inspect.iscoroutinefunction(my_async_view)
