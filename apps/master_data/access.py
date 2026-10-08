"""Central internal policy; no user, authentication, session or membership."""
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied

from apps.core.models import Organization
from .company_context import ConfigurationError, get_default_organization


@dataclass(frozen=True)
class InternalAccess:
    can_view_scenario: bool = True
    can_create_scenario: bool = True
    can_edit_scenario: bool = True
    can_view_channel: bool = True
    can_create_channel: bool = True
    can_edit_channel: bool = True
    can_view_channel_fee_rule: bool = True
    can_create_channel_fee_rule: bool = True
    can_edit_channel_fee_rule: bool = True
    can_view_tax_rule: bool = True
    can_create_tax_rule: bool = True
    can_edit_tax_rule: bool = True
    can_view_fx_rate: bool = True
    can_create_fx_rate: bool = True
    can_edit_fx_rate: bool = True
    can_view_run: bool = True
    can_create_run: bool = True
    can_view_scheme: bool = True
    can_create_scheme: bool = True
    can_edit_scheme: bool = True
    can_view_scheme_version: bool = True
    can_create_scheme_version: bool = True
    can_edit_scheme_version: bool = True
    can_view_scheme_line: bool = True
    can_create_scheme_line: bool = True
    can_edit_scheme_line: bool = True
    can_delete_scheme_line: bool = True
    can_view_formula: bool = True
    can_create_formula: bool = True
    can_edit_formula: bool = True
    can_view_formula_version: bool = True
    can_create_formula_version: bool = True
    can_edit_formula_version: bool = True
    can_view_formula_test: bool = True
    can_create_formula_test: bool = True
    can_edit_formula_test: bool = True
    can_view_cost_pool: bool = True
    can_create_cost_pool: bool = True
    can_edit_cost_pool: bool = True
    can_view_allocation_rule: bool = True
    can_create_allocation_rule: bool = True
    can_edit_allocation_rule: bool = True
    can_view_routing: bool = True
    can_create_routing: bool = True
    can_edit_routing: bool = True
    can_view_routing_version: bool = True
    can_create_routing_version: bool = True
    can_edit_routing_version: bool = True
    can_view_routing_operation: bool = True
    can_create_routing_operation: bool = True
    can_edit_routing_operation: bool = True
    can_delete_routing_operation: bool = True
    can_view_work_center: bool = True
    can_create_work_center: bool = True
    can_edit_work_center: bool = True
    can_view_resource: bool = True
    can_create_resource: bool = True
    can_edit_resource: bool = True
    can_view_resource_rate: bool = True
    can_create_resource_rate: bool = True
    can_edit_resource_rate: bool = True
    can_view_cost_element: bool = True
    can_create_cost_element: bool = True
    can_edit_cost_element: bool = True
    can_view_sensitive_cost_element: bool = True
    can_manage_sensitive_cost_element: bool = True
    can_view_currency: bool = True
    can_create_currency: bool = True
    can_edit_currency: bool = True
    can_view_uom_category: bool = True
    can_create_uom_category: bool = True
    can_edit_uom_category: bool = True
    can_view_uom: bool = True
    can_create_uom: bool = True
    can_edit_uom: bool = True
    can_view_uom_conversion: bool = True
    can_create_uom_conversion: bool = True
    can_edit_uom_conversion: bool = True
    can_view_product_category: bool = True
    can_create_product_category: bool = True
    can_edit_product_category: bool = True
    can_view_item: bool = True
    can_create_item: bool = True
    can_edit_item: bool = True
    can_view_product: bool = True
    can_create_product: bool = True
    can_edit_product: bool = True
    can_view_sku: bool = True
    can_create_sku: bool = True
    can_edit_sku: bool = True
    can_view_supplier: bool = True
    can_create_supplier: bool = True
    can_edit_supplier: bool = True
    can_view_supplier_price: bool = True
    can_create_supplier_price: bool = True
    can_edit_supplier_price: bool = True
    can_view_bom: bool = True
    can_create_bom: bool = True
    can_edit_bom: bool = True
    can_view_bom_version: bool = True
    can_create_bom_version: bool = True
    can_edit_bom_version: bool = True
    can_view_bom_line: bool = True
    can_create_bom_line: bool = True
    can_edit_bom_line: bool = True
    can_delete_bom_line: bool = True
    can_view_packaging: bool = True
    can_create_packaging: bool = True
    can_edit_packaging: bool = True
    can_view_packaging_version: bool = True
    can_create_packaging_version: bool = True
    can_edit_packaging_version: bool = True
    can_view_packaging_line: bool = True
    can_create_packaging_line: bool = True
    can_edit_packaging_line: bool = True
    can_delete_packaging_line: bool = True
    can_view_packaging_assignment: bool = True
    can_create_packaging_assignment: bool = True
    can_edit_packaging_assignment: bool = True


INTERNAL_ACCESS = InternalAccess()


@dataclass(frozen=True)
class Workspace:
    organization: Organization | None
    permissions: InternalAccess = INTERNAL_ACCESS


def get_workspace(request):
    if not hasattr(request, "_costing_workspace"):
        request._costing_workspace = Workspace(get_default_organization())
    return request._costing_workspace


def require_access(request, action="view", *, resource="cost_element"):
    workspace = get_workspace(request)
    if workspace.organization is None:
        raise ConfigurationError("Chưa cấu hình công ty cho hệ thống.")
    if not getattr(workspace.permissions, f"can_{action}_{resource}", False):
        raise PermissionDenied("Thao tác này chưa được hệ thống hỗ trợ.")
    return workspace


def require_write_access(workspace, *, resource, editing=False):
    if workspace.organization is None:
        raise ConfigurationError("Chưa cấu hình công ty cho hệ thống.")
    action = "edit" if editing else "create"
    if not getattr(workspace.permissions, f"can_{action}_{resource}", False):
        raise PermissionDenied("Thao tác này chưa được hệ thống hỗ trợ.")
