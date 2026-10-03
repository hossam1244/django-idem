from django.apps import AppConfig


class DjangoIdemConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_idem"
    verbose_name = "Django Idempotency"
