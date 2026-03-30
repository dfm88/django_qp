"""Compatibility module for optional dependencies."""

try:
    import msgspec  # type: ignore[import]  # noqa: F401

    HAS_MSGSPEC = True
except ImportError:
    HAS_MSGSPEC = False

try:
    import pydantic  # noqa: F401

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

try:
    import rest_framework  # noqa: F401

    HAS_DRF = True
except ImportError:
    HAS_DRF = False
