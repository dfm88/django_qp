"""Tests for core validation functions."""

import json

import pytest
from django.http import JsonResponse
from django.test import RequestFactory

from django_qp._compat import HAS_DRF, HAS_MSGSPEC, HAS_PYDANTIC
from django_qp.core import (
    create_error_response,
    is_drf_request,
    process_query_params,
)
from django_qp.exceptions import QueryParamsError

if HAS_DRF:
    from rest_framework.response import Response

pydantic_required = pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic not installed")


@pydantic_required
def test_list_conversion(rf: RequestFactory) -> None:
    """Test comma-separated values are split into lists."""
    from pydantic import BaseModel

    class ListParams(BaseModel):
        tags: list[str]

    request = rf.get("/test/", {"tags": "a,b,c"})
    params = process_query_params(request, ListParams)
    assert params.tags == ["a", "b", "c"]


@pydantic_required
def test_type_conversion(rf: RequestFactory) -> None:
    """Test query string values are coerced to the declared field types."""
    from pydantic import BaseModel

    class TypeParams(BaseModel):
        num: int
        flag: bool

    request = rf.get("/test/", {"num": "42", "flag": "true"})
    params = process_query_params(request, TypeParams)
    assert params.num == 42
    assert params.flag is True


@pydantic_required
def test_validation_error(rf: RequestFactory) -> None:
    """Test that constraint violations raise QueryParamsError."""
    from pydantic import BaseModel, Field

    class ValidParams(BaseModel):
        age: int = Field(ge=0)

    request = rf.get("/test/", {"age": "-1"})
    with pytest.raises(QueryParamsError):
        process_query_params(request, ValidParams)


@pydantic_required
def test_format_errors_via_pydantic_backend() -> None:
    """Test PydanticBackend.format_errors formats errors correctly."""
    from pydantic import BaseModel
    from pydantic import ValidationError as PydanticValidationError

    from django_qp.backends.pydantic_backend import PydanticBackend

    class TestModel(BaseModel):
        name: str
        age: int

    # Trigger a real pydantic validation error
    try:
        TestModel()  # type: ignore[call-arg]
    except PydanticValidationError as exc:
        # Format errors with no custom messages
        formatted, status_code = PydanticBackend.format_errors(exc, None, None, 422)
        assert status_code == 422
        assert len(formatted) >= 1
        field_names = [e["field"] for e in formatted]
        assert "name" in field_names
        assert "age" in field_names

        # Format errors with custom messages
        custom_messages = {
            "name": {"missing": "Please provide a name"},
            "age": {"missing": "Age is required"},
        }
        formatted_custom, _ = PydanticBackend.format_errors(exc, custom_messages, None, 422)
        for error in formatted_custom:
            if error["field"] == "name":
                assert error["msg"] == "Please provide a name"
            elif error["field"] == "age":
                assert error["msg"] == "Age is required"


@pydantic_required
def test_format_errors_status_codes_via_pydantic_backend() -> None:
    """Test PydanticBackend.format_errors with custom status codes."""
    from pydantic import BaseModel
    from pydantic import ValidationError as PydanticValidationError

    from django_qp.backends.pydantic_backend import PydanticBackend

    class TestModel(BaseModel):
        name: str

    try:
        TestModel()  # type: ignore[call-arg]
    except PydanticValidationError as exc:
        # With no custom status codes
        _, status = PydanticBackend.format_errors(exc, None, None, 422)
        assert status == 422

        # With custom status codes
        _, status = PydanticBackend.format_errors(exc, None, {"name": 400}, 422)
        assert status == 400

        # With custom status code for a different field
        _, status = PydanticBackend.format_errors(exc, None, {"age": 400}, 422)
        assert status == 422


@pydantic_required
def test_create_error_response_django() -> None:
    """Test create_error_response function for Django responses."""
    from pydantic import BaseModel
    from pydantic import ValidationError as PydanticValidationError

    class TestModel(BaseModel):
        name: str

    try:
        TestModel()  # type: ignore[call-arg]
    except PydanticValidationError as pydantic_exc:
        exc = QueryParamsError(pydantic_exc)

        response = create_error_response(exc, is_drf=False, model=TestModel)

        assert isinstance(response, JsonResponse)
        assert response.status_code == 422

        # Test with custom status code and title
        response = create_error_response(
            exc,
            error_title="Custom Error",
            error_status_code=400,
            is_drf=False,
            model=TestModel,
        )

        assert response.status_code == 400

        # Extract the response content
        data = json.loads(response.content.decode("utf-8"))
        assert data["title"] == "Custom Error"
        # Errors are now a list of dicts with "field" key
        field_names = [e["field"] for e in data["errors"]]
        assert "name" in field_names


