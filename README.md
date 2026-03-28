# Are you tired of accessing Django query parameters like this?

```python
# Traditional Django view
class MyView(View):
    def get(self, request):
        name = request.GET.get("name")
        age = int(request.GET.get("age", 0))
        # ...manual validation, type conversion, error handling...
```

Now, with **django-qp**, you can harness the power of Pydantic validation:

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

# Django Pydantic Query Params

A lightweight library for Django and Django Rest Framework that enables validation of query parameters using Pydantic models, inspired by FastAPI's approach.

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

## Installation

```bash
pip install django-qp
```

Or with uv:

```bash
uv pip install django-qp
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

### 2. Use with Django class-based views

```python
from django.views import View
from django.http import JsonResponse
from django_qp import QueryParamsMixinView
from typing import cast

# Specify the model as a generic parameter for IDE autocompletion
class ProductListView(QueryParamsMixinView[ProductFilterParams], View):
    validated_params_model = ProductFilterParams

    def get(self, request):
        params = self.validated_params  # IDE will now recognize type as ProductFilterParams
        # Use validated and type-converted parameters with autocompletion support
        return JsonResponse({
            "category": params.category,
            "min_price": params.min_price
        })
```

### 3. Use with Django Rest Framework views

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from django_qp import QueryParamsMixinView

# Use generic type parameter for IDE autocompletion
class ProductAPIView(QueryParamsMixinView[ProductFilterParams], APIView):
    validated_params_model = ProductFilterParams

    def get(self, request):
        # With the generic type parameter, your IDE will provide autocompletion
        params = self.validated_params
        return Response({
            "result": "success",
            "tags": params.tags
        })
```

### 4. Use with ViewSets for action-specific validation

You can implement different validation models for different actions by overriding the `get_query_params_class` method.
When working with ViewSets that use different Pydantic models for different actions, you have a few options for proper typing.

```python
from rest_framework.viewsets import ModelViewSet
from django_qp import QueryParamsMixinViewSet
from typing import cast

# For ViewSets with multiple parameter models:
# 1. Use the most common model or base model as the generic parameter
# 2. Use explicit type casting in each action method

class ProductViewSet(QueryParamsMixinViewSet[BaseParamsModel], ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    default_validated_params_model = DefaultParams

    def get_query_params_class(self):
        """
        Override to provide different parameter models per action
        """
        if self.action == 'list':
            return ProductFilterParams
        elif self.action == 'export':
            return ExportParams
        return self.default_validated_params_model

    def list(self, request):
        # Option 1: Use explicit type casting for IDE autocompletion
        params = cast(ProductFilterParams, self.validated_params)

        # Option 2: Use type annotation (works in many IDEs)
        params: ProductFilterParams = self.validated_params

        # Now you get proper IDE autocompletion for ProductFilterParams specific fields
        filtered_products = self.queryset.filter(
            category=params.category,
            price__gte=params.min_price
        )
        # ...

    @action(detail=False, methods=['get'])
    def export(self, request):
        # Use appropriate type casting for this action
        params = cast(ExportParams, self.validated_params)

        # Now you have access to ExportParams-specific fields with autocompletion
        return Response({
            "export_format": params.format,
            "with_details": params.include_details
        })
```

The alternative for ViewSets is using the dictionary-based configuration:

```python
class ProductViewSet(QueryParamsMixinViewSet[BaseParamsModel], ModelViewSet):
    # Configure models for different actions
    validated_params_models = {
        "list": ProductFilterParams,
        "export": ExportParams,
    }
    default_validated_params_model = DefaultParams

    # In your action methods, use the type casting techniques above
    # for proper IDE autocompletion
```

### 5. Use with function-based views

#### Simple validation with a single model

```python
from django.http import JsonResponse
from django_qp import validate_query_params, EnhancedHttpRequest

@validate_query_params(ProductFilterParams)
def product_list(request: EnhancedHttpRequest[ProductFilterParams]):
    # For function-based views, use EnhancedHttpRequest for proper type hints
    params = request.validated_params  # IDE autocomplete works here!
    return JsonResponse({"category": params.category})
```

#### Method-specific validation

You can provide different validation models for different HTTP methods:

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
    "GET": GetParams,
    "POST": PostParams,
    "": DefaultParams  # Optional fallback for unmapped methods
})
def products_api(request: HttpRequest):
    # The appropriate model will be used based on the request method
    params = request.validated_params

    if request.method == "GET":
        # Type hint for IDE autocompletion
        params: GetParams
        return JsonResponse({
            "filter": params.filter,
            "sort_by": params.sort_by
        })
    elif request.method == "POST":
        # Type hint for IDE autocompletion
        params: PostParams
        return JsonResponse({
            "data": params.data,
            "priority": params.priority
        })
```

#### Dynamic model selection

For more complex scenarios, you can use a resolver function:

```python
from django.http import JsonResponse
from django_qp import validate_query_params, EnhancedHttpRequest

# Dynamic model resolver based on request properties
def get_model_for_request(request):
    # Logic to determine which model to use
    if request.GET.get("export") == "true":
        return ExportParams
    return StandardParams

@validate_query_params(get_model_for_request)
def dynamic_api(request: EnhancedHttpRequest[ExportParams | StandardParams]):
    params = request.validated_params

    # Type check to determine which model was used
    if hasattr(params, 'format'):  # ExportParams specific field
        # Handle export parameters
        return JsonResponse({"format": params.format})
    else:
        # Handle standard parameters
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
}
```

## Advanced: Direct parameter validation

```python
from django_qp import process_query_params, QueryParamsError
from typing import cast

def custom_view(request):
    try:
        # Explicit typing for IDE autocompletion
        params: ProductFilterParams = process_query_params(request, ProductFilterParams)
        # Or use cast() if you prefer
        params = cast(ProductFilterParams, process_query_params(request, ProductFilterParams))
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

## Running Tests

```bash
uv run pytest
```

## License

MIT
