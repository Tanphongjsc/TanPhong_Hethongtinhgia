from django import template
from django.urls import reverse
from apps.master_data.deletion_registry import SPECS, DETAIL_RESOURCES, state_blocker
register=template.Library()

@register.simple_tag(takes_context=True)
def deletion_action(context,record=None,resource=None,secondary=False):
    request=context.get('request')
    match=getattr(request,'resolver_match',None)
    current=DETAIL_RESOURCES.get(match.view_name) if match else None
    if resource is None:
        resource=current
        if resource is None: return None
        record=context.get(SPECS[resource].context_key)
    elif secondary and current==resource:
        return None
    if resource not in SPECS or record is None or type(record) is not SPECS[resource].model: return None
    if state_blocker(record): return None
    if resource=='uom_conversion' and record.organization_id is None: return None
    url=reverse('master_data:record_delete',args=[resource,record.pk])
    if resource=='packaging_assignment' and request is not None and request.GET:
        from urllib.parse import urlencode
        url+='?'+urlencode({'query':request.GET.urlencode()})
    return {'url':url,'label':'Xóa '+SPECS[resource].label}