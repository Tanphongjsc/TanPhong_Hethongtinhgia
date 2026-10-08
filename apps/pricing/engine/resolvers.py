"""Scenario resolution reuses Foundation queries, with explicit execution policies."""
from datetime import datetime, time
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.pricing import selectors
from apps.pricing.constants import code_label, FIELDS
from apps.pricing.validators import validate_values
from .context import PricingError


def source(record):
    return {"table": record._meta.db_table, "id": record.pk,
        "fields": {field.attname: getattr(record, field.attname) for field in record._meta.fields}}


def choose(rows, *, key, rank, label):
    groups = {}
    for row in rows: groups.setdefault(key(row), []).append(row)
    winners, rejected = [], []
    for code, candidates in sorted(groups.items()):
        best = max(rank(row) for row in candidates)
        selected = [row for row in candidates if rank(row) == best]
        if len(selected) != 1:
            raise PricingError("AMBIGUOUS_RULE", f"Có nhiều {label} cùng phạm vi và mức ưu tiên cho mã {code}.")
        winners.append(selected[0])
        rejected.extend({"id": row.pk, "code": code, "rank": rank(row)} for row in candidates if row.pk != selected[0].pk)
    return winners, rejected


class Resolver:
    def __init__(self, context):
        self.ctx, self.sources, self.fx, self.warnings, self.rejected = context, [], [], [], []
        self.cache = {}
        self.instant = timezone.make_aware(datetime.combine(context.pricing_date, time.min))

    def convert(self, amount, currency):
        target = self.ctx.scenario.currency_code_id
        if currency == target: return amount
        if not currency or not self.ctx.fx_rate_type:
            raise PricingError("MISSING_FX_TYPE", "Vui lòng chọn loại tỷ giá khi cần quy đổi tiền tệ.")
        pair = (currency, target)
        if pair not in self.cache:
            try:
                row = selectors.get_effective_fx_rate(organization=self.ctx.organization, from_currency=currency,
                    to_currency=target, rate_type=self.ctx.fx_rate_type, effective_at=self.instant)
            except selectors.PricingResolutionError as error:
                raise PricingError(error.code, f"{error} Cặp {currency} → {target}, ngày {self.ctx.pricing_date:%d/%m/%Y}.") from None
            if not row.rate.is_finite() or row.rate <= 0: raise PricingError("INVALID_FX", "Tỷ giá phải lớn hơn 0.")
            self.cache[pair] = row.rate
            self.sources.append(source(row))
            self.fx.append({"id": row.pk, "from": currency, "to": target, "rate": row.rate, "at": self.instant, "direction": "MULTIPLY"})
        return amount * self.cache[pair]

    def validate(self, row, resource):
        try: validate_values(resource=resource, data={name: getattr(row, name) for name in FIELDS[resource]}, organization=self.ctx.organization, instance=row)
        except ValidationError: raise PricingError("INVALID_RULE", "Quy tắc hiệu lực có dữ liệu không hợp lệ. Vui lòng kiểm tra cấu hình.") from None

    def monetary(self, row, name):
        value = getattr(row, name)
        return self.convert(value, row.currency_code_id) if value is not None else None

    def fees(self):
        run, channel = self.ctx.run, self.ctx.scenario.channel
        rows = list(selectors.get_applicable_channel_fee_rules(organization=self.ctx.organization, channel=channel,
            on_date=self.ctx.pricing_date, sku=run.sku, product_category=run.product.category if run.product else None,
            include_all_currencies=True)[:201])
        if len(rows) > 200: raise PricingError("RULE_LIMIT", "Có quá nhiều quy tắc phí phù hợp; vui lòng thu hẹp phạm vi.")
        winners, rejected = choose(rows, key=lambda r: r.fee_type,
            rank=lambda r: (2 if r.sku_id else 1 if r.product_category_id else 0, r.priority), label="quy tắc phí")
        self.rejected.extend({"kind": "FEE", **item} for item in rejected)
        result = []
        for row in winners:
            self.validate(row, "channel_fee_rule")
            if row.fee_base != "LIST_PRICE": raise PricingError("UNSUPPORTED_FEE_BASE", f"Chưa hỗ trợ cơ sở phí {row.fee_base}. Chỉ hỗ trợ LIST_PRICE trên giá khách trả.")
            if row.refundable_ratio != 0: raise PricingError("UNSUPPORTED_REFUND", "Chưa hỗ trợ phí có tỷ lệ hoàn; không thể tự giảm phí.")
            if not row.tax_inclusive and any((value or 0) != 0 for value in (row.rate, row.fixed_amount, row.floor_amount)):
                raise PricingError("UNSUPPORTED_FEE_TAX", "Phí chưa gồm thuế cần chính sách thuế trên phí riêng. Chỉ tính phí đã gồm thuế trong phạm vi hiện tại.")
            self.sources.append(source(row))
            result.append({"id": row.pk, "label": code_label(row.fee_type), "rate": row.rate or Decimal(0),
                "fixed": self.monetary(row, "fixed_amount") or Decimal(0), "floor": self.monetary(row, "floor_amount"), "cap": self.monetary(row, "cap_amount")})
        if not result: self.warnings.append("Không có phí kênh hiệu lực phù hợp; kịch bản không khấu trừ phí kênh.")
        return result

    def taxes(self):
        if self.ctx.tax_mode == "NONE":
            self.warnings.append("Người lập đã chọn không áp dụng thuế bán hàng cho kịch bản này.")
            return []
        run, channel = self.ctx.run, self.ctx.scenario.channel
        rows = list(selectors.get_applicable_tax_rules(organization=self.ctx.organization, jurisdiction_code=self.ctx.jurisdiction,
            on_date=self.ctx.pricing_date, tax_class_code=run.product.tax_class_code if run.product else None,
            seller_type=channel.seller_type, transaction_type=self.ctx.transaction_type or None, include_all_currencies=True)[:201])
        if len(rows) > 200: raise PricingError("RULE_LIMIT", "Có quá nhiều quy tắc thuế phù hợp; vui lòng thu hẹp phạm vi.")
        winners, rejected = choose(rows, key=lambda r: r.tax_type,
            rank=lambda r: (sum(getattr(r, name) is not None for name in ("tax_class_code", "seller_type", "transaction_type")), r.priority), label="quy tắc thuế")
        if not winners: raise PricingError("MISSING_TAX", "Không tìm thấy quy tắc thuế phù hợp tại ngày định giá.")
        self.rejected.extend({"kind": "TAX", **item} for item in rejected)
        result = []
        for row in winners:
            self.validate(row, "tax_rule")
            if row.tax_base not in ("SELLING_PRICE", "LIST_PRICE"): raise PricingError("UNSUPPORTED_TAX_BASE", f"Chưa hỗ trợ cơ sở thuế {row.tax_base}. Chỉ hỗ trợ giá bán trước thuế chung.")
            if row.recoverable_ratio != 0: raise PricingError("UNSUPPORTED_TAX_RECOVERY", "Chưa hỗ trợ quy tắc thuế bán hàng có tỷ lệ khấu trừ.")
            self.sources.append(source(row))
            result.append({"id": row.pk, "label": code_label(row.tax_type), "rate": row.rate or Decimal(0),
                "fixed": self.monetary(row, "fixed_amount") or Decimal(0), "inclusive": row.inclusive})
        if len({r["inclusive"] for r in result}) > 1:
            raise PricingError("MIXED_TAX_INCLUSION", "Chưa hỗ trợ kết hợp thuế đã gồm và chưa gồm trong cùng giá niêm yết.")
        return result
