import sys
from pathlib import Path
from typing import ClassVar

from django.http import HttpRequest, HttpResponse
from django.views import View
from pydantic import BaseModel, Field
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from dj_pydantic_qparams.decorators import validate_query_params
from dj_pydantic_qparams.mixins import QueryParamsMixin, ViewSetQueryParamsMixin

# Add the project root directory to the Python path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))


# Test Pydantic models
class MockParams(BaseModel):
    """
    Mock Pydantic model for testing.
    """

    name: str
    age: int = Field(ge=0)
    tags: list[str] | None = None


class MockViewSetParams(BaseModel):
    """
    Mock Pydantic model for testing.
    """

    sort: str
    page: int = Field(ge=1)


# Test Views
class MockBasicDjangoView(QueryParamsMixin, View):
    query_params_model = MockParams

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Mock implementation of a Django view get method.
        """
        params = self.query_params
        return HttpResponse(f"name={params.name}, age={params.age}")


class MockBasicDRFView(QueryParamsMixin, APIView):
    query_params_model = MockParams

    def get(self, request: HttpRequest, *args, **kwargs) -> Response:
        """
        Mock implementation of a DRF view get method.
        """
        params = self.query_params
        return Response(
            {
                "name": params.name,
                "age": params.age,
                "tags": params.tags,
            },
        )


class MockViewSet(ViewSetQueryParamsMixin, ViewSet):
    query_params_models: ClassVar[dict[str, type[BaseModel]]] = {
        "list": MockViewSetParams,
        "retrieve": MockParams,
    }

    def list(self, request: HttpRequest) -> Response:
        """
        Mock implementation of a DRF view list method.
        """
        params = self.query_params
        return Response(
            {
                "sort": params.sort,
                "page": params.page,
            },
        )

    def retrieve(self, request: HttpRequest, pk: int | str | None = None) -> Response:
        """
        Mock implementation of a DRF view retrieve method.
        """
        params = self.query_params
        return Response(
            {
                "name": params.name,
                "age": params.age,
            },
        )


@validate_query_params(MockParams)
def function_view(request: HttpRequest) -> HttpResponse:
    """ "
    Mock implementation of a function-based view."
    """
    params = request.query_params
    return HttpResponse(f"name={params.name}, age={params.age}")
