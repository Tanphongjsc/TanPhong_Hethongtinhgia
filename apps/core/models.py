import uuid
from datetime import date

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone as django_timezone


class AllocationRule(models.Model):
    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey("Organization", models.DO_NOTHING)
    pool = models.ForeignKey("CostPool", models.DO_NOTHING)
    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    basis_type = models.CharField(max_length=50)
    basis_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    formula_code = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )
    priority = models.IntegerField(default=100)
    effective_from = models.DateField()
    effective_to = models.DateField(
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )
    condition_jsonb = models.JSONField(default=dict)
    created_by = models.UUIDField(
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "allocation_rule"
        unique_together = (("organization", "code"),)


class ApprovalAction(models.Model):
    id = models.BigAutoField(primary_key=True)

    approval_request = models.ForeignKey(
        "ApprovalRequest",
        models.DO_NOTHING,
    )

    step_no = models.IntegerField()
    action = models.CharField(max_length=30)

    actor_id = models.UUIDField(
        blank=True,
        null=True,
    )

    comment = models.TextField(
        blank=True,
        null=True,
    )

    before_status = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    after_status = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    acted_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "approval_action"
        db_table_comment = (
            "Lịch sử phê duyệt append-only theo từng bước."
        )


class ApprovalRequest(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
    )

    entity_type = models.CharField(max_length=80)
    entity_id = models.BigIntegerField()
    workflow_code = models.CharField(max_length=120)

    status = models.CharField(
        max_length=30,
        default="PENDING",
    )

    current_step = models.IntegerField(default=1)

    requested_by = models.UUIDField(
        blank=True,
        null=True,
    )

    requested_at = models.DateTimeField(default=django_timezone.now)

    requested_reason = models.TextField(
        blank=True,
        null=True,
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "approval_request"
        db_table_comment = (
            "Maker-checker approval header cho Formula, BOM, "
            "Costing Scheme, Rate, Standard Cost, Price Rule, "
            "Manual Override..."
        )


class AuditEvent(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    entity_type = models.CharField(max_length=100)

    entity_id = models.BigIntegerField(
        blank=True,
        null=True,
    )

    action = models.CharField(max_length=50)

    actor_id = models.UUIDField(
        blank=True,
        null=True,
    )

    occurred_at = models.DateTimeField(default=django_timezone.now)

    reason = models.TextField(
        blank=True,
        null=True,
    )

    before_jsonb = models.JSONField(
        blank=True,
        null=True,
    )

    after_jsonb = models.JSONField(
        blank=True,
        null=True,
    )

    entity_hash_before = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )

    entity_hash_after = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )

    trace_id = models.UUIDField(
        blank=True,
        null=True,
    )

    source_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
    )

    user_agent = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "audit_event"
        db_table_comment = (
            "Audit log append-only: ai thay đổi gì, lúc nào, "
            "vì sao, before/after và hash."
        )


