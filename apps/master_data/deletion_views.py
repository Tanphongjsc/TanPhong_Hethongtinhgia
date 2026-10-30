"""Read-only confirmation GET and guarded POST; all deletion policy is in service."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.vary import vary_on_headers
from .access import get_workspace
from . import deletion
from .deletion_registry import SPECS
from .ui_helpers import is_htmx, saved_response

@require_http_methods(['GET','POST'])
@vary_on_headers('HX-Request','HX-History-Restore-Request')
def record_delete(request, resource, identifier):
    workspace=get_workspace(request)
    if workspace.organization is None: raise Http404
    spec=SPECS.get(resource)
    if spec is None: raise Http404
    request.costing_resource_label=spec.label
    errors=[]
    if request.method=='POST':
        try:
            destination=deletion.delete_record(workspace=workspace,resource=resource,identifier=identifier,token=request.POST.get('confirmation'))
        except ValidationError as error: errors=error.messages
        else:
            messages.success(request,f'Đã xóa {spec.label}.')
            if resource=='packaging_assignment' and is_htmx(request):
                return _assignment_refresh(request,workspace,destination)
            return saved_response(request,destination)
    record=deletion.get_record(workspace,resource,identifier)
    if record is None and request.method=='GET': raise Http404
    preview=deletion.inspect_deletion(record) if record else deletion.DeletionPreview(())
    context={'page_title':'Xác nhận xóa','resource_label':spec.label,'record':record,
        'record_label':deletion.label_record(record) if record else spec.label,
        'delete_url':request.path,'list_url':reverse(spec.list_name),
        'return_query':request.POST.get('query',request.GET.get('query','')),
        'confirmation_token':deletion.confirmation_token(resource,record) if record else '',
        'can_delete':bool(record) and preview.allowed,'blockers':preview.blockers,'warnings':preview.warnings,
        'owned_rows':preview.owned,'delete_errors':errors,'delete_modal':is_htmx(request),
        'breadcrumbs':(('Xóa dữ liệu',None),('Xác nhận xóa',None))}
    return render(request,'master_data/partials/delete_confirm_content.html' if is_htmx(request) else 'master_data/delete_confirm.html',context)

def _assignment_refresh(request,workspace,destination):
    # Refresh the existing table after a row action, preserving its GET filters.
    from copy import copy
    from django.http import QueryDict
    from django.urls import resolve
    from apps.bom import packaging_selectors as selectors
    from apps.bom.definition_helpers import table_context
    config=selectors.config_detail(organization=workspace.organization,pk=resolve(destination).kwargs['pk'])
    filters=QueryDict(request.POST.get('query',''))
    page,sort,size=selectors.assignment_list(config=config,organization=workspace.organization,filters=filters)
    context=table_context(page=page,sort=sort,per_page=size,list_url=destination,
        columns=(('sku','SKU',False),(None,'Cấu hình chính',False),('effective_from','Hiệu lực từ ngày',False),(None,'Hiệu lực đến ngày',False),(None,'Hiệu lực theo ngày',False)),
        rows_template='bom/packaging/partials/assignment_rows.html',sort_labels=(('sku','SKU'),('effective_from','Hiệu lực từ ngày'),('created_at','Ngày tạo')),
        config=config,filters=filters,query_base_url=destination,has_filters=bool(filters),resource_label='liên kết SKU')
    table_request=copy(request); table_request.GET=filters; table_request.path=destination
    response=render(table_request,'master_data/partials/delete_assignment_success.html',context)
    response['HX-Retarget']='#reference-data-table'; response['HX-Reswap']='outerHTML'
    return response