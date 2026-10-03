from django.urls import path

from .views import EchoView, OptionalEchoView

urlpatterns = [
    path("echo/", EchoView.as_view(), name="echo"),
    path("optional-echo/", OptionalEchoView.as_view(), name="optional-echo"),
]
