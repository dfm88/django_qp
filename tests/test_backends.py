"""Tests for the backend abstraction layer."""

import pytest

from django_qp._compat import HAS_PYDANTIC
from django_qp.backends import contains_list_type, get_backend


def test_contains_list_type_direct_list() -> None:
    """Test detection of direct list type."""
    assert contains_list_type(list[str]) is True


def test_contains_list_type_none() -> None:
    """Test None annotation returns False."""
    assert contains_list_type(None) is False


def test_contains_list_type_scalar() -> None:
    """Test scalar types return False."""
    assert contains_list_type(str) is False
    assert contains_list_type(int) is False


def test_contains_list_type_union_with_list() -> None:
    """Test Union containing list returns True."""
    assert contains_list_type(list[str] | None) is True


def test_contains_list_type_union_without_list() -> None:
    """Test Union without list returns False."""
    assert contains_list_type(str | None) is False


def test_get_backend_pydantic() -> None:
    """Test auto-detection picks pydantic for BaseModel subclasses."""
    if not HAS_PYDANTIC:
        pytest.skip("pydantic not installed")

    from pydantic import BaseModel

    class MyModel(BaseModel):
        name: str

    backend = get_backend(MyModel)
    assert backend.is_model(MyModel) is True


def test_get_backend_msgspec() -> None:
    """Test auto-detection picks msgspec for Struct subclasses."""
    import msgspec

    class MyStruct(msgspec.Struct):
        name: str

    backend = get_backend(MyStruct)
    assert backend.is_model(MyStruct) is True


def test_get_backend_unknown_type() -> None:
    """Test auto-detection raises TypeError for unknown model types."""

    class NotAModel:
        name: str

    with pytest.raises(TypeError, match="No validation backend found"):
        get_backend(NotAModel)


@pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic not installed")
class TestPydanticBackend:
    """Tests for the pydantic backend."""

    def test_get_list_fields(self) -> None:
        """Test list field detection for pydantic models."""
        from pydantic import BaseModel

        from django_qp.backends.pydantic_backend import PydanticBackend

        class MyModel(BaseModel):
            name: str
            tags: list[str]
            ids: list[int] | None = None

        fields = PydanticBackend.get_list_fields(MyModel)
        assert fields == {"tags", "ids"}

    def test_validate_success(self) -> None:
        """Test successful validation."""
        from pydantic import BaseModel

        from django_qp.backends.pydantic_backend import PydanticBackend

        class MyModel(BaseModel):
            name: str
            age: int

        result = PydanticBackend.validate(MyModel, {"name": "test", "age": "25"})
        assert result.name == "test"
        assert result.age == 25

    def test_validate_failure(self) -> None:
        """Test validation failure raises PydanticValidationError."""
        from pydantic import BaseModel, ValidationError

        from django_qp.backends.pydantic_backend import PydanticBackend

        class MyModel(BaseModel):
            age: int

        with pytest.raises(ValidationError):
            PydanticBackend.validate(MyModel, {"age": "not_a_number"})

    def test_format_errors_basic(self) -> None:
        """Test basic error formatting preserves pydantic native structure."""
        from pydantic import BaseModel, Field, ValidationError

        from django_qp.backends.pydantic_backend import PydanticBackend

        class MyModel(BaseModel):
            age: int = Field(ge=0)

        try:
            MyModel(age=-1)
        except ValidationError as e:
            errors, status = PydanticBackend.format_errors(e, None, None, 422)
            assert status == 422
            assert len(errors) == 1
            assert errors[0]["field"] == "age"
            assert "msg" in errors[0]
            assert "type" in errors[0]

    def test_format_errors_custom_message(self) -> None:
        """Test custom error messages override default."""
        from pydantic import BaseModel, Field, ValidationError

        from django_qp.backends.pydantic_backend import PydanticBackend

        class MyModel(BaseModel):
            age: int = Field(ge=0)

        custom = {"age": {"greater_than_equal": "Age must be positive"}}

        try:
            MyModel(age=-1)
        except ValidationError as e:
            errors, _status = PydanticBackend.format_errors(e, custom, None, 422)
            assert errors[0]["msg"] == "Age must be positive"

    def test_format_errors_custom_status_code(self) -> None:
        """Test custom status code per field."""
        from pydantic import BaseModel, ValidationError

        from django_qp.backends.pydantic_backend import PydanticBackend

        class MyModel(BaseModel):
            name: str

        try:
            MyModel()
        except ValidationError as e:
            _errors, status = PydanticBackend.format_errors(e, None, {"name": 400}, 422)
            assert status == 400

    def test_format_errors_wildcard_message(self) -> None:
        """Test __all__ wildcard for field error messages."""
        from pydantic import BaseModel, ValidationError

        from django_qp.backends.pydantic_backend import PydanticBackend

        class MyModel(BaseModel):
            name: str

        custom = {"name": {"__all__": "Name is invalid"}}

        try:
            MyModel()
        except ValidationError as e:
            errors, _status = PydanticBackend.format_errors(e, custom, None, 422)
            assert errors[0]["msg"] == "Name is invalid"


