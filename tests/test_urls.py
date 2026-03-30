"""URL configuration for django-qp tests."""

from django.urls import path

from django_qp._compat import HAS_DRF, HAS_MSGSPEC, HAS_PYDANTIC

urlpatterns = []

if HAS_PYDANTIC:
    from conftest import (
        AsyncMockBasicDjangoView,
        MockBasicDjangoView,
        async_function_view,
        async_method_specific_view,
        function_view,
        method_specific_view,
    )

    urlpatterns += [
        path("test/", MockBasicDjangoView.as_view(), name="test"),
        path("test-func/", function_view, name="test-func"),
        path("method-specific/", method_specific_view, name="method-specific"),
        path("async-test/", AsyncMockBasicDjangoView.as_view(), name="async-test"),
        path("async-test-func/", async_function_view, name="async-test-func"),
        path("async-method-specific/", async_method_specific_view, name="async-method-specific"),
    ]

if HAS_MSGSPEC:
    from conftest import MsgspecMockBasicDjangoView, msgspec_function_view

    urlpatterns += [
        path("msgspec/basic/", MsgspecMockBasicDjangoView.as_view(), name="msgspec-basic"),
        path("msgspec/function/", msgspec_function_view, name="msgspec-function"),
    ]

if HAS_PYDANTIC and HAS_DRF:
    from conftest import (
        AsyncMockBasicDRFView,
        CustomErrorView,
        CustomStatusView,
        MockBasicDRFView,
        MockViewSet,
        api_function_view,
        api_method_specific_view,
        dynamic_model_view,
    )
    from rest_framework.routers import DefaultRouter

    urlpatterns += [
        path("api/test/", MockBasicDRFView.as_view(), name="api-test"),
        path("api/test-func/", api_function_view, name="api-test-func"),
        path("custom-errors/", CustomErrorView.as_view(), name="custom-errors"),
        path("custom-status/", CustomStatusView.as_view(), name="custom-status"),
        path("api/method-specific/", api_method_specific_view, name="api-method-specific"),
        path("api/dynamic-model/", dynamic_model_view, name="dynamic-model"),
        path("api/async-test/", AsyncMockBasicDRFView.as_view(), name="api-async-test"),
    ]

    router = DefaultRouter()
    router.register(r"api/items", MockViewSet, basename="items")
    urlpatterns += router.urls
