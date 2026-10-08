from django.urls import path
from . import views
from . import run_views
app_name = "costing"
urlpatterns = [
    path("runs/", run_views.run_list, name="run_list"),
    path("runs/create/", run_views.run_create, name="run_create"),
    path("runs/options/", run_views.run_options, name="run_options"),
    path("runs/<uuid:public_id>/", run_views.run_detail, name="run_detail"),
    path("runs/<uuid:public_id>/rerun/", run_views.run_rerun, name="run_rerun"),
    path("runs/<uuid:public_id>/snapshot/", run_views.run_snapshot, name="run_snapshot"),
    path("runs/<uuid:public_id>/lines/<int:line_pk>/trace/", run_views.run_trace, name="run_trace"),
    path("schemes/", views.scheme_list, name="scheme_list"),
    path("schemes/create/", views.scheme_create, name="scheme_create"),
    path("schemes/<int:pk>/", views.scheme_detail, name="scheme_detail"),
    path("schemes/<int:pk>/edit/", views.scheme_edit, name="scheme_edit"),
    path("schemes/<int:pk>/versions/", views.scheme_version_list, name="scheme_version_list"),
    path("schemes/<int:pk>/versions/create/", views.scheme_version_create, name="scheme_version_create"),
    path("schemes/<int:pk>/versions/<int:version_pk>/", views.scheme_version_detail, name="scheme_version_detail"),
    path("schemes/<int:pk>/versions/<int:version_pk>/edit/", views.scheme_version_edit, name="scheme_version_edit"),
    path("schemes/<int:pk>/versions/<int:version_pk>/validate/", views.scheme_version_validate, name="scheme_version_validate"),
    path("schemes/<int:pk>/versions/<int:version_pk>/activate/", views.scheme_version_activate, name="scheme_version_activate"),
    path("schemes/<int:pk>/versions/<int:version_pk>/lines/create/", views.scheme_line_create, name="scheme_line_create"),
    path("schemes/<int:pk>/versions/<int:version_pk>/lines/sources/", views.scheme_line_sources, name="scheme_line_sources"),
    path("schemes/<int:pk>/versions/<int:version_pk>/lines/<int:line_pk>/edit/", views.scheme_line_edit, name="scheme_line_edit"),
    path("schemes/<int:pk>/versions/<int:version_pk>/lines/<int:line_pk>/remove/", views.scheme_line_remove, name="scheme_line_remove"),
]
