"""Deletion boundary only: explicit policies, typed references and atomic removal."""
from dataclasses import dataclass
from functools import wraps
from decimal import Decimal
from hashlib import sha256
import json
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import DatabaseError, transaction, connection
from django.db.models import Q, F
from django.http import Http404
from django.urls import reverse
from apps.core import models as m
from .deletion_registry import SPECS, LABELS, OWNED, PARENT_STATUS, state_blocker
from .deletion_history import evidence

SALT = 'costing.record-delete.v1'

@dataclass(frozen=True)
class DeletionPreview:
    blockers: tuple
    warnings: tuple = ()
    owned: tuple = ()
    @property
    def allowed(self): return not self.blockers


def _serialized_delete(function):
    """Deletion only: reuse the existing internal definition lock."""
    @wraps(function)
    def call(*args, **kwargs):
        workspace = kwargs.get('workspace')
        try:
            with transaction.atomic():
                if workspace is not None and workspace.organization is not None:
                    m.Organization.objects.select_for_update().get(pk=workspace.organization.pk)
                return function(*args, **kwargs)
        except DatabaseError as error:
            _database_deletion_error(error)
    return call


def get_record(workspace, resource, identifier, *, lock=False):
    spec = SPECS.get(resource)
    if spec is None: raise Http404
    if spec.model is m.Currency:
        if not isinstance(identifier,str) or len(identifier) != 3: raise Http404
    else:
        try: identifier=int(identifier)
        except (TypeError,ValueError): raise Http404 from None
        if not 0 < identifier < 2**63: raise Http404
    query=spec.model.objects.all()
    if spec.parent: query=query.select_related(spec.parent)
    if lock: query=query.select_for_update(of=('self',))
    if any(f.name=='organization' for f in spec.model._meta.concrete_fields):
        query=query.filter(Q(organization=workspace.organization) | Q(organization__isnull=True)) if spec.model is m.UomConversion else query.filter(organization=workspace.organization)
    record=query.filter(pk=identifier).first()
    if record is None: return None
    owner=record
    while not hasattr(owner,'organization_id'):
        parent = PARENT_STATUS.get(type(owner)) or next((s.parent for s in SPECS.values() if s.model is type(owner)), '')
        if not parent: break
        owner=getattr(owner,parent)
    if hasattr(owner,'organization_id') and owner.organization_id not in (None,workspace.organization.pk): return None
    return record


def label_record(record):
    code,name=getattr(record,'code',''),getattr(record,'name','')
    if code: return f'{code} — {name}' if name else str(code)
    if hasattr(record,'version_no'):
        parent = next(s.parent for s in SPECS.values() if s.model is type(record))
        return f'{getattr(record,parent).code} · Phiên bản {record.version_no}'
    for field in ('supplier','resource','sku','component_item','packaging_item'):
        ref=getattr(record,field,None)
        if ref is not None: return f'{LABELS.get(type(record),"Dữ liệu")} — {ref.code} — {ref.name}'
    return name or getattr(record,'operation_name','') or f'{LABELS.get(type(record),"Dữ liệu")} #{record.pk}'


def _field_values(record):
    values={}
    for field in record._meta.concrete_fields:
        value=getattr(record,field.attname)
        if field.get_internal_type()=='DecimalField' and value is not None:
            value=format(Decimal(value),f'.{field.decimal_places}f')
        values[field.attname]=value
    return values


