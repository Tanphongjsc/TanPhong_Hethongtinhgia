from django.urls import path

from . import views

app_name = "master_data"
urlpatterns = [
    path("suppliers/", views.supplier_list, name="supplier_list"),
    path("suppliers/create/", views.supplier_create, name="supplier_create"),
    path("suppliers/<int:pk>/", views.supplier_detail, name="supplier_detail"),
    path("suppliers/<int:pk>/edit/", views.supplier_edit, name="supplier_edit"),
    path("supplier-prices/", views.supplier_price_list, name="supplier_price_list"),
    path("supplier-prices/create/", views.supplier_price_create, name="supplier_price_create"),
    path("supplier-prices/<int:pk>/", views.supplier_price_detail, name="supplier_price_detail"),
    path("supplier-prices/<int:pk>/edit/", views.supplier_price_edit, name="supplier_price_edit"),
    path("cost-elements/", views.cost_element_list, name="cost_element_list"),
    path("cost-elements/create/", views.cost_element_create, name="cost_element_create"),
    path("cost-elements/<int:pk>/", views.cost_element_detail, name="cost_element_detail"),
    path("cost-elements/<int:pk>/edit/", views.cost_element_edit, name="cost_element_edit"),
    path("currencies/", views.currency_list, name="currency_list"),
    path("currencies/create/", views.currency_create, name="currency_create"),
    path("currencies/<path:code>/edit/", views.currency_edit, name="currency_edit"),
    path("currencies/<path:code>/", views.currency_detail, name="currency_detail"),
    path("uom-categories/", views.uom_category_list, name="uom_category_list"),
    path("uom-categories/create/", views.uom_category_create, name="uom_category_create"),
    path("uom-categories/<int:pk>/", views.uom_category_detail, name="uom_category_detail"),
    path("uom-categories/<int:pk>/edit/", views.uom_category_edit, name="uom_category_edit"),
    path("uoms/", views.uom_list, name="uom_list"),
    path("uoms/create/", views.uom_create, name="uom_create"),
    path("uoms/<int:pk>/", views.uom_detail, name="uom_detail"),
    path("uoms/<int:pk>/edit/", views.uom_edit, name="uom_edit"),
    path("uom-conversions/", views.uom_conversion_list, name="uom_conversion_list"),
    path("uom-conversions/create/", views.uom_conversion_create, name="uom_conversion_create"),
    path("uom-conversions/<int:pk>/", views.uom_conversion_detail, name="uom_conversion_detail"),
    path("uom-conversions/<int:pk>/edit/", views.uom_conversion_edit, name="uom_conversion_edit"),
]