class TestMsgspecBackend:
    """Tests for the msgspec backend."""

    def test_is_model(self) -> None:
        """Test model detection for msgspec Struct."""
        import msgspec

        from django_qp.backends.msgspec_backend import MsgspecBackend

        class MyStruct(msgspec.Struct):
            name: str

        assert MsgspecBackend.is_model(MyStruct) is True
        assert MsgspecBackend.is_model(str) is False

    def test_get_list_fields(self) -> None:
        """Test list field detection for msgspec Struct."""
        import msgspec

        from django_qp.backends.msgspec_backend import MsgspecBackend

        class MyStruct(msgspec.Struct):
            name: str
            tags: list[str]
            ids: list[int] | None = None

        fields = MsgspecBackend.get_list_fields(MyStruct)
        assert fields == {"tags", "ids"}

    def test_validate_success(self) -> None:
        """Test successful validation via msgspec.convert."""
        import msgspec

        from django_qp.backends.msgspec_backend import MsgspecBackend

        class MyStruct(msgspec.Struct):
            name: str
            age: int

        result = MsgspecBackend.validate(MyStruct, {"name": "test", "age": 25})
        assert result.name == "test"
        assert result.age == 25

    def test_validate_failure(self) -> None:
        """Test validation failure raises msgspec.ValidationError."""
        import msgspec

        from django_qp.backends.msgspec_backend import MsgspecBackend

        class MyStruct(msgspec.Struct):
            age: int

        with pytest.raises(msgspec.ValidationError):
            MsgspecBackend.validate(MyStruct, {"age": "not_a_number"})

    def test_format_errors_type_error(self) -> None:
        """Test error formatting for type mismatch errors."""
        import msgspec

        from django_qp.backends.msgspec_backend import MsgspecBackend

        class MyStruct(msgspec.Struct):
            age: int

        try:
            msgspec.convert({"age": "not_a_number"}, MyStruct)
        except msgspec.ValidationError as e:
            errors, status = MsgspecBackend.format_errors(e, None, None, 422)
            assert status == 422
            assert len(errors) >= 1
            assert "msg" in errors[0]
            assert "field" in errors[0]

    def test_format_errors_missing_field(self) -> None:
        """Test error formatting for missing required fields."""
        import msgspec

        from django_qp.backends.msgspec_backend import MsgspecBackend

        class MyStruct(msgspec.Struct):
            name: str

        try:
            msgspec.convert({}, MyStruct)
        except msgspec.ValidationError as e:
            errors, _status = MsgspecBackend.format_errors(e, None, None, 422)
            assert len(errors) >= 1
            assert errors[0]["field"] == "name"

    def test_format_errors_custom_message(self) -> None:
        """Test custom error messages override default for msgspec."""
        import msgspec

        from django_qp.backends.msgspec_backend import MsgspecBackend

        class MyStruct(msgspec.Struct):
            name: str

        custom = {"name": {"__all__": "Name is required"}}

        try:
            msgspec.convert({}, MyStruct)
        except msgspec.ValidationError as e:
            errors, _status = MsgspecBackend.format_errors(e, custom, None, 422)
            assert errors[0]["msg"] == "Name is required"

    def test_format_errors_custom_status_code(self) -> None:
        """Test custom status code per field for msgspec."""
        import msgspec

        from django_qp.backends.msgspec_backend import MsgspecBackend

        class MyStruct(msgspec.Struct):
            name: str

        try:
            msgspec.convert({}, MyStruct)
        except msgspec.ValidationError as e:
            _errors, status = MsgspecBackend.format_errors(e, None, {"name": 400}, 422)
            assert status == 400

    def test_validate_string_to_int_coercion(self) -> None:
        """Test that msgspec.convert handles string-to-int coercion for query params."""
        import msgspec

        from django_qp.backends.msgspec_backend import MsgspecBackend

        class MyStruct(msgspec.Struct):
            age: int

        result = MsgspecBackend.validate(MyStruct, {"age": "25"})
        assert result.age == 25
