from django.urls import path
from . import resource_views as views

urlpatterns = [
    path("work-centers/", views.work_center_list, name="work_center_list"),
    path("work-centers/create/", views.work_center_create, name="work_center_create"),
    path("work-centers/<int:pk>/", views.work_center_detail, name="work_center_detail"),
    path("work-centers/<int:pk>/edit/", views.work_center_edit, name="work_center_edit"),
    path("resources/", views.resource_list, name="resource_list"),
    path("resources/create/", views.resource_create, name="resource_create"),
    path("resources/<int:pk>/", views.resource_detail, name="resource_detail"),
    path("resources/<int:pk>/edit/", views.resource_edit, name="resource_edit"),
    path("resource-rates/", views.resource_rate_list, name="resource_rate_list"),
    path("resource-rates/create/", views.resource_rate_create, name="resource_rate_create"),
    path("resource-rates/<int:pk>/", views.resource_rate_detail, name="resource_rate_detail"),
    path("resource-rates/<int:pk>/edit/", views.resource_rate_edit, name="resource_rate_edit"),
]
