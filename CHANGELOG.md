# Changelog

## v0.2.0 - [2026-03-29]

- Dropped Django 3.2 support (minimum is now Django 4.2)
- Added async view support for both function-based and class-based views
- DRF async views (>= 3.15) are also supported
- Added Python 3.14 support

## v0.1.0 - [2026-03-29]

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
