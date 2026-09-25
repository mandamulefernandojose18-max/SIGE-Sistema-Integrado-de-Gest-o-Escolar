from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CertificadoViewSet, VerificarCertificadoView

router = DefaultRouter()
router.register(r'', CertificadoViewSet, basename='certificados')

urlpatterns = [
    path('verificar/<str:codigo>', VerificarCertificadoView.as_view(), name='verificar_certificado_no_slash'),
    path('verificar/<str:codigo>/', VerificarCertificadoView.as_view(), name='verificar_certificado'),
    path('', include(router.urls)),
]
