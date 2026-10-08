from apps.core.models import CostingSchemeVersion
from .common import dated, one


def resolve_scheme(ctx, scheme_id):
    query = CostingSchemeVersion.objects.filter(scheme_id=scheme_id, scheme__organization=ctx.organization, scheme__is_active=True, status="EFFECTIVE").select_related("scheme")
    version = one(dated(query, ctx.day), "phiên bản phương án")
    ctx.remember(version.scheme, version)
    return version
