"""The idempotency contract, tested against a real DRF create view."""

import pytest
from django.test import override_settings

from tests.app.models import Echo

pytestmark = pytest.mark.django_db

ECHO_URL = "/api/echo/"
OPTIONAL_URL = "/api/optional-echo/"


def payload(text="hello"):
    return {"payload": text}


class TestReplay:
    def test_retry_replays_the_stored_response_without_side_effects(self, api):
        first = api.post(ECHO_URL, payload(), format="json", HTTP_IDEMPOTENCY_KEY="k1")
        retry = api.post(ECHO_URL, payload(), format="json", HTTP_IDEMPOTENCY_KEY="k1")

        assert first.status_code == 201
        assert retry.status_code == 201
        assert retry.json()["id"] == first.json()["id"]
        assert retry.headers["Idempotency-Replayed"] == "true"
        assert first.headers.get("Idempotency-Replayed") is None
        # The side effect ran exactly once.
        assert Echo.objects.count() == 1

    def test_validation_errors_are_cached_too(self, api):
        too_long = {"payload": "x" * 500}
        first = api.post(ECHO_URL, too_long, format="json", HTTP_IDEMPOTENCY_KEY="e1")
        retry = api.post(ECHO_URL, too_long, format="json", HTTP_IDEMPOTENCY_KEY="e1")

        assert first.status_code == 400
        assert retry.status_code == 400
        assert retry.headers["Idempotency-Replayed"] == "true"


class TestKeyReuse:
    def test_same_key_different_body_is_rejected(self, api):
        api.post(ECHO_URL, payload("one"), format="json", HTTP_IDEMPOTENCY_KEY="c1")
        response = api.post(ECHO_URL, payload("two"), format="json", HTTP_IDEMPOTENCY_KEY="c1")

        assert response.status_code == 409


class TestRequired:
    def test_missing_key_is_rejected_by_default(self, api):
        response = api.post(ECHO_URL, payload(), format="json")
        assert response.status_code == 400

    @override_settings(DJANGO_IDEM={"REQUIRED": False})
    def test_globally_optional_passthrough(self, api):
        response = api.post(ECHO_URL, payload(), format="json")
        assert response.status_code == 201

    def test_per_view_optional_passthrough(self, api):
        response = api.post(OPTIONAL_URL, payload(), format="json")
        assert response.status_code == 201

    def test_per_view_optional_still_replays_with_key(self, api):
        first = api.post(OPTIONAL_URL, payload(), format="json", HTTP_IDEMPOTENCY_KEY="o1")
        retry = api.post(OPTIONAL_URL, payload(), format="json", HTTP_IDEMPOTENCY_KEY="o1")
        assert retry.json()["id"] == first.json()["id"]
        assert Echo.objects.count() == 1


class TestScope:
    @override_settings(
        DJANGO_IDEM={
            "SCOPE_CALLABLE": lambda request: f"tenant:{request.headers.get('X-Tenant', 'none')}"
        }
    )
    def test_custom_scope_isolates_keys(self, api):
        first = api.post(
            ECHO_URL,
            payload(),
            format="json",
            HTTP_IDEMPOTENCY_KEY="shared",
            HTTP_X_TENANT="acme",
        )
        second = api.post(
            ECHO_URL,
            payload(),
            format="json",
            HTTP_IDEMPOTENCY_KEY="shared",
            HTTP_X_TENANT="globex",
        )

        assert first.status_code == 201
        assert second.status_code == 201
        assert second.json()["id"] != first.json()["id"]


class TestStorage:
    def test_record_stores_serializable_body(self, api):
        from django_idem.models import IdempotencyRecord

        api.post(ECHO_URL, payload(), format="json", HTTP_IDEMPOTENCY_KEY="s1")
        record = IdempotencyRecord.objects.get(key="s1")
        assert record.response_status == 201
        assert record.response_body["payload"] == "hello"
        assert len(record.request_hash) == 64
        assert record.scope == "anon"
