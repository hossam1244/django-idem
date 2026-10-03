from rest_framework import generics

from django_idem.mixins import IdempotencyMixin

from .models import Echo
from .serializers import EchoSerializer


class EchoView(IdempotencyMixin, generics.CreateAPIView):
    """The idempotent endpoint under test."""

    queryset = Echo.objects.all()
    serializer_class = EchoSerializer


class OptionalEchoView(IdempotencyMixin, generics.CreateAPIView):
    """Header optional — passthrough when absent."""

    queryset = Echo.objects.all()
    serializer_class = EchoSerializer
    idempotency_required = False
