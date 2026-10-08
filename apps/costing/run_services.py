"""Atomic persisted execution, idempotency, controlled failures, new-record reruns."""
from datetime import datetime, time
from decimal import Decimal
import logging
import uuid
from django.core.exceptions import ValidationError
from django.db import connection, transaction, DatabaseError
from django.utils import timezone
from apps.core.models import CostingRun, CostingRunLine, CostingScheme, Product, Sku, Uom, Currency, Organization
from apps.master_data.access import require_write_access
from .engine.context import ExecutionContext, json_data, digest
from .engine.errors import CostingError
from .engine.resolvers.scheme import resolve_scheme
from .engine.runner import execute
from .run_constants import REQUEST_FIELDS, RUN_TYPES

logger = logging.getLogger(__name__)


def request_payload(data):
    values = {key: getattr(data.get(key), "pk", data.get(key)) for key in REQUEST_FIELDS}
    values["manual"] = data.get("manual", {})
    values["supersedes_run"] = getattr(data.get("supersedes_run"), "pk", None)
    return json_data(values)


def _refresh(model, record, organization=None, **extra):
    if not isinstance(record, model): raise ValidationError("Vui lòng chọn danh mục hợp lệ.")
    query = model.objects.filter(pk=record.pk, is_active=True, **extra)
    if organization is not None: query = query.filter(organization=organization)
    if model is Product: query = query.select_related("costing_uom__category", "output_item")
    if model is Sku: query = query.select_related("sales_uom__category", "net_quantity_uom__category", "sell_item")
    if model is Uom: query = query.select_related("category")
    result = query.first()
    if not result: raise ValidationError("Danh mục đã ngừng hoạt động hoặc không thuộc hệ thống.")
    return result


def create_run(*, workspace, data, idempotency_key):
    require_write_access(workspace, resource="run")
    try: token = str(uuid.UUID(str(idempotency_key)))
    except (ValueError, TypeError, AttributeError): raise ValidationError("Khóa lần tính không hợp lệ. Vui lòng tải lại biểu mẫu.") from None
    try: payload = request_payload(data)
    except CostingError as error: raise ValidationError(str(error)) from None
    fingerprint = digest(payload)
    # Serialization failures are safe to retry: the entire run transaction rolls
    # back and the same request key is retained. No external effects or I/O.
    for attempt in range(3):
        try:
            root_transaction = connection.get_autocommit()
            with transaction.atomic():
                if root_transaction:
                    with connection.cursor() as cursor: cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                Organization.objects.select_for_update().get(pk=workspace.organization.pk)
                previous = CostingRun.objects.filter(organization=workspace.organization, idempotency_key=token).first()
                if previous:
                    if previous.context_jsonb.get("request_hash") != fingerprint:
                        raise ValidationError("Khóa lần tính đã được dùng cho dữ liệu khác. Vui lòng mở biểu mẫu mới.")
                    return previous
                product = _refresh(Product, data.get("product"), workspace.organization)
                sku = _refresh(Sku, data["sku"], workspace.organization, product=product) if data.get("sku") else None
                uom = _refresh(Uom, data.get("quantity_uom"))
                currency = _refresh(Currency, data.get("result_currency_code"))
                scheme = _refresh(CostingScheme, data.get("scheme"), workspace.organization)
                packing_unit = _refresh(Uom, data["packaging_uom"]) if data.get("packaging_uom") else None
                quantity = data.get("quantity")
                if not isinstance(quantity, Decimal) or not quantity.is_finite() or quantity <= 0 or quantity >= Decimal("1e16") or quantity.as_tuple().exponent < -8:
                    raise ValidationError("Sản lượng phải lớn hơn 0 và nằm trong độ chính xác cho phép.")
                if data.get("run_type") not in dict(RUN_TYPES): raise ValidationError("Loại lần tính chưa được hỗ trợ.")
                day = data.get("costing_date")
                from datetime import date
                if type(day) is not date: raise ValidationError("Vui lòng chọn ngày tính giá hợp lệ.")
                ctx = ExecutionContext(workspace.organization, product, sku, day, quantity, uom, currency, data.get("manual", {}), data.get("packaging_quantity"), packing_unit)
                try: version = resolve_scheme(ctx, scheme.pk)
                except CostingError as error: raise ValidationError(str(error)) from None
                parent = data.get("supersedes_run")
                if parent and not CostingRun.objects.filter(pk=parent.pk, organization=workspace.organization).exists(): raise ValidationError("Không tìm thấy lần tính gốc.")
                public_id = uuid.uuid4()
                context = {"schema": 1, "request": payload, "request_hash": fingerprint, "started_at": timezone.now().isoformat(), "notes": data.get("notes", ""),
                    "display": {"product": f"{product.code} — {product.name}", "sku": f"{sku.code} — {sku.name}" if sku else None, "scheme": f"{scheme.code} — {scheme.name}", "version": version.version_no, "uom": uom.name, "currency": currency.code}}
                run = CostingRun.objects.create(organization=workspace.organization, public_id=public_id, run_no=str(public_id), run_type=data["run_type"], scheme_version=version,
                    product=product, sku=sku, quantity=quantity, quantity_uom=uom, result_currency_code=currency,
                    effective_at=timezone.make_aware(datetime.combine(day, time.min)), context_jsonb=json_data(context), idempotency_key=token, supersedes_run=parent, created_by=None)
                try:
                    with transaction.atomic():
                        result = execute(ctx, scheme.pk)
                        CostingRunLine.objects.bulk_create([CostingRunLine(run=run, **row) for row in result.lines], batch_size=200)
                        context.update(finished_at=timezone.now().isoformat(), warnings=list(result.warnings), per_unit=str(result.per_unit))
                        run.context_jsonb = json_data(context)
                        run.version_snapshot_jsonb = result.snapshot
                        run.manufacturing_cost = result.total
                        run.full_cost = result.total
                        run.run_status = "CALCULATED"
                        run.save(update_fields=["context_jsonb", "version_snapshot_jsonb", "manufacturing_cost", "full_cost", "run_status"])
                        run.run_status, run.locked_at = "LOCKED", timezone.now()
                        run.save(update_fields=["run_status", "locked_at"])
                except Exception as error:
                    # Savepoint rolls back ALL result lines/snapshots/status. The
                    # outer transaction retains a failed run and safe diagnostics.
                    if isinstance(error, DatabaseError):
                        if getattr(error.__cause__, "sqlstate", None) in ("40001", "40P01"): raise
                    if isinstance(error, CostingError): message, code, stage = str(error), error.code, error.stage
                    else:
                        message, code, stage = "Đã xảy ra lỗi khi xử lý lần tính giá. Vui lòng cung cấp mã tham chiếu để kiểm tra.", "SYSTEM_ERROR", "execution"
                        logger.exception("Costing execution failed run_id=%s trace_id=%s stage=%s", run.pk, run.trace_id, stage)
                    context.update(finished_at=timezone.now().isoformat(), errors=[{"code": code, "stage": stage, "message": message}])
                    CostingRun.objects.filter(pk=run.pk).update(run_status="FAILED", context_jsonb=json_data(context))
                    run.refresh_from_db()
                return run
        except DatabaseError as error:
            state = getattr(error.__cause__, "sqlstate", None)
            if state in ("40001", "40P01", "23505") and attempt < 2: continue
            logger.exception("Costing persistence failed trace_key=%s", token)
            raise ValidationError("Không thể lưu lần tính giá. Vui lòng thử lại với cùng biểu mẫu.") from None
