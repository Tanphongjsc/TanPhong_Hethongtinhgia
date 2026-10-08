from .access import Workspace, get_workspace
from .company_context import ConfigurationError
from .navigation import DESTINATIONS, NAVIGATION_LABELS, SECTIONS
from django.urls import reverse


def _active_destination(request, label):
    match = request.resolver_match
    if not match or label not in DESTINATIONS:
        return False
    resource, url_name = DESTINATIONS[label]
    if match.namespace != url_name.split(":")[0]:
        return False
    if resource == "comparison":
        return match.url_name == "scenario_compare"
    if resource == "scenario" and match.url_name == "scenario_compare":
        return False
    if resource in ("bom", "packaging", "routing", "formula", "scheme", "run", "channel_fee_rule", "tax_rule", "fx_rate", "scenario"):
        return match.url_name.startswith(f"{resource}_")
    return match.url_name in {f"{resource}_{action}" for action in ("list", "detail", "create", "edit")}


def workspace(request):
    try:
        context = get_workspace(request)
    except ConfigurationError:
        # An unrelated 404/error template must still render with missing config.
        context = request._costing_workspace = Workspace(None)
    sections = []
    for title, labels in SECTIONS:
        items = tuple({
            "label": NAVIGATION_LABELS.get(label, label),
            "url": reverse(DESTINATIONS[label][1]) if label in DESTINATIONS else None,
            "active": _active_destination(request, label),
        } for label in labels)
        sections.append((NAVIGATION_LABELS.get(title, title), items, any(item["active"] for item in items)))
    return {
        "workspace": context,
        "current_organization": context.organization,
        "permissions": context.permissions,
        "sidebar_sections": sections,
    }
