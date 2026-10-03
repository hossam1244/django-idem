from rest_framework import serializers

from tests.app.models import Echo


class EchoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Echo
        fields = ("id", "payload")
