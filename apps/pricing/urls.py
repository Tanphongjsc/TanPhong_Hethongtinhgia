from django.urls import path
from . import views, scenario_views, comparison_views

app_name = "pricing"
urlpatterns = [
    path("scenarios/compare/", comparison_views.scenario_compare, name="scenario_compare"),
    path("scenarios/", scenario_views.scenario_list, name="scenario_list"),
    path("scenarios/create/", scenario_views.scenario_form, name="scenario_create"),
    path("scenarios/options/", scenario_views.scenario_options, name="scenario_options"),
    path("scenarios/<int:pk>/", scenario_views.scenario_detail, name="scenario_detail"),
    path("scenarios/<int:pk>/edit/", scenario_views.scenario_form, name="scenario_edit"),
    path("scenarios/<int:pk>/calculate/", scenario_views.scenario_calculate, name="scenario_calculate"),
]
# Same four endpoints per implemented catalog; no dynamic model discovery.
for slug, resource in (("channels", "channel"), ("channel-fee-rules", "channel_fee_rule"), ("tax-rules", "tax_rule"), ("fx-rates", "fx_rate")):
    urlpatterns.extend((
        path(f"{slug}/", views.list_view, {"resource": resource}, name=f"{resource}_list"),
        path(f"{slug}/create/", views.form_view, {"resource": resource}, name=f"{resource}_create"),
        path(f"{slug}/<int:pk>/", views.detail_view, {"resource": resource}, name=f"{resource}_detail"),
        path(f"{slug}/<int:pk>/edit/", views.form_view, {"resource": resource}, name=f"{resource}_edit"),
    ))
    if resource != "channel":
        urlpatterns.append(path(f"{slug}/<int:pk>/close/", views.close_view, {"resource": resource}, name=f"{resource}_close"))
