from django.urls import path
from . import views

app_name = "formula_engine"
urlpatterns = [
    path("formulas/", views.formula_list, name="formula_list"),
    path("formulas/create/", views.formula_create, name="formula_create"),
    path("catalogue/", views.formula_catalogue, name="formula_catalogue"),
    path("formulas/<int:pk>/", views.formula_detail, name="formula_detail"),
    path("formulas/<int:pk>/edit/", views.formula_edit, name="formula_edit"),
    path("formulas/<int:pk>/test/", views.formula_test, name="formula_test"),
    path("formulas/<int:pk>/tests/<int:case_id>/deactivate/", views.formula_test_deactivate, name="formula_test_deactivate"),
    path("formulas/<int:pk>/versions/", views.formula_version_list, name="formula_version_list"),
    path("formulas/<int:pk>/versions/create/", views.formula_version_create, name="formula_version_create"),
    path("formulas/<int:pk>/versions/<int:version_id>/", views.formula_version_detail, name="formula_version_detail"),
    path("formulas/<int:pk>/versions/<int:version_id>/edit/", views.formula_version_edit, name="formula_version_edit"),
    path("formulas/<int:pk>/versions/<int:version_id>/activate/", views.formula_version_activate, name="formula_version_activate"),
]
