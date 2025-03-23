from django.urls import path

from tests.conftest import MockBasicDjangoView, MockBasicDRFView, MockViewSet, function_view

urlpatterns = [
    path("test/", MockBasicDjangoView.as_view()),
    path("api/test/", MockBasicDRFView.as_view()),
    path("api/items/", MockViewSet.as_view({"get": "list"})),
    path("api/items/<int:pk>/", MockViewSet.as_view({"get": "retrieve"})),
    path("test-func/", function_view),
]
