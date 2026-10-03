# django-idem

**Stripe-style request idempotency for [Django REST Framework](https://www.django-rest-framework.org/).**

A client retrying a payment after a flaky network must never be charged twice.
`django-idem` gives any DRF create-view the full idempotency contract in one
mixin: replayed responses, key-reuse rejection, and race resolution.

[![CI](https://github.com/hossam1244/django-idem/actions/workflows/ci.yml/badge.svg)](https://github.com/hossam1244/django-idem/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/badge/pypi-0.1.0-blue)](https://pypi.org/project/django-idem/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## The contract

| Situation | Behavior |
|---|---|
| First request with `Idempotency-Key: K` | Executes; response stored |
| Retry with key `K`, **same body** | Stored response replayed, `Idempotency-Replayed: true` — **no side effects run twice** |
| Key `K` with a **different body** | `409 idempotency_key_reused` — a client bug, not a retry |
| Two requests racing with key `K` | Unique constraint resolves it; the loser replays the winner |
| Validation error (4xx) | Cached too — retries converge to the same error |
| Server error (5xx) | Never cached — clients retry with the same key |

Extracted from the author's banking backend
([novabank-api](https://github.com/hossam1244/novabank-api)), where it guards
every payment submission.

## Install

```bash
pip install django-idem        # (on PyPI soon; until then: pip install git+https://github.com/hossam1244/django-idem.git)
```

```python
# settings.py
INSTALLED_APPS = [
    ...,
    "django_idem",
]

# migrate  → creates django_idem_idempotencyrecord
```

## Usage

```python
from django_idem.mixins import IdempotencyMixin
from rest_framework import generics


class PaymentView(IdempotencyMixin, generics.CreateAPIView):
    """POSTs now require an Idempotency-Key and are safe to retry."""

    serializer_class = PaymentSerializer
```

That's it. Configure (all optional):

```python
DJANGO_IDEM = {
    "HEADER": "Idempotency-Key",  # the request header to honor
    "REPLAY_HEADER": "Idempotency-Replayed",
    "REQUIRED": True,  # 400 when the header is missing
    "STORE_ERROR_RESPONSES": True,  # cache definitive 4xx outcomes
    "SCOPE_CALLABLE": None,  # default: "user:{pk}" / "anon"
}
```

Or per view:

```python
class PaymentView(IdempotencyMixin, generics.CreateAPIView):
    idempotency_required = False  # header optional here
    idempotency_scope = lambda r: f"org:{r.org.pk}"  # custom isolation
```

Scoping matters: keys are isolated per (scope, endpoint, key). The default
scope is the requesting user; multi-tenant APIs usually want an org-scoped
callable so the same key in two tenants is two different operations.

## Testing

```bash
pip install -e . && pytest
```

Eight tests cover the contract end-to-end against a real DRF view with a real
side effect: replay without double effects, cached validation errors, key-reuse
409, required/optional modes (global and per-view), custom scoping isolation,
and stored-body fidelity. CI runs the suite across Python 3.11–3.13 ×
Django 4.2/5.1/5.2 × DRF 3.15/3.16.

## License

[MIT](LICENSE)
