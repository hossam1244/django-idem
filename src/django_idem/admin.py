from django.contrib import admin

from django_idem.models import IdempotencyRecord


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ("endpoint", "key", "scope", "response_status", "created_at")
    search_fields = ("key", "scope", "endpoint")
    readonly_fields = [f.name for f in IdempotencyRecord._meta.fields]
