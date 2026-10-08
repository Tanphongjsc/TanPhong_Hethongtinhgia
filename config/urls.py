"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path
from django.views.generic import RedirectView
from .health import health, ready

urlpatterns = [
    path('health/', health, name='health'),
    path('ready/', ready, name='ready'),
    path('', RedirectView.as_view(pattern_name='master_data:cost_element_list', permanent=False)),
    path('master-data/', include('apps.master_data.urls')),
    path('product/', include('apps.product.urls')),
    path('bom/', include('apps.bom.urls')),
    path('formula-engine/', include('apps.formula_engine.urls')),
    path('costing/', include('apps.costing.urls')),
    path('pricing/', include('apps.pricing.urls')),
]

handler400 = 'apps.master_data.errors.bad_request'
handler403 = 'apps.master_data.errors.permission_denied'
handler404 = 'apps.master_data.errors.not_found'
handler500 = 'apps.master_data.errors.server_error'
