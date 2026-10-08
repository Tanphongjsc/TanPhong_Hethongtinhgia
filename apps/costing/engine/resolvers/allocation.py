from apps.core.models import AllocationRule, CostPoolPeriod
from ..context import ResolvedValue, step
from ..errors import CostingError
from .common import active, dated, one


def allocation_rule(organization, code, day):
    return one(dated(AllocationRule.objects.filter(organization=organization, code=code, status="EFFECTIVE", pool__is_active=True, pool__organization=organization).select_related("pool", "basis_uom__category"), day), "quy tắc phân bổ")


def allocate(ctx, units, code, *, output_quantity):
    rule = allocation_rule(ctx.organization, code, ctx.day)
    if rule.basis_type != "NORMAL_CAPACITY" or rule.formula_code or rule.condition_jsonb:
        raise CostingError("Quy tắc phân bổ này chưa có dữ liệu mẫu số hoặc hợp đồng thực thi. Chỉ hỗ trợ công suất bình thường có số liệu kỳ và đơn vị rõ ràng.", code="UNSUPPORTED_ALLOCATION_DRIVER", stage="allocation")
    period = one(CostPoolPeriod.objects.filter(pool=rule.pool, period_start__lte=ctx.day, period_end__gte=ctx.day, status="EFFECTIVE").select_related("currency_code", "capacity_uom__category"), "số liệu kỳ của nhóm chi phí chung")
    if not period.normal_capacity or period.normal_capacity <= 0 or not period.capacity_uom:
        raise CostingError("Thiếu công suất bình thường hoặc đơn vị công suất của kỳ phân bổ.", code="MISSING_DENOMINATOR", stage="allocation")
    if period.amount < 0: raise CostingError("Số tiền kỳ chi phí không hợp lệ.", stage="allocation")
    if rule.basis_uom_id and rule.basis_uom_id != period.capacity_uom_id:
        raise CostingError("Đơn vị cơ sở quy tắc khác đơn vị công suất kỳ; chưa có quy tắc chọn tiêu thức.", stage="allocation")
    if period.currency_code_id != ctx.currency.pk: raise CostingError("Chi phí chung khác tiền tệ kết quả; chưa có quy tắc FX.", code="MISSING_FX", stage="allocation")
    active(ctx, rule.pool, period.currency_code, period.capacity_uom)
    ctx.remember(rule, period)
    usage, conversion = output_quantity(period.capacity_uom)
    if usage > period.normal_capacity:
        raise CostingError("Sản lượng vượt công suất bình thường; chưa có quy tắc xử lý phần vượt công suất.", code="UNSUPPORTED_CAPACITY", stage="allocation")
    amount = period.amount * usage / period.normal_capacity
    return ResolvedValue(amount, (*conversion, step("Phân bổ theo công suất bình thường", **{"Quy tắc": rule.code, "Nhóm chi phí": rule.pool.code, "Kỳ từ ngày": period.period_start, "Kỳ đến ngày": period.period_end, "Chi phí kỳ": period.amount, "Tiêu thức sử dụng": usage, "Công suất bình thường": period.normal_capacity, "Đơn vị": period.capacity_uom.name, "Chi phí phân bổ": amount})))
