# Django Pydantic Query Params

A lightweight library for Django and Django Rest Framework that enables validation of query parameters using Pydantic models, inspired by FastAPI's approach.

## Features

- Validate query parameters using Pydantic models
- Type conversion and validation
- Support for Django views and DRF (APIView, ViewSet)
- Class-based mixins and function-based decorators
- Support for comma-separated list parameters

## Installation

```bash
pip install dj-pydantic-qparams
```

Or with uv:

```bash
uv pip install dj-pydantic-qparams
```

## Usage

### Define your Pydantic model

```python
from pydantic import BaseModel, Field

class ProductFilterParams(BaseModel):
    category: str | None = None
    min_price: float = Field(default=0, ge=0)
    max_price: float | None = None
    in_stock: bool = False
    tags: list[str] | None = None  # Will parse comma-separated values
```

### Use with Django class-based views

```python
from django.views import View
from django.http import JsonResponse
from dj_pydantic_qparams import QueryParamsMixin

class ProductListView(QueryParamsMixin, View):
    query_params_model = ProductFilterParams

    def get(self, request):
        params = self.query_params  # Validated Pydantic model instance

        # Use validated and type-converted parameters
        products = Product.objects.all()

        if params.category:
            products = products.filter(category=params.category)

        if params.min_price:
            products = products.filter(price__gte=params.min_price)

        # ... more filtering ...

        return JsonResponse({"products": list(products)})
```

### Use with Django Rest Framework views

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from dj_pydantic_qparams import QueryParamsMixin

class ProductAPIView(QueryParamsMixin, APIView):
    query_params_model = ProductFilterParams

    def get(self, request):
        params = self.query_params  # Validated Pydantic model instance

        # Process your validated params...

        return Response({"result": "success"})
```

### Use with ViewSets for action-specific validation

```python
from rest_framework.viewsets import ModelViewSet
from dj_pydantic_qparams import ViewSetQueryParamsMixin

class ProductViewSet(ViewSetQueryParamsMixin, ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    # Define different validation models for different actions
    query_params_models = {
        "list": ProductFilterParams,
        "export": ExportParams,
    }

    def list(self, request):
        params = self.query_params

        queryset = self.filter_queryset(self.get_queryset())
        # Apply additional filtering using params...

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def export(self, request):
        params = self.query_params  # Will use ExportParams
        # Export logic...
```

### Use with function-based views

```python
from django.http import JsonResponse
from dj_pydantic_qparams import validate_query_params

@validate_query_params(ProductFilterParams)
def product_list(request):
    params = request.query_params  # Validated Pydantic model instance

    # Use params to filter products...

    return JsonResponse({"products": products})
```

## Advanced Features

### Direct parameter validation

```python
from dj_pydantic_qparams import process_query_params

def custom_view(request):
    # Manual validation, maybe with custom error handling
    try:
        params = process_query_params(request, SomeModel)
    except QueryParamsError as e:
        # Custom error handling
        return JsonResponse({"error": e.detail}, status=400)

    # Use params...
```

## Running Tests

```bash
uv run pytest
```

## License

MIT
