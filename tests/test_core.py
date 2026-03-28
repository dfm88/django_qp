import json

import pytest
from django.http import JsonResponse
from django.test import RequestFactory
from pydantic import BaseModel, Field

from django_qp._compat import HAS_DRF
from django_qp.core import (
    create_error_response,
    format_pydantic_errors,
    get_status_code_for_error,
    is_drf_request,
    process_query_params,
)
from django_qp.exceptions import QueryParamsError

if HAS_DRF:
    from rest_framework.response import Response


def test_list_conversion(rf: RequestFactory) -> None:
    class ListParams(BaseModel):
        tags: list[str]

    request = rf.get("/test/", {"tags": "a,b,c"})
    params = process_query_params(request, ListParams)
    assert params.tags == ["a", "b", "c"]


def test_type_conversion(rf: RequestFactory) -> None:
    class TypeParams(BaseModel):
        num: int
        flag: bool

    request = rf.get("/test/", {"num": "42", "flag": "true"})
    params = process_query_params(request, TypeParams)
    assert params.num == 42
    assert params.flag is True


def test_validation_error(rf: RequestFactory) -> None:
    class ValidParams(BaseModel):
        age: int = Field(ge=0)

    request = rf.get("/test/", {"age": "-1"})
    with pytest.raises(QueryParamsError):
        process_query_params(request, ValidParams)


def test_format_pydantic_errors() -> None:
    """Test the format_pydantic_errors function."""
    # Sample Pydantic errors
    errors = [
        {"loc": ("name",), "msg": "field required", "type": "missing"},
        {"loc": ("age",), "msg": "value is not a valid integer", "type": "type_error"},
    ]

    # Format errors with no custom messages
    formatted = format_pydantic_errors(errors)
    assert "name" in formatted
    assert "age" in formatted
    assert formatted["name"] == ["field required"]
    assert formatted["age"] == ["value is not a valid integer"]

    # Format errors with custom messages
    custom_messages = {
        "name": {"missing": "Please provide a name"},
        "age": {"type_error": "Age must be a number"},
    }

    formatted_custom = format_pydantic_errors(errors, custom_messages)
    assert formatted_custom["name"] == ["Please provide a name"]
    assert formatted_custom["age"] == ["Age must be a number"]


def test_get_status_code_for_error() -> None:
    """Test the get_status_code_for_error function."""
    errors = [
        {"loc": ("name",), "msg": "field required", "type": "missing"},
    ]

    # With no custom status codes
    status = get_status_code_for_error(errors, 422, None)
    assert status == 422

    # With custom status codes
    status = get_status_code_for_error(errors, 422, {"name": 400})
    assert status == 400

    # With custom status code for a different field
    status = get_status_code_for_error(errors, 422, {"age": 400})
    assert status == 422


def test_create_error_response_django() -> None:
    """Test create_error_response function for Django responses."""
    errors = [
        {"loc": ("name",), "msg": "field required", "type": "missing"},
    ]

    response = create_error_response(errors, is_drf=False)

    assert isinstance(response, JsonResponse)
    assert response.status_code == 422

    # Test with custom status code and title
    response = create_error_response(
        errors,
        error_title="Custom Error",
        error_status_code=400,
        is_drf=False,
    )

    assert response.status_code == 400

    # Extract the response content
    data = json.loads(response.content.decode("utf-8"))
    assert data["title"] == "Custom Error"
    assert "name" in data["errors"]


@pytest.mark.skipif(not HAS_DRF, reason="DRF not installed")
def test_create_error_response_drf() -> None:
    """Test create_error_response function for DRF responses."""
    errors = [
        {"loc": ("name",), "msg": "field required", "type": "missing"},
    ]

    response = create_error_response(errors, is_drf=True)

    assert isinstance(response, Response)
    assert response.status_code == 422

    # Test with custom messages
    custom_messages = {
        "name": {"missing": "Please provide a name"},
    }

    response = create_error_response(
        errors,
        is_drf=True,
        field_error_messages=custom_messages,
    )

    assert response.data["errors"]["name"] == ["Please provide a name"]


@pytest.mark.skipif(not HAS_DRF, reason="DRF not installed")
def test_is_drf_request(rf: RequestFactory) -> None:
    """Test is_drf_request function uses isinstance check against DRF Request."""
    from rest_framework.request import Request as DRFRequest

    # Create a standard Django request
    django_request = rf.get("/test/")
    assert is_drf_request(django_request) is False

    # Create an actual DRF Request wrapping a Django request
    drf_request = DRFRequest(rf.get("/test/"))
    assert is_drf_request(drf_request) is True

    # A plain Django request with DRF-like attributes is NOT a DRF request
    fake_drf_request = rf.get("/test/")
    fake_drf_request.parser_context = {}
    assert is_drf_request(fake_drf_request) is False
