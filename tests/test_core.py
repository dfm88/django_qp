import pytest
from django.test import RequestFactory
from pydantic import BaseModel, Field

from dj_pydantic_qparams.core import process_query_params
from dj_pydantic_qparams.exceptions import QueryParamsError


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
