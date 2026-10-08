"""Draft persistence. Calculated scenarios are immutable at the application boundary."""
from django.core.exceptions import ValidationError
from datetime import date
import logging
import uuid
from django.db import connection, transaction, IntegrityError, DatabaseError
from django.utils import timezone
from apps.core.models import PriceScenario, Product, Sku, CostingRun, Channel, Currency
from apps.master_data.access import require_write_access
from .scenario_constants import FIELDS
from .scenario_validators import validate_input
from .engine.context import PricingContext, PricingError, digest
from .engine.runner import execute

logger = logging.getLogger(__name__)


def save_scenario(*, workspace, data, instance=None):
    require_write_access(workspace, resource="scenario", editing=instance is not None)
    values = dict(data)
    values["code"] = str(values.get("code") or "").strip().upper()
    values["name"] = str(values.get("name") or "").strip()
    for name in ("jurisdiction_code", "transaction_type", "fx_rate_type"):
        values[name] = str(values.get(name) or "").strip().upper()
    try:
        with transaction.atomic():
            if instance is not None:
                record = PriceScenario.objects.select_for_update().filter(organization=workspace.organization, pk=instance.pk).first()
                if record is None: raise ValidationError("Không tìm thấy kịch bản giá bán.")
                if record.status != "DRAFT": raise ValidationError("Kịch bản đã chốt chỉ được xem; hãy tạo kịch bản mới.")
            else: record = PriceScenario(organization=workspace.organization, created_by=None, approved_by=None)
            for name, model in (("product", Product), ("sku", Sku), ("base_run", CostingRun), ("channel", Channel), ("currency_code", Currency)):
                if values.get(name) is None: continue
                query = model.objects.filter(pk=getattr(values[name], "pk", None))
                if model is not Currency: query = query.filter(organization=workspace.organization)
                # Costing is read-only, including no row lock on its historical data.
                if model is not CostingRun: query = query.select_for_update()
                values[name] = query.first()
                if values[name] is None: raise ValidationError({name: "Không tìm thấy dữ liệu đã chọn."})
            validate_input(data=values, organization=workspace.organization, instance=record)
            for name in FIELDS: setattr(record, name, values.get(name))
            display = values["base_run"].context_jsonb.get("display", {})
            record.scenario_context_jsonb = {"schema": 1, "pricing_date": values["pricing_date"].isoformat(),
                "display": {"product": display.get("product"), "sku": display.get("sku"), "uom": display.get("uom"),
                    "channel": f"{values['channel'].code} — {values['channel'].name}", "currency": values["currency_code"].code}}
            for name in ("tax_mode", "jurisdiction_code", "transaction_type", "fx_rate_type"):
                record.scenario_context_jsonb[name] = values.get(name, "")
            record.output_snapshot_jsonb = {}
            record.save()
            return record
    except IntegrityError as error:
        if getattr(error.__cause__, "sqlstate", None) == "23505":
            raise ValidationError({"code": "Mã kịch bản đã tồn tại."}) from None
        raise ValidationError("Không thể lưu kịch bản. Vui lòng kiểm tra dữ liệu đã chọn.") from None


def calculate_scenario(*, workspace, instance):
    """Idempotent on a calculated row; failed attempts retain a draft and diagnostics."""
    require_write_access(workspace, resource="scenario", editing=True)
    for attempt in range(3):
        try:
            root = connection.get_autocommit()
            with transaction.atomic():
                if root:
                    with connection.cursor() as cursor: cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                record = PriceScenario.objects.select_for_update(of=("self",)).select_related("channel", "currency_code").filter(pk=instance.pk, organization=workspace.organization).first()
                if record is None: raise ValidationError("Không tìm thấy kịch bản giá bán.")
                if record.status == "CALCULATED": return record
                if record.status != "DRAFT": raise ValidationError("Kịch bản đã chốt chỉ được xem; hãy tạo kịch bản mới.")
                trace_id = str(uuid.uuid4())
                try:
                    run = CostingRun.objects.select_related("product__category", "sku__product__category").get(pk=record.base_run_id, organization=workspace.organization)
                    inputs = record.scenario_context_jsonb
                    day = date.fromisoformat(inputs.get("pricing_date", ""))
                    data = {name: getattr(record, name) for name in FIELDS}
                    data.update(product=run.product, sku=run.sku, pricing_date=day,
                        **{name: inputs.get(name, "") for name in ("tax_mode", "jurisdiction_code", "transaction_type", "fx_rate_type")})
                    validate_input(data=data, organization=workspace.organization, instance=record)
                    if not record.currency_code.is_active or not record.channel.is_active: raise PricingError("INACTIVE_REFERENCE", "Kênh bán hoặc tiền tệ đã ngừng hoạt động.")
                    context = PricingContext(workspace.organization, record, run, day, data["jurisdiction_code"], data["transaction_type"], data["tax_mode"], data["fx_rate_type"])
                    snapshot = execute(context)
                except Exception as error:
                    if isinstance(error, DatabaseError): raise
                    message = " ".join(error.messages) if isinstance(error, ValidationError) else str(error) if isinstance(error, PricingError) else "Dữ liệu nguồn hoặc ngày định giá không hợp lệ."
                    if not isinstance(error, (PricingError, ValidationError, ValueError, CostingRun.DoesNotExist)):
                        logger.exception("Pricing execution failed scenario_id=%s trace_id=%s", record.pk, trace_id)
                        message = "Đã xảy ra lỗi khi tính giá bán. Vui lòng cung cấp mã tham chiếu để kiểm tra."
                    record.output_snapshot_jsonb = {"schema": 1, "trace_id": trace_id, "attempted_at": timezone.now().isoformat(),
                        "errors": [{"code": getattr(error, "code", "INVALID_INPUT"), "message": message}]}
                    record.save(update_fields=["output_snapshot_jsonb"])
                    return record
                snapshot.update(trace_id=trace_id, calculated_at=timezone.now().isoformat())
                snapshot["hash"] = digest({key: value for key, value in snapshot.items() if key != "hash"})
                record.output_snapshot_jsonb = snapshot
                record.suggested_price = snapshot["result"]["gross_price"]
                record.status = "CALCULATED"
                record.save(update_fields=["output_snapshot_jsonb", "suggested_price", "status"])
                return record
        except DatabaseError as error:
            if getattr(error.__cause__, "sqlstate", None) in ("40001", "40P01") and attempt < 2: continue
            logger.exception("Pricing persistence failed scenario_id=%s", instance.pk)
            raise ValidationError("Không thể lưu kết quả định giá. Vui lòng thử lại.") from None
