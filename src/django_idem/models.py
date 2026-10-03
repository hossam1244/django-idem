"""The idempotency record: one stored response per (scope, endpoint, key)."""

import uuid
from typing import Any

from django.db import models
from django.utils import timezone


class IdempotencyRecord(models.Model):
    """Stores the rendered response of an idempotent request for replay.

    `scope` typically identifies the actor (user id) plus whatever context
    the endpoint cares about — it is produced by the scope callable you
    configure (default: the authenticated user's primary key).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scope = models.CharField(max_length=200, db_index=True)
    endpoint = models.CharField(max_length=200)
    key = models.CharField(max_length=100)
    request_hash = models.CharField(max_length=64)
    response_status = models.PositiveSmallIntegerField()
    response_body: Any = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "endpoint", "key"], name="django_idem_unique_key"
            )
        ]
        indexes = [models.Index(fields=["scope", "endpoint"])]

    def __str__(self) -> str:
        return f"{self.endpoint}#{self.key}"
