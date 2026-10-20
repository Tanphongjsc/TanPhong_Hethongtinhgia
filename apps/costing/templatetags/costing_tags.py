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


@register.simple_tag
def run_explanation(run, line, steps):
    from apps.costing.presentation import trace_presentation
    return trace_presentation(run, line, steps)


@register.simple_tag
def snapshot_sources(snapshot):
    from apps.costing.presentation import source_groups
    return source_groups(snapshot)


@register.simple_tag
def saved_unit(snapshot, reference):
    from apps.costing.presentation import saved_unit as label
    return label(snapshot, reference)


@register.filter
def trace_is_mapping(value):
    return isinstance(value, dict)


@register.filter
def trace_is_sequence(value):
    return isinstance(value, (list, tuple))

@register.filter
def trace_key(value):
    return {"expression": "Phép tính", "arguments": "Giá trị đầu vào", "value": "Kết quả"}.get(value, value)
