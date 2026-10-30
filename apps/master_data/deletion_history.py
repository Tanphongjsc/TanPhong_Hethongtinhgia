"""Read historical references with known structure; never call financial engines."""
from django.apps import apps
from hashlib import sha256
import json
from django.db.models import Q
from apps.core.models import CostingRun, PriceScenario, Uom

INCOMPLETE = 'Không thể xóa vì nguồn lịch sử còn tham chiếu nhưng bản chụp chưa đủ thông tin để xác định an toàn.'
COMPLETE = 'Dữ liệu này có trong bản chụp lịch sử đã lưu đầy đủ. Kết quả cũ vẫn giữ nguyên; các lần tính mới dùng cấu hình hiện tại.'

TABLE_MODELS = {model._meta.db_table: model for model in apps.get_app_config('core').get_models()}

def _trusted(snapshot, hash_field):
    if not isinstance(snapshot,dict) or snapshot.get('schema') != 1: return False
    content={k:v for k,v in snapshot.items() if k != hash_field}
    expected=sha256(json.dumps(content,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    return snapshot.get(hash_field)==expected


def evidence(record):
    warnings, blockers = [], []
    table, pk = record._meta.db_table, str(record.pk)
    def inspect(value, hint=None, trusted=False):
        # Typed source-map keys remain evidence even when their value is damaged.
        hint_table,hint_id=(hint.split(':',1) if isinstance(hint,str) and ':' in hint else (None,None))
        keyed = hint_table == table and hint_id == pk
        if keyed and not isinstance(value,dict):
            blockers.append(INCOMPLETE)
        if isinstance(value,list):
            for entry in value: inspect(entry,trusted=trusted)
        elif isinstance(value,dict):
            raw_table=value.get('table',hint_table)
            source_table=raw_table if isinstance(raw_table,str) else None
            source_id=value.get('id',hint_id)
            fields=value.get('fields')
            direct=keyed or (source_table == table and str(source_id) == pk)
            model=TABLE_MODELS.get(source_table)
            related=False
            if model and isinstance(fields,dict):
                related=any(f.is_relation and f.related_model is type(record) and str(fields.get(f.attname)) == pk for f in model._meta.concrete_fields)
            if direct or related:
                required={f.attname for f in model._meta.concrete_fields if f.get_internal_type() not in ('JSONField','UUIDField')} if model else set()
                consistent=not hint_table or (source_table == hint_table and str(source_id) == hint_id)
                complete=trusted and consistent and bool(required) and isinstance(fields,dict) and required.issubset(fields)
                if complete: warnings.append(COMPLETE)
                else: blockers.append(INCOMPLETE)
            for key,child in value.items():
                # Inspect a typed key independently of the child's JSON type.
                if isinstance(child,(dict,list)) or (isinstance(key,str) and ':' in key):
                    inspect(child,str(key),trusted)
    condition = Q(version_snapshot_jsonb__icontains=pk) | Q(fx_snapshot_jsonb__icontains=pk)
    if isinstance(record,Uom): condition |= Q(context_jsonb__request__packaging_uom=record.pk)
    for run in CostingRun.objects.filter(condition).only('version_snapshot_jsonb','fx_snapshot_jsonb','context_jsonb').iterator(chunk_size=50):
        inspect(run.version_snapshot_jsonb,trusted=_trusted(run.version_snapshot_jsonb,'sha256')); inspect(run.fx_snapshot_jsonb,trusted=_trusted(run.fx_snapshot_jsonb,'sha256'))
        context=run.context_jsonb if isinstance(run.context_jsonb,dict) else {}
        request=context.get('request')
        if isinstance(record,Uom) and isinstance(request,dict) and request.get('packaging_uom') == record.pk:
            blockers.append('Không thể xóa đơn vị cơ sở đóng gói còn được đầu vào của lần tính tham chiếu.')
    for scenario in PriceScenario.objects.filter(output_snapshot_jsonb__icontains=pk).only('output_snapshot_jsonb').iterator(chunk_size=50):
        inspect(scenario.output_snapshot_jsonb,trusted=_trusted(scenario.output_snapshot_jsonb,'hash'))
        snapshot = scenario.output_snapshot_jsonb or {}
        if isinstance(snapshot,dict):
            trace=snapshot.get('trace')
            rejected=trace.get('rejected_rules') if isinstance(trace,dict) else None
            for ref in rejected if isinstance(rejected,list) else ():
                if isinstance(ref,dict) and str(ref.get('id')) == pk and isinstance(ref.get('kind'),str) and table == {'FEE':'channel_fee_rule','TAX':'tax_rule'}.get(ref['kind']):
                    warnings.append('Quy tắc đã xuất hiện trong diễn giải lựa chọn phí/thuế. Bản chụp diễn giải được giữ nguyên.')
    return tuple(dict.fromkeys(blockers)), tuple(dict.fromkeys(warnings))