def state_fingerprint(record):
    values={'record':_field_values(record),'owned':{}}
    for relation in record._meta.related_objects:
        model=relation.related_model
        if model in OWNED.get(type(record),()):
            rows=model.objects.filter(**{relation.field.attname:record.pk}).order_by('pk')
            values['owned'][model._meta.db_table]=[_field_values(row) for row in rows.iterator(chunk_size=100)]
    return sha256(json.dumps(values,cls=DjangoJSONEncoder,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def confirmation_token(resource,record):
    return signing.dumps({'resource':resource,'id':str(record.pk),'state':state_fingerprint(record)},salt=SALT,compress=True)


def _incoming(record, *, owned=()):
    blockers, children=[],[]
    for relation in record._meta.related_objects:
        model=relation.related_model
        query=model._default_manager.filter(**{relation.field.attname:record.pk})
        count=query.count()
        if not count: continue
        label=LABELS.get(model,'dữ liệu liên quan')
        if model in owned: children.append((model,query,count,label))
        else: blockers.append(f'Không thể xóa vì đang được sử dụng bởi {label} ({count} bản ghi).')
    return blockers,children


def _code_references(record):
    errors=[]
    if isinstance(record,(m.CostElement,m.Formula)):
        from apps.formula_engine.errors import FormulaError
        from apps.formula_engine.parser import parse
        from apps.formula_engine.dependencies import references
        for version in m.FormulaVersion.objects.filter(formula__organization_id=record.organization_id,expression__icontains=record.code).select_related('formula').iterator(chunk_size=100):
            try: refs=references(parse(version.expression))
            except FormulaError:
                errors.append('Không thể xác định an toàn vì có biểu thức cũ chưa phân tích được còn chứa mã này.'); break
            kinds={'element','bare'} if isinstance(record,m.CostElement) else {'formula','bare'}
            # Bare names use the parser's unqualified kind; explicit $/@ stay separate.
            if any(name==record.code.upper() and (kind in kinds or kind not in ('element','formula')) for kind,name in refs):
                if version.formula.organization_id==record.organization_id:
                    errors.append(f'Không thể xóa vì công thức {version.formula.code} còn tham chiếu mã này.'); break
        if isinstance(record,m.Formula) and m.AllocationRule.objects.filter(organization_id=record.organization_id,formula_code__iexact=record.code).exists():
            errors.append('Không thể xóa vì quy tắc phân bổ còn tham chiếu mã công thức.')
        if isinstance(record,m.CostElement) and m.FormulaTestCase.objects.filter(formula__organization_id=record.organization_id,input_context__has_key=record.code.upper()).exists():
            errors.append('Không thể xóa vì dữ liệu kiểm thử công thức còn sử dụng mã phần tử chi phí.')
    if isinstance(record,m.AllocationRule) and m.CostingSchemeLine.objects.filter(scheme_version__scheme__organization_id=record.organization_id,system_resolver_code__iexact='ALLOCATION:'+record.code).exists():
        errors.append('Không thể xóa vì dòng phương án tính giá còn sử dụng mã quy tắc phân bổ.')
    return errors


def _conversion_blocker(record):
    from .deletion_conversions import used_conversion_reason
    return used_conversion_reason(record)


def inspect_deletion(record):
    blocked=state_blocker(record)
    if blocked: return DeletionPreview((blocked,))
    if isinstance(record,m.UomConversion) and record.organization_id is None:
        return DeletionPreview(('Quy đổi dùng chung hiện chỉ được xem; không thể xóa từ màn hình này.',))
    blockers,children=_incoming(record,owned=OWNED.get(type(record),()))
    blockers.extend(_code_references(record))
    if isinstance(record,m.UomConversion):
        reason=_conversion_blocker(record)
        if reason: blockers.append(reason)
    historical,warnings=evidence(record)
    blockers.extend(historical)
    owned=[]
    for model,query,count,label in children:
        owned.append((label,count))
        for child in query.iterator(chunk_size=100):
            external,_=_incoming(child)
            blockers.extend(external)
            child_blocks,child_warnings=evidence(child)
            blockers.extend(child_blocks); warnings=(*warnings,*child_warnings)
    if isinstance(record,m.FormulaVersion) and m.FormulaDependency.objects.filter(depends_on_formula_id=record.formula_id).exclude(formula_version_id=record.pk).exists():
        warnings=(*warnings,'Công thức khác có thể dùng phiên bản mới nhất khi kiểm thử. Xóa bản nháp có thể làm màn hình kiểm thử chuyển sang phiên bản trước; các bản đã chốt được giữ nguyên.')
    return DeletionPreview(tuple(dict.fromkeys(blockers)),tuple(dict.fromkeys(warnings)),tuple(owned))


def assert_child_removable(record):
    preview=inspect_deletion(record)
    if preview.blockers: raise ValidationError(list(preview.blockers))


@_serialized_delete
def delete_record(*,workspace,resource,identifier,token):
    try:
        with transaction.atomic():
            _lock_indirect_writers(resource)
            record=get_record(workspace,resource,identifier,lock=True)
            if record is None: raise ValidationError('Bản ghi không còn tồn tại hoặc đã được xóa trước đó.')
            try: signed=signing.loads(token,salt=SALT,max_age=1800)
            except (signing.BadSignature,TypeError,ValueError): raise ValidationError('Vui lòng mở lại hộp thoại xác nhận xóa; yêu cầu không hợp lệ hoặc đã hết hạn.') from None
            expected={'resource':resource,'id':str(record.pk),'state':state_fingerprint(record)}
            if signed!=expected: raise ValidationError('Dữ liệu đã thay đổi hoặc xác nhận không đúng bản ghi. Vui lòng kiểm tra và xác nhận lại.')
            preview=inspect_deletion(record)
            if not preview.allowed: raise ValidationError(list(preview.blockers))
            destination=destination_after_delete(record,resource)
            _,children=_incoming(record,owned=OWNED.get(type(record),()))
            for model,query,_,_ in children:
                # Explicit owned rows only; database CASCADE is never the policy.
                query.delete()
            if type(record) in PARENT_STATUS:
                _remove_child(workspace, record)
            else:
                record.delete()
            return destination
    except DatabaseError as error:
        _database_deletion_error(error)


def _database_deletion_error(error):
    state=getattr(error.__cause__,'sqlstate',None)
    if state in ('55P03','40P01'):
        raise ValidationError('Dữ liệu đang được thao tác khác sử dụng. Vui lòng đợi và xác nhận xóa lại.') from None
    if state=='P0001': raise ValidationError('Không thể xóa dữ liệu đã được chốt hoặc khóa.') from None
    raise ValidationError('Không thể xóa vì có dữ liệu liên quan hoặc dữ liệu vừa thay đổi. Vui lòng tải lại và kiểm tra các liên kết.') from None

def destination_after_delete(record,resource):
    spec=SPECS[resource]
    if resource.endswith('_version'):
        base=resource.removesuffix('_version'); parent=getattr(record,spec.parent)
        return reverse(SPECS[base].list_name.removesuffix('_list')+'_detail',args=[parent.pk])
    if resource=='packaging_assignment':
        return reverse('bom:packaging_assignment_list',args=[record.packaging_config_id])
    if resource in ('bom_line','packaging_line','routing_operation','scheme_line'):
        parent=getattr(record,spec.parent)
        base={'bom_line':'bom','packaging_line':'packaging','routing_operation':'routing','scheme_line':'scheme'}[resource]
        version_spec=SPECS[base+'_version']
        return reverse(SPECS[base].list_name.removesuffix('_list')+'_version_detail',args=[getattr(parent,version_spec.parent+'_id'),parent.pk])
    return reverse(spec.list_name)

def _remove_child(workspace, record):
    # Existing child-removal services own hash invalidation and mutation rules.
    if isinstance(record,m.RecipeLine):
        from apps.bom.services import remove_line
        remove_line(workspace=workspace,recipe=record.recipe_version.recipe,version=record.recipe_version,instance=record)
    elif isinstance(record,m.PackagingLine):
        from apps.bom.packaging_services import remove_line
        remove_line(workspace=workspace,config=record.packaging_config_version.packaging_config,version=record.packaging_config_version,instance=record)
    elif isinstance(record,m.RoutingOperation):
        from apps.bom.routing_services import remove_operation
        remove_operation(workspace=workspace,routing=record.routing_version.routing,version=record.routing_version,instance=record)
    else:
        from apps.costing.services import remove_line
        remove_line(workspace=workspace,scheme=record.scheme_version.scheme,version=record.scheme_version,instance=record)


def _lock_indirect_writers(resource):
    # No ORM equivalent for table locks. Only a deletion takes these short,
    # non-waiting locks; existing writers/calculation services are unchanged.
    models = {
        'formula': (m.AllocationRule,m.CostPool),
        'uom_conversion': (m.Recipe,m.PackagingConfig,m.Routing,m.SupplierPrice,m.ResourceRate,m.Product,m.Sku,m.Item,m.CostPoolPeriod,m.CostElement),
    }.get(resource,())
    if models:
        tables=', '.join(connection.ops.quote_name(model._meta.db_table) for model in sorted(models,key=lambda model:model._meta.db_table))
        with connection.cursor() as cursor:
            cursor.execute('LOCK TABLE '+tables+' IN EXCLUSIVE MODE NOWAIT')
