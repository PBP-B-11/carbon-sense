from django import template
from django.utils.timesince import timesince

register = template.Library()


@register.filter
def ago(value):
    """Satu satuan waktu saja, mis. '3 jam lalu'."""
    if not value:
        return ""
    return f"{timesince(value, depth=1)} lalu"
