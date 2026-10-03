"""Package settings — override anything via ``DJANGO_IDEM`` in settings."""

from django.conf import settings

DEFAULTS: dict[str, object] = {
    # Header clients send to opt a request into idempotency.
    "HEADER": "Idempotency-Key",
    # Response header marking a replayed response.
    "REPLAY_HEADER": "Idempotency-Replayed",
    # Require the header on views using the mixin? (False → passthrough when absent)
    "REQUIRED": True,
    # Cache definitive outcomes (2xx/4xx); never 5xx.
    "STORE_ERROR_RESPONSES": True,
    # Produces the scope string for a request (default: user pk or "anon").
    "SCOPE_CALLABLE": None,
}


class IdemSettings:
    """Simple overlay over ``settings.DJANGO_IDEM`` with sane defaults."""

    def __getattr__(self, name: str):
        if name not in DEFAULTS:
            raise AttributeError(f"Unknown django-idem setting: {name}")
        user = getattr(settings, "DJANGO_IDEM", {})
        return user.get(name, DEFAULTS[name])


idem_settings = IdemSettings()


def default_scope(request) -> str:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return f"user:{user.pk}"
    return "anon"
