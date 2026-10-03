import pytest
from rest_framework.test import APIClient

from tests.app.views import Echo


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def echo():
    return Echo.objects.create(payload="seed")
