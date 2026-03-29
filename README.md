# Django QP

[![CI](https://github.com/dfm88/django_qp/actions/workflows/ci.yml/badge.svg)](https://github.com/dfm88/django_qp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/django-qp)](https://pypi.org/project/django-qp/)
[![Python](https://img.shields.io/pypi/pyversions/django-qp)](https://pypi.org/project/django-qp/)
[![Django](https://img.shields.io/badge/django-4.2%20%7C%205.0%20%7C%205.1%20%7C%205.2-blue)](https://pypi.org/project/django-qp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/dfm88/django_qp/blob/main/LICENSE)

## Are you tired of accessing Django query parameters like this?

```python
# Traditional Django view
class MyView(View):
    def get(self, request):
        name = request.GET.get("name")
        age = int(request.GET.get("age", 0))
        # ...manual validation, type conversion, error handling...
```

Or maybe you're using DRF and validating query parameters with a serializer defined as an inner class of your view, only to access the values through a dict with no IDE autocompletion?

```python
# DRF approach — no IDE autocompletion, dict-based access
class MyView(APIView):
    class QuerySerializer(serializers.Serializer):
        name = serializers.CharField()
        age = serializers.IntegerField(min_value=0)

    def get(self, request):
        serializer = self.QuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"]  # No autocompletion, always a dict lookup
        age = serializer.validated_data["age"]     # Easy to typo the key, no type safety
```

With **django-qp**, you get the power of Pydantic validation with full IDE autocompletion:

```python
from pydantic import BaseModel, Field
from django_qp import QueryParamsMixinView

class UserParams(BaseModel):
    name: str
    age: int = Field(ge=0)

# Use generic type parameter for IDE autocompletion
class MyView(QueryParamsMixinView[UserParams], View):
    validated_params_model = UserParams

    def get(self, request):
        params = self.validated_params  # Validated Pydantic model with IDE autocompletion!
        return JsonResponse({"name": params.name, "age": params.age})
```

---

A lightweight library for Django and Django Rest Framework that enables validation of query parameters using Pydantic models, inspired by FastAPI's approach.

## Requirements

- Python >= 3.10, < 3.15
- Django >= 4.2, < 7.0
- Pydantic >= 2.0
- Django REST Framework >= 3.15.2 (**optional**)

## Why use this library?

- **No more manual parsing or type conversion**: Query parameters are validated and converted to Python types automatically.
- **Clear, maintainable code**: Use Pydantic models to define your expected query parameters.
- **Consistent error handling**: Get structured error responses for invalid input.
- **Works with Django, DRF, class-based and function-based views**.
- **Supports action-specific validation for ViewSets**.
- **Supports method-specific validation for function-based views**.
- **Customizable error messages and status codes**.
- **Type hints for IDE autocompletion**: Get full IntelliSense/autocomplete in your IDE.

## Features

- Validate query parameters using Pydantic models
- Type conversion and validation
- Support for Django views and DRF (APIView, ViewSet)
- Class-based mixins and function-based decorators
- Support for comma-separated list parameters
- Action-specific models for ViewSets
- Method-specific models for function-based views
- Custom error messages and status codes
- Generic type annotations for IDE autocompletion
- Enhanced type hints for request objects in function-based views
- Transparent async view support (Django 4.2+, DRF 3.15+)

## Installation

```bash
pip install django-qp
```

With DRF support:

```bash
pip install django-qp[drf]
```

Or with uv:

```bash
uv pip install django-qp        # Django only
uv pip install django-qp[drf]   # with DRF support
```

## Usage

### 1. Define your Pydantic model

```python
from pydantic import BaseModel, Field

class ProductFilterParams(BaseModel):
    category: str | None = None
    min_price: float = Field(default=0, ge=0)
    max_price: float | None = None
    in_stock: bool = False
    tags: list[str] | None = None  # Will parse comma-separated values
```

> **List parameters:** Fields typed as `list[...]` support two patterns that can be combined:
> - Comma-separated: `?tags=python,django` → `["python", "django"]`
> - Repeated keys: `?tags=python&tags=django` → `["python", "django"]`
> - Combined: `?tags=python,django&tags=fastapi` → `["python", "django", "fastapi"]`

### 2. Use with Django class-based views

```python
from django.views import View
from django.http import JsonResponse
from django_qp import QueryParamsMixinView

# Specify the model as a generic parameter for IDE autocompletion
class ProductListView(QueryParamsMixinView[ProductFilterParams], View):
    validated_params_model = ProductFilterParams

    def get(self, request):
        params = self.validated_params  # IDE will now recognize type as ProductFilterParams
        return JsonResponse({
            "category": params.category,
            "min_price": params.min_price
        })
```

> **Important:** `QueryParamsMixinView` must appear **before** the view class in the inheritance list.
> A `TypeError` is raised at class definition time if the order is wrong.
> ```python
> # Correct
> class MyView(QueryParamsMixinView[MyParams], View): ...
>
> # Wrong — raises TypeError
> class MyView(View, QueryParamsMixinView[MyParams]): ...
> ```

### 3. Use with Django Rest Framework views

Requires `pip install django-qp[drf]`.

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from django_qp import QueryParamsMixinView

class ProductAPIView(QueryParamsMixinView[ProductFilterParams], APIView):
    validated_params_model = ProductFilterParams

    def get(self, request):
        params = self.validated_params
        return Response({
            "result": "success",
            "tags": params.tags
        })
```

### 4. Use with ViewSets for action-specific validation

Override `get_query_params_class` to return different models per action (similar to DRF's `get_serializer_class`):

```python
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django_qp import QueryParamsMixinView
from typing import cast

class ProductViewSet(QueryParamsMixinView[ProductFilterParams], ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_query_params_class(self, action):
        if action == "list":
            return ProductFilterParams
        elif action == "export":
            return ExportParams
        return None  # No validation for other actions

    def list(self, request):
        params = cast(ProductFilterParams, self.validated_params)
        filtered_products = self.queryset.filter(
            category=params.category,
            price__gte=params.min_price
        )
        # ...

    @action(detail=False, methods=["get"])
    def export(self, request):
        params = cast(ExportParams, self.validated_params)
        return Response({
            "export_format": params.format,
            "with_details": params.include_details
        })
```

### 5. Use with function-based views

#### Simple validation with a single model

```python
from django.http import JsonResponse
from django_qp import validate_query_params, EnhancedHttpRequest

@validate_query_params(ProductFilterParams)
def product_list(request: EnhancedHttpRequest[ProductFilterParams]):
    params = request.validated_params  # IDE autocomplete works here!
    return JsonResponse({"category": params.category})
```

#### Method-specific validation

Provide different validation models for different HTTP methods using a dict with **lowercase** method names:

```python
from django.http import JsonResponse, HttpRequest
from django_qp import validate_query_params

class GetParams(BaseModel):
    filter: str
    sort_by: str | None = None

class PostParams(BaseModel):
    data: str
    priority: int = Field(ge=1, le=5)

# Dictionary mapping HTTP methods to models
@validate_query_params({
    "get": GetParams,
    "post": PostParams,
    "": DefaultParams,  # Optional fallback for unmapped methods
})
def products_api(request: HttpRequest):
    params = request.validated_params

    if request.method == "GET":
        params: GetParams
        return JsonResponse({
            "filter": params.filter,
            "sort_by": params.sort_by
        })
    elif request.method == "POST":
        params: PostParams
        return JsonResponse({
            "data": params.data,
            "priority": params.priority
        })
```

#### Dynamic model selection

For more complex scenarios, use a resolver function:

```python
from django.http import JsonResponse
from django_qp import validate_query_params, EnhancedHttpRequest

def get_model_for_request(request):
    if request.GET.get("export") == "true":
        return ExportParams
    return StandardParams

@validate_query_params(get_model_for_request)
def dynamic_api(request: EnhancedHttpRequest[ExportParams | StandardParams]):
    params = request.validated_params

    if hasattr(params, "format"):
        return JsonResponse({"format": params.format})
    else:
        return JsonResponse({"query": params.query})
```

## Customizing Error Messages and Status Codes

You can provide custom error messages and status codes for specific fields and error types:

```python
class CustomView(QueryParamsMixinView[ProductFilterParams], APIView):
    validated_params_model = ProductFilterParams
    field_error_messages = {
        "min_price": {
            "greater_than_equal": "Minimum price must be non-negative.",
            "__all__": "Invalid price provided."
        },
        "category": {
            "type_error": "Category must be a string."
        }
    }
    field_error_status_codes = {
        "min_price": 400,
        "category": 404,
    }
```

## Advanced: Direct parameter validation

```python
from django_qp import process_query_params, QueryParamsError

def custom_view(request):
    try:
        params = cast(
            ProductFilterParams,
            process_query_params(request, ProductFilterParams)
        )
    except QueryParamsError as e:
        return JsonResponse({"error": e.detail}, status=400)
    # ...
```

## Type Hints for Function-Based Views

For better IDE support and type checking in function-based views, use the `EnhancedHttpRequest` generic type:

```python
from django_qp import validate_query_params, EnhancedHttpRequest
from pydantic import BaseModel

class UserParams(BaseModel):
    name: str
    age: int

@validate_query_params(UserParams)
def my_view(request: EnhancedHttpRequest[UserParams]):
    # Your IDE now knows that:
    params = request.validated_params  # This is a UserParams instance
    name = params.name  # This is a string
    age = params.age    # This is an int

    return HttpResponse(f"Hello {name}, you are {age} years old")
```

### Handling Dynamic Models with Type Casting

When working with dynamic models (such as when using a resolver function), you can use Python's `cast()` function for better type safety:

```python
from typing import cast
from django_qp import validate_query_params, EnhancedHttpRequest

# Define a resolver function that returns different models
def get_model_for_request(request):
    if request.GET.get("use_detailed") == "true":
        return DetailedParams
    return SimpleParams

@validate_query_params(get_model_for_request)
def dynamic_view(request: EnhancedHttpRequest[SimpleParams | DetailedParams]):
    params = request.validated_params

    # Option 1: Type narrowing with isinstance
    if isinstance(params, DetailedParams):
        # IDE knows this is DetailedParams
        return JsonResponse({"details": params.details})

    # Option 2: Type narrowing with attribute check + cast
    if hasattr(params, "details"):
        # Use cast to tell the type checker what type this is
        detailed_params = cast(DetailedParams, params)
        return JsonResponse({"details": detailed_params.details})

    # Now IDE knows this must be SimpleParams
    return JsonResponse({"name": params.name})
```

This approach gives you the full benefits of type checking while still supporting dynamic model selection.

## Async Views

Async views are supported out of the box. The library auto-detects whether your view is async and handles it transparently — no API changes, no special imports. Both the mixin and decorator work with async views:

```python
# Async CBV — works exactly like sync
class MyView(QueryParamsMixinView[MyParams], View):
    validated_params_model = MyParams

    async def get(self, request):
        params = self.validated_params
        return JsonResponse({"name": params.name})

# Async FBV — works exactly like sync
@validate_query_params(MyParams)
async def my_view(request: EnhancedHttpRequest[MyParams]):
    params = request.validated_params
    return JsonResponse({"name": params.name})
```

Requires Django >= 4.2. DRF async views (>= 3.15) are also supported.

## Changelog

### v0.2.0

- Dropped Django 3.2 support (minimum is now Django 4.2)
- Added async view support for both function-based and class-based views
- DRF async views (>= 3.15) are also supported
- Added Python 3.14 support

### v0.1.0

- Initial release
- Django 3.2+ support (sync views only)
- Pydantic-based query parameter validation
- Class-based view mixin (`QueryParamsMixinView[T]`)
- Function-based view decorator (`@validate_query_params`)
- Direct validation function (`process_query_params`)
- Support for comma-separated list parameters
- Action-specific models for ViewSets
- Method-specific models for function-based views
- Custom error messages and status codes
- Generic type annotations for IDE autocompletion
- DRF as optional dependency (`pip install django-qp[drf]`)

## Running Tests

```bash
uv run pytest
```

## License

MIT
