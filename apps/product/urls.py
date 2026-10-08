from django.urls import path
from . import views

app_name = "product"
urlpatterns = [
    path("categories/", views.category_list, name="category_list"),
    path("categories/create/", views.category_create, name="category_create"),
    path("categories/<int:pk>/", views.category_detail, name="category_detail"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("items/", views.item_list, name="item_list"),
    path("items/create/", views.item_create, name="item_create"),
    path("items/<int:pk>/", views.item_detail, name="item_detail"),
    path("items/<int:pk>/edit/", views.item_edit, name="item_edit"),
    path("products/", views.product_list, name="product_list"),
    path("products/create/", views.product_create, name="product_create"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("skus/", views.sku_list, name="sku_list"),
    path("skus/create/", views.sku_create, name="sku_create"),
    path("skus/<int:pk>/", views.sku_detail, name="sku_detail"),
    path("skus/<int:pk>/edit/", views.sku_edit, name="sku_edit"),
]
