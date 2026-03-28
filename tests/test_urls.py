from conftest import (
    CustomErrorView,
    CustomStatusView,
    MockBasicDjangoView,
    MockBasicDRFView,
    MockViewSet,
    api_function_view,
    api_method_specific_view,
    dynamic_model_view,
    function_view,
    method_specific_view,
)
from django.urls import path
from rest_framework.routers import DefaultRouter

urlpatterns = [
    # Django views
    path("test/", MockBasicDjangoView.as_view(), name="test"),
    path("test-func/", function_view, name="test-func"),
    # DRF views
    path("api/test/", MockBasicDRFView.as_view(), name="api-test"),
    path("api/test-func/", api_function_view, name="api-test-func"),
    path("custom-errors/", CustomErrorView.as_view(), name="custom-errors"),
    path("custom-status/", CustomStatusView.as_view(), name="custom-status"),
    # Method-specific validation views
    path("method-specific/", method_specific_view, name="method-specific"),
    path("api/method-specific/", api_method_specific_view, name="api-method-specific"),
    path("api/dynamic-model/", dynamic_model_view, name="dynamic-model"),
]

# for ViewSet
router = DefaultRouter()
router.register(r"api/items", MockViewSet, basename="items")

urlpatterns += router.urls
