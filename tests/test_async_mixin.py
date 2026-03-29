"""Tests for async view support in QueryParamsMixinView."""

import pytest
from django.test import AsyncClient

from django_qp._compat import HAS_DRF

drf_required = pytest.mark.skipif(not HAS_DRF, reason="DRF not installed")

pytestmark = pytest.mark.asyncio


class TestAsyncDjangoMixin:
    """Test async Django CBVs with the mixin."""

    async def test_valid_params(self) -> None:
        """Test async Django view with valid query parameters."""
        client = AsyncClient()
        response = await client.get("/async-test/?name=John&age=25")
        assert response.status_code == 200
        assert "async: name=John, age=25" in response.content.decode()

    async def test_invalid_params(self) -> None:
        """Test async Django view with invalid query parameters."""
        client = AsyncClient()
        response = await client.get("/async-test/?name=John&age=invalid")
        assert response.status_code == 422
        error_data = response.json()
        assert "age" in error_data["errors"]

    async def test_missing_required_param(self) -> None:
        """Test async Django view with missing required parameter."""
        client = AsyncClient()
        response = await client.get("/async-test/?age=25")
        assert response.status_code == 422
        error_data = response.json()
        assert "name" in error_data["errors"]


@drf_required
class TestAsyncDRFMixin:
    """Test async DRF CBVs with the mixin."""

    async def test_valid_params(self) -> None:
        """Test async DRF view with valid query parameters."""
        client = AsyncClient()
        response = await client.get("/api/async-test/?name=John&age=25&tags=a,b")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "John"
        assert data["age"] == 25
        assert data["tags"] == ["a", "b"]

    async def test_invalid_params(self) -> None:
        """Test async DRF view with invalid query parameters."""
        client = AsyncClient()
        response = await client.get("/api/async-test/?name=John&age=invalid")
        assert response.status_code == 422
        error_data = response.json()
        assert "age" in error_data["errors"]
