from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import CertificadoViewSet, VerificarCertificadoView

router = OptionalSlashRouter()
router.register(r'', CertificadoViewSet, basename='certificados')

urlpatterns = [
    path('verificar/<str:codigo>', VerificarCertificadoView.as_view(), name='verificar_certificado_no_slash'),
    path('verificar/<str:codigo>/', VerificarCertificadoView.as_view(), name='verificar_certificado'),
    path('', include(router.urls)),
]
