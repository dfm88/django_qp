"""Compatibility module for optional dependencies."""

try:
    import rest_framework  # noqa: F401

    HAS_DRF = True
except ImportError:
    HAS_DRF = False
