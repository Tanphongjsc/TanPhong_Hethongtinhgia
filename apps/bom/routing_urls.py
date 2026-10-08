from django.urls import path
from . import routing_views as views

urlpatterns = [
    path("routings/", views.routing_list, name="routing_list"),
    path("routings/create/", views.routing_create, name="routing_create"),
    path("routings/<int:pk>/", views.routing_detail, name="routing_detail"),
    path("routings/<int:pk>/edit/", views.routing_edit, name="routing_edit"),
    path("routings/<int:pk>/versions/", views.routing_version_list, name="routing_version_list"),
    path("routings/<int:pk>/versions/create/", views.routing_version_create, name="routing_version_create"),
    path("routings/<int:pk>/versions/<int:version_pk>/", views.routing_version_detail, name="routing_version_detail"),
    path("routings/<int:pk>/versions/<int:version_pk>/edit/", views.routing_version_edit, name="routing_version_edit"),
    path("routings/<int:pk>/versions/<int:version_pk>/operations/resources/", views.routing_operation_resources, name="routing_operation_resources"),
    path("routings/<int:pk>/versions/<int:version_pk>/operations/create/", views.routing_operation_create, name="routing_operation_create"),
    path("routings/<int:pk>/versions/<int:version_pk>/operations/<int:operation_pk>/edit/", views.routing_operation_edit, name="routing_operation_edit"),
    path("routings/<int:pk>/versions/<int:version_pk>/operations/<int:operation_pk>/remove/", views.routing_operation_remove, name="routing_operation_remove"),
]
