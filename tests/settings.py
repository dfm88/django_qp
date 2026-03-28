"""Minimal Django settings for pytest-django test runner."""

from django_qp._compat import HAS_DRF

SECRET_KEY = "django-insecure-key-for-testing"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django_qp",
]

if HAS_DRF:
    INSTALLED_APPS.append("rest_framework")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

ROOT_URLCONF = "tests.test_urls"
