from django import template
from apps.master_data.presentation import display_label, format_number, format_percent

register = template.Library()


@register.filter
def formula_value(value):
    if type(value) is bool:
        return "Có" if value else "Không"
    if isinstance(value, str):
        return value
    return format_number(value)


register.filter("display_label", display_label)
register.filter("vn_number", format_number)
register.filter("vn_percent", format_percent)


@register.simple_tag(takes_context=True)
def query_url(context, **changes):
    request = context["request"]
    query = request.GET.copy()
    for key, value in changes.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = str(value)
    encoded = query.urlencode()
    base = context.get("query_base_url", request.path)
    return f"{base}?{encoded}" if encoded else base


@register.filter
def ui_label(label):
    from apps.master_data.presentation import ui_field_label
    return ui_field_label(label)


@register.filter
def ui_help(field):
    from apps.master_data.presentation import UI_FIELD_HELP
    return UI_FIELD_HELP.get(str(field.label), field.help_text)
