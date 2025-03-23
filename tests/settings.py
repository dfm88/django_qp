# Minimal settings required for Django and pytest-django
SECRET_KEY = "django-insecure-key-for-testing"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    # Your app
    "dj_pydantic_qparams",
]

# Required database configuration
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# URL configuration
ROOT_URLCONF = "tests.test_urls"