class Channel(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    channel_type = models.CharField(max_length=30)

    platform_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    market_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    seller_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    default_currency_code = models.ForeignKey(
        "Currency",
        models.DO_NOTHING,
        db_column="default_currency_code",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "channel"
        unique_together = (("organization", "code"),)


class ChannelFeeRule(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
    )

    channel = models.ForeignKey(
        Channel,
        models.DO_NOTHING,
    )

    product_category = models.ForeignKey(
        "ProductCategory",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    sku = models.ForeignKey(
        "Sku",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    fee_type = models.CharField(max_length=80)

    fee_base = models.CharField(
        max_length=80,
        db_comment=(
            "Cơ sở tính phí: LIST_PRICE, ACTUAL_PAID, "
            "PAYMENT_BASE, PAYOUT, PER_ORDER..."
        ),
    )

    rate = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        blank=True,
        null=True,
    )

    fixed_amount = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    currency_code = models.ForeignKey(
        "Currency",
        models.DO_NOTHING,
        db_column="currency_code",
        blank=True,
        null=True,
    )

    cap_amount = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    floor_amount = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    refundable_ratio = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        default=0,
    )

    tax_inclusive = models.BooleanField(default=False)
    priority = models.IntegerField(default=100)

    effective_from = models.DateField()

    effective_to = models.DateField(
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    source_reference = models.TextField(
        blank=True,
        null=True,
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "channel_fee_rule"


class CostElement(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
    )

    group = models.ForeignKey(
        "CostElementGroup",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    code = models.CharField(
        max_length=120,
        db_comment=(
            "Mã kỹ thuật ổn định để formula tham chiếu, "
            "ví dụ MATERIAL_COST, PACKAGING_COST, TARGET_MARGIN."
        ),
    )

    name = models.CharField(max_length=255)

    description = models.TextField(
        blank=True,
        null=True,
    )

    value_type = models.CharField(max_length=30)

    dimension_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    default_source_mode = models.CharField(max_length=30)
    accounting_scope = models.CharField(max_length=40)
    cost_scope = models.CharField(max_length=40)

    currency_code = models.ForeignKey(
        "Currency",
        models.DO_NOTHING,
        db_column="currency_code",
        blank=True,
        null=True,
    )

    default_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    is_sensitive = models.BooleanField(
        default=False,
        db_comment=(
            "Đánh dấu phần tử nhạy cảm như giá mua, "
            "margin, tỷ lệ phí."
        ),
    )

    rounding_scale = models.SmallIntegerField(default=6)

    rounding_mode = models.CharField(
        max_length=30,
        default="HALF_UP",
    )

    is_active = models.BooleanField(default=True)

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    updated_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "cost_element"
        unique_together = (("organization", "code"),)
        db_table_comment = (
            "Từ điển biến nghiệp vụ dùng trong Formula Engine "
            "và Costing Scheme."
        )


class CostElementGroup(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
    )

    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    category_code = models.CharField(max_length=100)

    description = models.TextField(
        blank=True,
        null=True,
    )

    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "cost_element_group"
        unique_together = (("organization", "code"),)
        db_table_comment = (
            "Nhóm phần tử chi phí: Material, Packaging, Labor, "
            "Machine, Overhead, Logistics, Channel, Tax, Profit."
        )


class CostPool(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    pool_type = models.CharField(max_length=50)

    description = models.TextField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "cost_pool"
        unique_together = (("organization", "code"),)


class CostPoolPeriod(models.Model):
    id = models.BigAutoField(primary_key=True)

    pool = models.ForeignKey(
        CostPool,
        models.DO_NOTHING,
    )

    period_start = models.DateField()
    period_end = models.DateField()

    amount = models.DecimalField(
        max_digits=24,
        decimal_places=8,
    )

    currency_code = models.ForeignKey(
        "Currency",
        models.DO_NOTHING,
        db_column="currency_code",
    )

    normal_capacity = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    capacity_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    source_reference = models.TextField(
        blank=True,
        null=True,
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "cost_pool_period"


class CostingOverride(models.Model):
    id = models.BigAutoField(primary_key=True)

    run = models.ForeignKey(
        "CostingRun",
        models.DO_NOTHING,
    )

    scheme_line = models.ForeignKey(
        "CostingSchemeLine",
        models.DO_NOTHING,
    )

    original_value = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    override_value = models.DecimalField(
        max_digits=24,
        decimal_places=8,
    )

    reason = models.TextField()

    override_status = models.CharField(
        max_length=30,
        default="PENDING",
    )

    requested_by = models.UUIDField(
        blank=True,
        null=True,
    )

    approved_by = models.UUIDField(
        blank=True,
        null=True,
    )

    requested_at = models.DateTimeField(default=django_timezone.now)

    approved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "costing_override"
        db_table_comment = (
            "Manual override được lưu riêng, không sửa mất "
            "giá trị engine đã tính."
        )


class CostingRun(models.Model):
    id = models.BigAutoField(primary_key=True)

    public_id = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
    )

    run_no = models.CharField(max_length=120)
    run_type = models.CharField(max_length=30)

    run_status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    scheme_version = models.ForeignKey(
        "CostingSchemeVersion",
        models.DO_NOTHING,
    )

    product = models.ForeignKey(
        "Product",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    sku = models.ForeignKey(
        "Sku",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    channel = models.ForeignKey(
        Channel,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    quantity = models.DecimalField(
        max_digits=24,
        decimal_places=8,
    )

    quantity_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
    )

    result_currency_code = models.ForeignKey(
        "Currency",
        models.DO_NOTHING,
        db_column="result_currency_code",
    )

    effective_at = models.DateTimeField()

    context_jsonb = models.JSONField(default=dict)

    version_snapshot_jsonb = models.JSONField(
        default=dict,
        db_comment=(
            "Snapshot các version đã resolve: recipe, packaging, "
            "routing, formula, rule, supplier/resource rate..."
        ),
    )

    fx_snapshot_jsonb = models.JSONField(default=dict)

    manufacturing_cost = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    inventory_cost = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    landed_cost = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    cost_to_serve = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    channel_cost = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    full_cost = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    target_selling_price = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    actual_realized_margin = models.DecimalField(
        max_digits=18,
        decimal_places=10,
        blank=True,
        null=True,
    )

    trace_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
    )

    idempotency_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_comment=(
            "Khóa idempotency để API retry không tạo "
            "nhiều run trùng."
        ),
    )

    supersedes_run = models.ForeignKey(
        "self",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    compares_to_run = models.ForeignKey(
        "self",
        models.DO_NOTHING,
        related_name="costingrun_compares_to_run_set",
        blank=True,
        null=True,
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    approved_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    approved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    locked_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "costing_run"
        unique_together = (
            ("organization", "idempotency_key"),
            ("organization", "run_no"),
        )
        db_table_comment = (
            "Mỗi lần tính tạo một Costing Run riêng. "
            "Run lưu snapshot version/rate/context."
        )


class CostingRunLine(models.Model):
    id = models.BigAutoField(primary_key=True)

    run = models.ForeignKey(
        CostingRun,
        models.DO_NOTHING,
    )

    scheme_line = models.ForeignKey(
        "CostingSchemeLine",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    cost_element = models.ForeignKey(
        CostElement,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    formula_version = models.ForeignKey(
        "FormulaVersion",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    line_code = models.CharField(max_length=120)
    label = models.CharField(max_length=255)
    line_type = models.CharField(max_length=30)
    source_mode = models.CharField(max_length=30)
    value_type = models.CharField(max_length=30)

    quantity = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    quantity_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    unit_rate = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    amount = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    currency_code = models.ForeignKey(
        "Currency",
        models.DO_NOTHING,
        db_column="currency_code",
        blank=True,
        null=True,
    )

    percent_value = models.DecimalField(
        max_digits=18,
        decimal_places=10,
        blank=True,
        null=True,
    )

    number_value = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    boolean_value = models.BooleanField(
        blank=True,
        null=True,
    )

    text_value = models.TextField(
        blank=True,
        null=True,
    )

    input_snapshot_jsonb = models.JSONField(default=dict)
    source_trace_jsonb = models.JSONField(default=dict)
    warnings_jsonb = models.JSONField(default=list)

    display_order = models.IntegerField()

    computed_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "costing_run_line"
        unique_together = (
            ("run", "line_code"),
            ("run", "display_order"),
        )
        db_table_comment = (
            "Snapshot chi tiết từng dòng tính giá: input, "
            "formula/rule source, intermediate trace và output."
        )


class CostingScheme(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    purpose = models.CharField(max_length=100)

    context_scope = models.CharField(
        max_length=100,
        default="GENERAL",
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "costing_scheme"
        unique_together = (("organization", "code"),)
        db_table_comment = (
            "Định nghĩa một Cost Sheet/chế độ tính giá ổn định. "
            "Nội dung cấu hình nằm ở version và lines."
        )


class CostingSchemeLine(models.Model):
    id = models.BigAutoField(primary_key=True)

    scheme_version = models.ForeignKey(
        "CostingSchemeVersion",
        models.DO_NOTHING,
    )

    cost_element = models.ForeignKey(
        CostElement,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    line_code = models.CharField(max_length=120)
    label = models.CharField(max_length=255)
    line_type = models.CharField(max_length=30)
    source_mode = models.CharField(max_length=30)

    system_resolver_code = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )

    rule_table = models.ForeignKey(
        "RuleTable",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    formula_version = models.ForeignKey(
        "FormulaVersion",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    external_adapter_code = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )

    condition_jsonb = models.JSONField(default=dict)

    editable = models.BooleanField(default=False)

    min_override_value = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    max_override_value = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    override_requires_reason = models.BooleanField(default=True)

    approval_policy_code = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )

    visibility_scope = models.CharField(
        max_length=30,
        default="INTERNAL",
    )

    cost_scope = models.CharField(max_length=40)
    display_order = models.IntegerField()

    rounding_scale = models.SmallIntegerField(
        blank=True,
        null=True,
    )

    notes = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "costing_scheme_line"
        unique_together = (
            ("scheme_version", "line_code"),
            ("scheme_version", "display_order"),
        )
        db_table_comment = (
            "Dòng cấu hình Costing Scheme; hỗ trợ source SYSTEM, "
            "MANUAL, LOOKUP, FORMULA và EXTERNAL."
        )


class CostingSchemeVersion(models.Model):
    id = models.BigAutoField(primary_key=True)

    scheme = models.ForeignKey(
        CostingScheme,
        models.DO_NOTHING,
    )

    version_no = models.IntegerField()

    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    effective_from = models.DateField(
        blank=True,
        null=True,
    )

    effective_to = models.DateField(
        blank=True,
        null=True,
    )

    change_reason = models.TextField(
        blank=True,
        null=True,
    )

    content_hash = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    approved_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    approved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "costing_scheme_version"
        unique_together = (("scheme", "version_no"),)


class Currency(models.Model):
    code = models.CharField(
        primary_key=True,
        max_length=3,
    )

    name = models.CharField(max_length=100)

    decimal_places = models.SmallIntegerField(default=2)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "currency"
        db_table_comment = (
            "Danh mục tiền tệ. Mọi đơn giá/chi phí/tỷ giá "
            "phải khai báo currency rõ ràng."
        )


class Formula(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)

    output_element = models.ForeignKey(
        CostElement,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "formula"
        unique_together = (("organization", "code"),)
        db_table_comment = (
            "Identity ổn định của công thức. "
            "Expression nằm trong formula_version."
        )


class FormulaDependency(models.Model):
    id = models.BigAutoField(primary_key=True)

    formula_version = models.ForeignKey(
        "FormulaVersion",
        models.DO_NOTHING,
    )

    depends_on_element = models.ForeignKey(
        CostElement,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    depends_on_formula = models.ForeignKey(
        Formula,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    dependency_kind = models.CharField(max_length=30)

    dependency_code = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "formula_dependency"
        db_table_comment = (
            "Dependency graph phục vụ cycle detection, "
            "topological sort, impact analysis và explainability."
        )


class FormulaTestCase(models.Model):
    id = models.BigAutoField(primary_key=True)

    formula = models.ForeignKey(
        Formula,
        models.DO_NOTHING,
    )

    name = models.CharField(max_length=255)

    input_context = models.JSONField()

    expected_value_numeric = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    expected_value_text = models.TextField(
        blank=True,
        null=True,
    )

    tolerance = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        default=0,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "formula_test_case"
        db_table_comment = (
            "Golden/regression test cho Formula."
        )


class FormulaVersion(models.Model):
    id = models.BigAutoField(primary_key=True)

    formula = models.ForeignKey(
        Formula,
        models.DO_NOTHING,
    )

    version_no = models.IntegerField()

    expression = models.TextField()

    ast_jsonb = models.JSONField(
        blank=True,
        null=True,
    )

    ast_hash = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    effective_from = models.DateField(
        blank=True,
        null=True,
    )

    effective_to = models.DateField(
        blank=True,
        null=True,
    )

    validation_status = models.CharField(
        max_length=30,
        default="NOT_VALIDATED",
    )

    validation_message = models.TextField(
        blank=True,
        null=True,
    )

    change_reason = models.TextField(
        blank=True,
        null=True,
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    approved_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    submitted_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    approved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "formula_version"
        unique_together = (("formula", "version_no"),)
        db_table_comment = (
            "Biểu thức DSL có version. "
            "Không eval Python/JavaScript/SQL trực tiếp."
        )


class FxRate(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
    )

    rate_type = models.CharField(max_length=50)

    from_currency_code = models.ForeignKey(
        Currency,
        models.DO_NOTHING,
        db_column="from_currency_code",
    )

    to_currency_code = models.ForeignKey(
        Currency,
        models.DO_NOTHING,
        db_column="to_currency_code",
        related_name="fxrate_to_currency_code_set",
    )

    rate = models.DecimalField(
        max_digits=24,
        decimal_places=12,
    )

    effective_at = models.DateTimeField()

    valid_to = models.DateTimeField(
        blank=True,
        null=True,
    )

    source_name = models.CharField(max_length=150)

    source_reference = models.TextField(
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=30,
        default="EFFECTIVE",
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "fx_rate"
        db_table_comment = (
            "Tỷ giá theo loại Spot/Reference, Accounting, "
            "Negotiated hoặc Settlement."
        )


class Item(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
    )

    category = models.ForeignKey(
        "ProductCategory",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    item_type = models.CharField(max_length=40)

    base_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
    )

    purchase_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        related_name="item_purchase_uom_set",
        blank=True,
        null=True,
    )

    production_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        related_name="item_production_uom_set",
        blank=True,
        null=True,
    )

    tax_class_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    net_weight = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    gross_weight = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    weight_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        related_name="item_weight_uom_set",
        blank=True,
        null=True,
    )

    length = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    width = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    height = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    dimension_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        related_name="item_dimension_uom_set",
        blank=True,
        null=True,
    )

    is_stock_item = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    metadata = models.JSONField(default=dict)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "item"
        unique_together = (("organization", "code"),)
        db_table_comment = (
            "Universal Item Master cho nguyên liệu, bao bì, "
            "bán thành phẩm, thành phẩm và dịch vụ."
        )


class Organization(models.Model):
    id = models.BigAutoField(primary_key=True)

    public_id = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        unique=True,
        max_length=100,
    )

    name = models.CharField(max_length=255)

    tax_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    country_code = models.CharField(
        max_length=2,
        blank=True,
        null=True,
    )

    timezone = models.CharField(
        max_length=100,
        default="Asia/Ho_Chi_Minh",
    )

    is_active = models.BooleanField(default=True)

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "organization"
        db_table_comment = (
            "Tổ chức/doanh nghiệp sử dụng hệ thống Costing."
        )


class OrganizationMember(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    user_id = models.UUIDField()

    role_code = models.CharField(max_length=50)

    permissions = ArrayField(
        models.TextField(),
        default=list,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "organization_member"
        unique_together = (("organization", "user_id"),)
        db_table_comment = (
            "Gán Supabase Auth user vào organization "
            "và lưu role/quyền nghiệp vụ."
        )


class PackagingConfig(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    product = models.ForeignKey(
        "Product",
        models.DO_NOTHING,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)

    description = models.TextField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "packaging_config"
        unique_together = (("organization", "code"),)


class PackagingConfigVersion(models.Model):
    id = models.BigAutoField(primary_key=True)

    packaging_config = models.ForeignKey(
        PackagingConfig,
        models.DO_NOTHING,
    )

    version_no = models.IntegerField()

    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    effective_from = models.DateField(
        blank=True,
        null=True,
    )

    effective_to = models.DateField(
        blank=True,
        null=True,
    )

    gross_weight = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    weight_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    length = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    width = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    height = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    dimension_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        related_name="packagingconfigversion_dimension_uom_set",
        blank=True,
        null=True,
    )

    content_hash = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )

    change_reason = models.TextField(
        blank=True,
        null=True,
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    approved_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    approved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "packaging_config_version"
        unique_together = (
            ("packaging_config", "version_no"),
        )


class PackagingLine(models.Model):
    id = models.BigAutoField(primary_key=True)

    packaging_config_version = models.ForeignKey(
        PackagingConfigVersion,
        models.DO_NOTHING,
    )

    packaging_item = models.ForeignKey(
        Item,
        models.DO_NOTHING,
    )

    level_code = models.CharField(max_length=30)

    qty = models.DecimalField(
        max_digits=24,
        decimal_places=8,
    )

    uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
    )

    units_per_parent = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    parent_level_code = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    market_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    artwork_code = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )

    display_order = models.IntegerField(default=0)

    notes = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "packaging_line"


class PriceScenario(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)

    base_run = models.ForeignKey(
        CostingRun,
        models.DO_NOTHING,
    )

    channel = models.ForeignKey(
        Channel,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    pricing_method = models.CharField(max_length=40)

    target_margin = models.DecimalField(
        max_digits=18,
        decimal_places=10,
        blank=True,
        null=True,
    )

    target_markup = models.DecimalField(
        max_digits=18,
        decimal_places=10,
        blank=True,
        null=True,
    )

    target_profit_per_unit = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    minimum_price = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    suggested_price = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    final_price = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    currency_code = models.ForeignKey(
        Currency,
        models.DO_NOTHING,
        db_column="currency_code",
    )

    scenario_context_jsonb = models.JSONField(default=dict)
    output_snapshot_jsonb = models.JSONField(default=dict)

    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    valid_from = models.DateField(
        blank=True,
        null=True,
    )

    valid_to = models.DateField(
        blank=True,
        null=True,
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    approved_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    approved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "price_scenario"
        unique_together = (("organization", "code"),)
        db_table_comment = (
            "Kịch bản giá bán dựa trên Costing Run immutable. "
            "Margin và Markup là hai tham số riêng."
        )


class Product(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    category = models.ForeignKey(
        "ProductCategory",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    output_item = models.ForeignKey(
        Item,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)

    description = models.TextField(
        blank=True,
        null=True,
    )

    costing_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
    )

    tax_class_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "product"
        unique_together = (("organization", "code"),)
        db_table_comment = (
            "Sản phẩm gốc. Recipe và Packaging Configuration "
            "được quản lý độc lập."
        )


class ProductCategory(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    parent = models.ForeignKey(
        "self",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)

    description = models.TextField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "product_category"
        unique_together = (("organization", "code"),)


class Recipe(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    product = models.ForeignKey(
        Product,
        models.DO_NOTHING,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)

    description = models.TextField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "recipe"
        unique_together = (("organization", "code"),)


class RecipeLine(models.Model):
    id = models.BigAutoField(primary_key=True)

    recipe_version = models.ForeignKey(
        "RecipeVersion",
        models.DO_NOTHING,
    )

    component_item = models.ForeignKey(
        Item,
        models.DO_NOTHING,
    )

    qty = models.DecimalField(
        max_digits=24,
        decimal_places=8,
    )

    uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
    )

    scrap_rate = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        default=0,
    )

    operation_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    substitute_group = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    is_optional = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)

    notes = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "recipe_line"


class RecipeVersion(models.Model):
    id = models.BigAutoField(primary_key=True)

    recipe = models.ForeignKey(
        Recipe,
        models.DO_NOTHING,
    )

    version_no = models.IntegerField()

    output_qty = models.DecimalField(
        max_digits=24,
        decimal_places=8,
    )

    output_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
    )

    yield_rate = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        default=1,
    )

    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    effective_from = models.DateField(
        blank=True,
        null=True,
    )

    effective_to = models.DateField(
        blank=True,
        null=True,
    )

    change_reason = models.TextField(
        blank=True,
        null=True,
    )

    content_hash = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    approved_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    approved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "recipe_version"
        unique_together = (("recipe", "version_no"),)
        db_table_comment = (
            "Phiên bản BOM/Recipe có hiệu lực. "
            "Approved/Effective version phải bất biến."
        )


class Resource(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    work_center = models.ForeignKey(
        "WorkCenter",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=30)

    capacity_value = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    capacity_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    metadata = models.JSONField(default=dict)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "resource"
        unique_together = (("organization", "code"),)


class ResourceRate(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    resource = models.ForeignKey(
        Resource,
        models.DO_NOTHING,
    )

    rate_type = models.CharField(max_length=50)

    amount = models.DecimalField(
        max_digits=24,
        decimal_places=8,
    )

    currency_code = models.ForeignKey(
        Currency,
        models.DO_NOTHING,
        db_column="currency_code",
    )

    per_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
    )

    effective_from = models.DateField()

    effective_to = models.DateField(
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    source_reference = models.TextField(
        blank=True,
        null=True,
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "resource_rate"


class Routing(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    product = models.ForeignKey(
        Product,
        models.DO_NOTHING,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "routing"
        unique_together = (("organization", "code"),)


class RoutingOperation(models.Model):
    id = models.BigAutoField(primary_key=True)

    routing_version = models.ForeignKey(
        "RoutingVersion",
        models.DO_NOTHING,
    )

    sequence_no = models.IntegerField()

    operation_code = models.CharField(max_length=100)
    operation_name = models.CharField(max_length=255)

    work_center = models.ForeignKey(
        "WorkCenter",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    primary_resource = models.ForeignKey(
        Resource,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    setup_time = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        default=0,
    )

    run_time = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        default=0,
    )

    time_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    quantity_basis = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    quantity_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        related_name="routingoperation_quantity_uom_set",
        blank=True,
        null=True,
    )

    notes = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "routing_operation"
        unique_together = (
            ("routing_version", "sequence_no"),
        )


class RoutingVersion(models.Model):
    id = models.BigAutoField(primary_key=True)

    routing = models.ForeignKey(
        Routing,
        models.DO_NOTHING,
    )

    version_no = models.IntegerField()

    batch_size = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    batch_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    effective_from = models.DateField(
        blank=True,
        null=True,
    )

    effective_to = models.DateField(
        blank=True,
        null=True,
    )

    content_hash = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )

    change_reason = models.TextField(
        blank=True,
        null=True,
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    approved_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    approved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "routing_version"
        unique_together = (("routing", "version_no"),)


class RuleRow(models.Model):
    id = models.BigAutoField(primary_key=True)

    rule_table_version = models.ForeignKey(
        "RuleTableVersion",
        models.DO_NOTHING,
    )

    priority = models.IntegerField(default=100)
    specificity_score = models.IntegerField(default=0)

    condition_jsonb = models.JSONField(default=dict)

    value_numeric = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    value_text = models.TextField(
        blank=True,
        null=True,
    )

    value_boolean = models.BooleanField(
        blank=True,
        null=True,
    )

    value_jsonb = models.JSONField(
        blank=True,
        null=True,
    )

    formula_version = models.ForeignKey(
        FormulaVersion,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    currency_code = models.ForeignKey(
        Currency,
        models.DO_NOTHING,
        db_column="currency_code",
        blank=True,
        null=True,
    )

    uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    row_effective_from = models.DateField(
        blank=True,
        null=True,
    )

    row_effective_to = models.DateField(
        blank=True,
        null=True,
    )

    notes = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "rule_row"
        db_table_comment = (
            "Rule row dùng condition_jsonb có kiểm soát. "
            "Resolve theo effective date, priority và specificity."
        )


class RuleTable(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    purpose = models.CharField(max_length=100)
    result_value_type = models.CharField(max_length=30)

    description = models.TextField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "rule_table"
        unique_together = (("organization", "code"),)
        db_table_comment = (
            "Bảng rule logic: fee, freight, margin floor, "
            "threshold và pricing policy."
        )


class RuleTableVersion(models.Model):
    id = models.BigAutoField(primary_key=True)

    rule_table = models.ForeignKey(
        RuleTable,
        models.DO_NOTHING,
    )

    version_no = models.IntegerField()

    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    effective_from = models.DateField(
        blank=True,
        null=True,
    )

    effective_to = models.DateField(
        blank=True,
        null=True,
    )

    change_reason = models.TextField(
        blank=True,
        null=True,
    )

    content_hash = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    approved_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    approved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "rule_table_version"
        unique_together = (
            ("rule_table", "version_no"),
        )


class Sku(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    product = models.ForeignKey(
        Product,
        models.DO_NOTHING,
    )

    sell_item = models.ForeignKey(
        Item,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    code = models.CharField(max_length=150)
    name = models.CharField(max_length=255)

    barcode = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    sales_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
    )

    net_quantity = models.DecimalField(
        max_digits=24,
        decimal_places=8,
    )

    net_quantity_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
        related_name="sku_net_quantity_uom_set",
    )

    attributes = models.JSONField(default=dict)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "sku"
        unique_together = (
            ("organization", "code"),
            ("organization", "barcode"),
        )
        db_table_comment = (
            "SKU/quy cách bán cụ thể."
        )


class SkuPackagingAssignment(models.Model):
    id = models.BigAutoField(primary_key=True)

    sku = models.ForeignKey(
        Sku,
        models.DO_NOTHING,
    )

    packaging_config = models.ForeignKey(
        PackagingConfig,
        models.DO_NOTHING,
    )

    effective_from = models.DateField()

    effective_to = models.DateField(
        blank=True,
        null=True,
    )

    is_primary = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "sku_packaging_assignment"
        unique_together = (
            (
                "sku",
                "packaging_config",
                "effective_from",
            ),
        )


class Supplier(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)

    tax_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    default_currency_code = models.ForeignKey(
        Currency,
        models.DO_NOTHING,
        db_column="default_currency_code",
        blank=True,
        null=True,
    )

    payment_terms = models.TextField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "supplier"
        unique_together = (("organization", "code"),)


class SupplierPrice(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    supplier = models.ForeignKey(
        Supplier,
        models.DO_NOTHING,
    )

    item = models.ForeignKey(
        Item,
        models.DO_NOTHING,
    )

    price_uom = models.ForeignKey(
        "Uom",
        models.DO_NOTHING,
    )

    currency_code = models.ForeignKey(
        Currency,
        models.DO_NOTHING,
        db_column="currency_code",
    )

    min_qty = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        default=0,
    )

    unit_price = models.DecimalField(
        max_digits=24,
        decimal_places=8,
    )

    tax_inclusive = models.BooleanField(default=False)

    tax_rate = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        blank=True,
        null=True,
    )

    tax_recoverable_ratio = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        default=1,
    )

    effective_from = models.DateField()

    effective_to = models.DateField(
        blank=True,
        null=True,
    )

    source_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    source_reference = models.TextField(
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "supplier_price"
        db_table_comment = (
            "Lịch sử giá mua theo supplier/item/UoM/currency, "
            "quantity break và ngày hiệu lực."
        )


class TaxRule(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    jurisdiction_code = models.CharField(max_length=80)
    tax_type = models.CharField(max_length=80)

    tax_class_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    seller_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    transaction_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    rate = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        blank=True,
        null=True,
    )

    fixed_amount = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    currency_code = models.ForeignKey(
        Currency,
        models.DO_NOTHING,
        db_column="currency_code",
        blank=True,
        null=True,
    )

    tax_base = models.CharField(max_length=100)

    recoverable_ratio = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        default=0,
    )

    inclusive = models.BooleanField(default=False)

    priority = models.IntegerField(default=100)

    effective_from = models.DateField()

    effective_to = models.DateField(
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=30,
        default="DRAFT",
    )

    source_reference = models.TextField(
        blank=True,
        null=True,
    )

    created_by = models.UUIDField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "tax_rule"


class Uom(models.Model):
    id = models.BigAutoField(primary_key=True)

    category = models.ForeignKey(
        "UomCategory",
        models.DO_NOTHING,
    )

    code = models.CharField(
        unique=True,
        max_length=50,
    )

    name = models.CharField(max_length=150)
    symbol = models.CharField(max_length=30)

    precision = models.SmallIntegerField(default=6)
    is_base = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "uom"
        db_table_comment = (
            "Đơn vị đo chuẩn của hệ thống Costing."
        )


class UomCategory(models.Model):
    id = models.BigAutoField(primary_key=True)

    code = models.CharField(
        unique=True,
        max_length=50,
    )

    name = models.CharField(max_length=150)
    dimension_code = models.CharField(max_length=50)

    description = models.TextField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "uom_category"


class UomConversion(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    from_uom = models.ForeignKey(
        Uom,
        models.DO_NOTHING,
    )

    to_uom = models.ForeignKey(
        Uom,
        models.DO_NOTHING,
        related_name="uomconversion_to_uom_set",
    )

    factor = models.DecimalField(
        max_digits=24,
        decimal_places=12,
    )

    item = models.ForeignKey(
        Item,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    effective_from = models.DateField(default=date.today)

    effective_to = models.DateField(
        blank=True,
        null=True,
    )

    source_reference = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "uom_conversion"
        db_table_comment = (
            "Quy tắc quy đổi UoM có hiệu lực; có thể "
            "cấu hình riêng theo Item."
        )


class WorkCenter(models.Model):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
    )

    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)

    site_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    capacity_value = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    capacity_uom = models.ForeignKey(
        Uom,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    normal_capacity_value = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        managed = False
        db_table = "work_center"
        unique_together = (("organization", "code"),)