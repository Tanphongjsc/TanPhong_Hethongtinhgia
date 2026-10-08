from django.urls import path
from . import views
from .packaging_urls import urlpatterns as packaging_patterns
from .resource_urls import urlpatterns as resource_patterns
from .routing_urls import urlpatterns as routing_patterns
from .overhead_urls import urlpatterns as overhead_patterns

app_name = "bom"
urlpatterns = [
    path("", views.bom_list, name="bom_list"),
    path("create/", views.bom_create, name="bom_create"),
    path("<int:pk>/", views.bom_detail, name="bom_detail"),
    path("<int:pk>/edit/", views.bom_edit, name="bom_edit"),
    path("<int:pk>/versions/", views.bom_version_list, name="bom_version_list"),
    path("<int:pk>/versions/create/", views.bom_version_create, name="bom_version_create"),
    path("<int:pk>/versions/<int:version_pk>/", views.bom_version_detail, name="bom_version_detail"),
    path("<int:pk>/versions/<int:version_pk>/edit/", views.bom_version_edit, name="bom_version_edit"),
    path("<int:pk>/versions/<int:version_pk>/lines/create/", views.bom_line_create, name="bom_line_create"),
    path("<int:pk>/versions/<int:version_pk>/lines/<int:line_pk>/edit/", views.bom_line_edit, name="bom_line_edit"),
    path("<int:pk>/versions/<int:version_pk>/lines/<int:line_pk>/remove/", views.bom_line_remove, name="bom_line_remove"),
] + packaging_patterns + resource_patterns + routing_patterns + overhead_patterns
