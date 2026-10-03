"""The mixin that makes a DRF create-view idempotent.

Protocol (Stripe-style):

* Client sends ``Idempotency-Key: <unique-per-operation>`` on POST.
* The first request executes; its serialized response is stored.
* A retry with the same key and the same body **replays** the stored response
  (marked with ``Idempotency-Replayed: true``) — no side effects run twice.
* The same key with a *different* body is a client bug: ``409``.
* Concurrent duplicates race on the unique constraint; the loser replays the
  winner's stored response.
"""

import hashlib
import json
import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError
from django.http import HttpResponse
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from django_idem.conf import default_scope, idem_settings
from django_idem.models import IdempotencyRecord

logger = logging.getLogger(__name__)


class IdempotencyKeyReused(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This idempotency key was already used with a different request body."
    default_code = "idempotency_key_reused"


class IdempotencyKeyRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The Idempotency-Key header is required for this endpoint."
    default_code = "idempotency_key_required"


class IdempotencyMixin:
    """Add to a ``CreateAPIView`` (or any view with ``.create``).

    Class attributes (optional):

    * ``idempotency_required`` — override the global REQUIRED setting.
    * ``idempotency_scope`` — a callable ``(request) -> str`` overriding the
      global SCOPE_CALLABLE (e.g. ``lambda r: f"org:{r.org.pk}"``).
    """

    idempotency_required: bool | None = None
    idempotency_scope = None

    def create(self, request, *args, **kwargs):
        header = idem_settings.HEADER
        key = request.headers.get(header)

        if not key:
            required = (
                self.idempotency_required
                if self.idempotency_required is not None
                else idem_settings.REQUIRED
            )
            if required:
                raise IdempotencyKeyRequired()
            return super().create(request, *args, **kwargs)

        endpoint = request.path
        request_hash = hashlib.sha256(
            (request.body or b"") + b"|" + self._idem_scope(request).encode()
        ).hexdigest()

        existing = self._idem_lookup(request, endpoint, key)
        if existing is not None:
            return self._idem_replay(existing, request_hash)

        try:
            response = super().create(request, *args, **kwargs)
        except APIException as exc:
            # Domain errors are definitive outcomes for some callers — cache
            # them when configured, exactly like Stripe caches 4xx.
            if idem_settings.STORE_ERROR_RESPONSES and exc.status_code < 500:
                built = self._idem_build_error_response(exc)
                self._idem_store(request, endpoint, key, request_hash, built)
                return built
            raise

        return self._idem_store(request, endpoint, key, request_hash, response)

    # -- internals ----------------------------------------------------------

    def _idem_scope(self, request) -> str:
        scope_callable = self.idempotency_scope or idem_settings.SCOPE_CALLABLE
        if scope_callable is None:
            return default_scope(request)
        return scope_callable(request)

    def _idem_lookup(self, request, endpoint, key):
        return IdempotencyRecord.objects.filter(
            scope=self._idem_scope(request), endpoint=endpoint, key=key
        ).first()

    def _idem_replay(self, record, request_hash):
        if record.request_hash != request_hash:
            raise IdempotencyKeyReused()
        logger.info("django-idem: replaying %s for key %s", record.endpoint, record.key)
        return HttpResponse(
            content=json.dumps(record.response_body, cls=DjangoJSONEncoder),
            status=record.response_status,
            headers={
                idem_settings.REPLAY_HEADER: "true",
                "Content-Type": "application/json",
            },
        )

    def _idem_store(self, request, endpoint, key, request_hash, response):
        if response.status_code >= 500:
            return response  # server errors are never cached
        try:
            body = (
                json.loads(json.dumps(response.data, cls=DjangoJSONEncoder))
                if response.data is not None
                else {}
            )
            IdempotencyRecord.objects.create(
                scope=self._idem_scope(request),
                endpoint=endpoint,
                key=key,
                request_hash=request_hash,
                response_status=response.status_code,
                response_body=body,
            )
        except IntegrityError:
            # Lost the race to a concurrent duplicate — replay the winner.
            existing = self._idem_lookup(request, endpoint, key)
            if existing is not None:
                return self._idem_replay(existing, request_hash)
            raise
        return response

    def _idem_build_error_response(self, exc: APIException) -> Response:
        response = Response(status=exc.status_code)
        detail = exc.detail
        response.data = {"detail": str(detail)} if not isinstance(detail, (dict, list)) else detail
        return response