@pytest.mark.skipif(not HAS_PYDANTIC or not HAS_DRF, reason="pydantic and DRF required")
def test_create_error_response_drf() -> None:
    """Test create_error_response function for DRF responses."""
    from pydantic import BaseModel
    from pydantic import ValidationError as PydanticValidationError

    class TestModel(BaseModel):
        name: str

    try:
        TestModel()  # type: ignore[call-arg]
    except PydanticValidationError as pydantic_exc:
        exc = QueryParamsError(pydantic_exc)

        response = create_error_response(exc, is_drf=True, model=TestModel)

        assert isinstance(response, Response)
        assert response.status_code == 422

        # Test with custom messages
        custom_messages = {
            "name": {"missing": "Please provide a name"},
        }

        response = create_error_response(
            exc,
            is_drf=True,
            model=TestModel,
            field_error_messages=custom_messages,
        )

        # Errors are now a list of dicts
        errors = response.data["errors"]
        name_errors = [e for e in errors if e["field"] == "name"]
        assert name_errors[0]["msg"] == "Please provide a name"


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


@pydantic_required
def test_multi_value_query_params(rf: RequestFactory) -> None:
    """Test repeated query keys are collected into a list."""
    from pydantic import BaseModel

    class ListParams(BaseModel):
        tags: list[str]

    request = rf.get("/test/", {"tags": ["a", "b"]})
    params = process_query_params(request, ListParams)
    assert params.tags == ["a", "b"]


@pydantic_required
def test_multi_value_with_comma_split(rf: RequestFactory) -> None:
    """Test repeated keys with commas are split and flattened."""
    from pydantic import BaseModel

    class ListParams(BaseModel):
        tags: list[str]

    request = rf.get("/test/?tags=a,b&tags=c,d")
    params = process_query_params(request, ListParams)
    assert params.tags == ["a", "b", "c", "d"]


@pydantic_required
def test_single_value_list_field_unchanged(rf: RequestFactory) -> None:
    """Test comma-separated single value still works (regression guard)."""
    from pydantic import BaseModel

    class ListParams(BaseModel):
        tags: list[str]

    request = rf.get("/test/", {"tags": "a,b,c"})
    params = process_query_params(request, ListParams)
    assert params.tags == ["a", "b", "c"]


@pydantic_required
def test_scalar_field_multi_value_takes_last(rf: RequestFactory) -> None:
    """Test scalar fields with repeated keys take the last value (QueryDict default)."""
    from pydantic import BaseModel

    class ScalarParams(BaseModel):
        name: str

    request = rf.get("/test/?name=a&name=b")
    params = process_query_params(request, ScalarParams)
    assert params.name == "b"


def test_extract_request_data_returns_querydict(rf: RequestFactory) -> None:
    """Test _extract_request_data returns a QueryDict, not a plain dict."""
    from django.http import QueryDict

    from django_qp.core import _extract_request_data

    request = rf.get("/test/", {"key": "value"})
    data = _extract_request_data(request)
    assert isinstance(data, QueryDict)


def test_compat_flags_exist() -> None:
    """Test that backend availability flags are importable."""
    from django_qp._compat import HAS_DRF, HAS_MSGSPEC, HAS_PYDANTIC

    # msgspec is a core dep, always True
    assert HAS_MSGSPEC is True
    # pydantic may or may not be installed depending on test environment
    assert isinstance(HAS_PYDANTIC, bool)
    assert isinstance(HAS_DRF, bool)


@pydantic_required
def test_plain_dict_fallback(rf: RequestFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test list processing works when _extract_request_data returns a plain dict."""
    from pydantic import BaseModel

    import django_qp.core

    class ListParams(BaseModel):
        tags: list[str]

    # Monkeypatch to return a plain dict (simulates a custom override)
    monkeypatch.setattr(django_qp.core, "_extract_request_data", lambda r: {"tags": "x,y,z"})

    request = rf.get("/test/")
    params = process_query_params(request, ListParams)
    assert params.tags == ["x", "y", "z"]


# --- Msgspec tests ---


@pytest.mark.skipif(not HAS_MSGSPEC, reason="msgspec not installed")
def test_process_query_params_msgspec(rf: RequestFactory) -> None:
    """Test basic msgspec Struct validation."""
    import msgspec

    class MsgspecParams(msgspec.Struct):
        name: str
        age: int

    request = rf.get("/test/", {"name": "alice", "age": "30"})
    params = process_query_params(request, MsgspecParams)
    assert params.name == "alice"
    assert params.age == 30


@pytest.mark.skipif(not HAS_MSGSPEC, reason="msgspec not installed")
def test_process_query_params_msgspec_list(rf: RequestFactory) -> None:
    """Test comma-splitting works for msgspec Struct list fields."""
    import msgspec

    class MsgspecListParams(msgspec.Struct):
        tags: list[str]

    request = rf.get("/test/", {"tags": "a,b,c"})
    params = process_query_params(request, MsgspecListParams)
    assert params.tags == ["a", "b", "c"]


@pytest.mark.skipif(not HAS_MSGSPEC, reason="msgspec not installed")
def test_process_query_params_msgspec_validation_error(rf: RequestFactory) -> None:
    """Test that msgspec validation errors raise QueryParamsError."""
    import msgspec

    class MsgspecRequiredParams(msgspec.Struct):
        name: str

    request = rf.get("/test/")
    with pytest.raises(QueryParamsError):
        process_query_params(request, MsgspecRequiredParams)


def test_process_query_params_unknown_model(rf: RequestFactory) -> None:
    """Test that an unsupported model type raises TypeError."""

    class NotAModel:
        pass

    request = rf.get("/test/")
    with pytest.raises(TypeError, match="No validation backend found"):
        process_query_params(request, NotAModel)
