from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
import json

from .errors import CostingError


def json_data(value):
    """Stable, lossless JSON. Never serialize a financial Decimal as float."""
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, (date, datetime)): return value.isoformat()
    if isinstance(value, dict): return {str(key): json_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)): return [json_data(item) for item in value]
    if value is None or type(value) in (str, bool, int): return value
    raise CostingError("Dữ liệu đầu vào không có định dạng được hỗ trợ.")


def digest(value):
    return sha256(json.dumps(json_data(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


@dataclass
class ExecutionContext:
    organization: object
    product: object
    sku: object
    day: date
    quantity: Decimal
    uom: object
    currency: object
    manual: dict = field(default_factory=dict)
    packaging_quantity: Decimal | None = None
    packaging_uom: object = None
    sources: dict = field(default_factory=dict)
    cache: dict = field(default_factory=dict)

    def remember(self, *records):
        for record in records:
            if record is None: continue
            key = f"{record._meta.db_table}:{record.pk}"
            if key in self.sources: continue
            values = {}
            for field in record._meta.concrete_fields:
                # Business snapshot needs typed scalar fields, not unrelated raw
                # metadata, executable configuration or identity information.
                if field.get_internal_type() in ("JSONField", "UUIDField"): continue
                values[field.attname] = getattr(record, field.attname)
            self.sources[key] = json_data({"table": record._meta.db_table, "id": record.pk, "fields": values})


@dataclass(frozen=True)
class ResolvedValue:
    value: object
    steps: tuple = ()
    warnings: tuple = ()


def step(title, **fields):
    return {"title": title, "fields": list(fields.items())}
