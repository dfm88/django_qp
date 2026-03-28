# Contributing to django-qp

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setup

```bash
# Clone the repo
git clone https://github.com/your-username/django-qp.git
cd django-qp

# Install dev dependencies (includes DRF, pytest, ruff, mypy, tox, pre-commit)
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install
```

## Running tests

```bash
# Full test suite
uv run pytest

# Single test
uv run pytest tests/test_core.py::test_list_conversion

# With coverage
uv run pytest --cov
```

## Multi-version testing with tox

The project uses tox with tox-uv to test across Django, Python, and DRF version combinations:

```bash
# List all environments
uv run tox list

# Run a specific environment
uv run tox run -e py312-django52-drf

# Run a no-DRF environment (validates optional dependency story)
uv run tox run -e py312-django51-nodrf
```

Environments cover:

| Django | Python | DRF |
|--------|--------|-----|
| 3.2 | 3.10 | with/without |
| 4.2 | 3.10, 3.12 | with/without |
| 5.0 | 3.12 | with |
| 5.1 | 3.12, 3.13 | with/without |
| 5.2 | 3.13, 3.14 | with/without |

## Linting and formatting

```bash
# Lint
uv run ruff check src/ tests/

# Auto-fix lint issues
uv run ruff check --fix src/ tests/

# Format
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

Pre-commit hooks run ruff (lint + format) and mypy automatically on each commit.

## Project structure

```
src/django_qp/
├── _compat.py            # HAS_DRF flag for optional DRF detection
├── core.py               # Validation engine (extract, split, validate, error formatting)
├── decorators.py         # @validate_query_params for function-based views
├── mixins.py             # QueryParamsMixinView for class-based views
├── exceptions.py         # QueryParamsError
├── internal_typing.py    # Type definitions (EnhancedHttpRequest, ErrorList, etc.)
└── __init__.py           # Public API exports

tests/
├── conftest.py           # All test models, views, and fixtures
├── test_core.py          # Unit tests for core validation functions
├── test_views.py         # Integration tests for all view patterns
├── test_urls.py          # URL routing for test views
└── settings.py           # Minimal Django settings for tests
```

## DRF is optional

`djangorestframework` is an optional dependency. The `_compat.py` module exports a `HAS_DRF` flag that guards all DRF imports at runtime.

When writing code:
- Never import DRF at module level in `src/` files (use lazy imports inside functions or `TYPE_CHECKING` blocks)
- Guard DRF-dependent test code with `HAS_DRF` checks or `pytest.mark.skipif`

## Code standards

- **Ruff**: runs on pre-commit
- **Type annotations**: required on all public functions and classes
- **Docstrings**: required on all public functions and classes
