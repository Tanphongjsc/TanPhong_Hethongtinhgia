from django.urls import path
from . import overhead_views as views

urlpatterns = [
    path("cost-pools/", views.cost_pool_list, name="cost_pool_list"),
    path("cost-pools/create/", views.cost_pool_create, name="cost_pool_create"),
    path("cost-pools/<int:pk>/", views.cost_pool_detail, name="cost_pool_detail"),
    path("cost-pools/<int:pk>/edit/", views.cost_pool_edit, name="cost_pool_edit"),
    path("allocation-rules/", views.allocation_rule_list, name="allocation_rule_list"),
    path("allocation-rules/create/", views.allocation_rule_create, name="allocation_rule_create"),
    path("allocation-rules/<int:pk>/", views.allocation_rule_detail, name="allocation_rule_detail"),
    path("allocation-rules/<int:pk>/edit/", views.allocation_rule_edit, name="allocation_rule_edit"),
]
