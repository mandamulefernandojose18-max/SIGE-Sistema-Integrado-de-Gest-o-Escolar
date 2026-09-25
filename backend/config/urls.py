from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'service': 'SIGE — Sistema Integrado de Gestão Escolar (Django REST Framework SaaS)'
    })

api_v1_patterns = [
    path('auth/', include('apps.accounts.urls')),
    path('', include('apps.tenants.urls')),
    path('escola-admin/turmas/', include('apps.turmas.urls')),
    path('turmas/', include('apps.turmas.urls')),
    path('alunos/', include('apps.alunos.urls')),
    path('professores/', include('apps.professores.urls')),
    path('disciplinas/', include('apps.disciplinas.urls')),
    path('notas/', include('apps.notas.urls')),
    path('pautas/', include('apps.pautas.urls')),
    path('material-escolar/', include('apps.material_escolar.urls')),
    path('pagamentos/', include('apps.pagamentos.urls')),
    path('certificados/', include('apps.certificados.urls')),
    path('impressao/', include('apps.documentos.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health', health_check, name='health_no_slash'),
    path('health/', health_check, name='health'),

    # API Versionada /api/v1/
    path('api/v1/', include(api_v1_patterns)),

    # OpenAPI Schema & Swagger UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
