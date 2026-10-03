from django.db import models


class Echo(models.Model):
    """A toy model so create() has a real side effect to guard."""

    payload = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
