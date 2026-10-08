from django.urls import path
from . import packaging_views as views

urlpatterns = [
    path("packaging/", views.packaging_list, name="packaging_list"),
    path("packaging/create/", views.packaging_create, name="packaging_create"),
    path("packaging/<int:pk>/", views.packaging_detail, name="packaging_detail"),
    path("packaging/<int:pk>/edit/", views.packaging_edit, name="packaging_edit"),
    path("packaging/<int:pk>/versions/", views.packaging_version_list, name="packaging_version_list"),
    path("packaging/<int:pk>/versions/create/", views.packaging_version_create, name="packaging_version_create"),
    path("packaging/<int:pk>/versions/<int:version_pk>/", views.packaging_version_detail, name="packaging_version_detail"),
    path("packaging/<int:pk>/versions/<int:version_pk>/edit/", views.packaging_version_edit, name="packaging_version_edit"),
    path("packaging/<int:pk>/versions/<int:version_pk>/lines/create/", views.packaging_line_create, name="packaging_line_create"),
    path("packaging/<int:pk>/versions/<int:version_pk>/lines/<int:line_pk>/edit/", views.packaging_line_edit, name="packaging_line_edit"),
    path("packaging/<int:pk>/versions/<int:version_pk>/lines/<int:line_pk>/remove/", views.packaging_line_remove, name="packaging_line_remove"),
    path("packaging/<int:pk>/skus/", views.packaging_assignment_list, name="packaging_assignment_list"),
    path("packaging/<int:pk>/skus/create/", views.packaging_assignment_create, name="packaging_assignment_create"),
    path("packaging/<int:pk>/skus/<int:assignment_pk>/edit/", views.packaging_assignment_edit, name="packaging_assignment_edit"),
]
