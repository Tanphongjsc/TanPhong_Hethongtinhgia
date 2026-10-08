from django import template
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from apps.master_data.presentation import format_number, display_label

register = template.Library()


@register.filter
def snapshot_date(value):
    if not value: return "—"
    text = str(value)
    try:
        if len(text) == 10:
            day = parse_date(text)
            return day.strftime("%d/%m/%Y") if day else text
        moment = parse_datetime(text)
        if moment: return (timezone.localtime(moment) if timezone.is_aware(moment) else moment).strftime("%d/%m/%Y %H:%M")
        day = parse_date(text)
        return day.strftime("%d/%m/%Y") if day else text
    except ValueError: return text


@register.filter
def trace_value(value):
    if type(value) is bool: return "Có" if value else "Không"
    if isinstance(value, list): return ", ".join(trace_value(item) for item in value)
    if value is None: return "—"
    if isinstance(value, str) and (len(value) == 10 and value[4:5] == "-" or "T" in value and ":" in value): return snapshot_date(value)
    return display_label(format_number(value))
