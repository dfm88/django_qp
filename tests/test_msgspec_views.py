"""Integration tests for msgspec-backed views."""

import json

import pytest
from django.test import Client

from django_qp._compat import HAS_MSGSPEC

msgspec_required = pytest.mark.skipif(not HAS_MSGSPEC, reason="msgspec not installed")


@msgspec_required
@pytest.mark.django_db
class TestMsgspecMixinView:
    """Tests for the mixin view with msgspec backend."""

    def test_valid_params(self, client: Client) -> None:
        """Test valid query params with msgspec mixin view."""
        response = client.get("/msgspec/basic/", {"name": "alice", "age": "30"})
        assert response.status_code == 200
        assert b"name=alice" in response.content

    def test_missing_required_param(self, client: Client) -> None:
        """Test missing required param returns 422 error."""
        response = client.get("/msgspec/basic/", {"name": "alice"})
        assert response.status_code == 422

    def test_invalid_type(self, client: Client) -> None:
        """Test invalid type returns 422 error."""
        response = client.get("/msgspec/basic/", {"name": "alice", "age": "not_a_number"})
        assert response.status_code == 422

    def test_error_response_format(self, client: Client) -> None:
        """Test error response has expected structure."""
        response = client.get("/msgspec/basic/", {"name": "alice"})
        data = json.loads(response.content)
        assert "title" in data
        assert "errors" in data
        assert isinstance(data["errors"], list)

    def test_optional_field_omitted(self, client: Client) -> None:
        """Test that optional fields can be omitted."""
        response = client.get("/msgspec/basic/", {"name": "alice", "age": "30"})
        assert response.status_code == 200

    def test_optional_list_field_provided(self, client: Client) -> None:
        """Test that optional list fields are accepted when provided."""
        response = client.get("/msgspec/basic/", {"name": "alice", "age": "30", "tags": "x,y"})
        assert response.status_code == 200


@msgspec_required
@pytest.mark.django_db
class TestMsgspecDecoratorView:
    """Tests for the decorator view with msgspec backend."""

    def test_valid_params(self, client: Client) -> None:
        """Test valid query params with msgspec decorator view."""
        response = client.get("/msgspec/function/", {"name": "bob", "age": "25"})
        assert response.status_code == 200
        assert b"name=bob" in response.content

    def test_missing_required_param(self, client: Client) -> None:
        """Test missing required param returns 422 error."""
        response = client.get("/msgspec/function/")
        assert response.status_code == 422

    def test_invalid_type(self, client: Client) -> None:
        """Test invalid type returns 422 error."""
        response = client.get("/msgspec/function/", {"name": "bob", "age": "not_a_number"})
        assert response.status_code == 422

    def test_comma_separated_list(self, client: Client) -> None:
        """Test comma-separated values are split into lists for msgspec."""
        response = client.get("/msgspec/function/", {"name": "bob", "age": "25", "tags": "a,b,c"})
        assert response.status_code == 200

    def test_error_response_format(self, client: Client) -> None:
        """Test error response has expected structure."""
        response = client.get("/msgspec/function/")
        data = json.loads(response.content)
        assert "title" in data
        assert "errors" in data
        assert isinstance(data["errors"], list)
