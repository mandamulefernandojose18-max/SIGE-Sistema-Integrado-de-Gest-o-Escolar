import uuid
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Certificado
from .serializers import CertificadoSerializer

class CertificadoViewSet(viewsets.ModelViewSet):
    serializer_class = CertificadoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        escola = self.request.tenant or self.request.user.escola
        return Certificado.objects.filter(escola=escola).select_related('aluno', 'escola').order_by('-emitido_em')

    def perform_create(self, serializer):
        escola = self.request.tenant or self.request.user.escola
        codigo = f"CERT-{uuid.uuid4().hex[:10].upper()}"
        qr_url = f"https://sige.co.mz/verificar-certificado.html?codigo={codigo}"
        serializer.save(
            escola=escola,
            codigo_autenticidade=codigo,
            qrcode_data=qr_url,
            emitido_por=self.request.user.nome if self.request.user else 'Secretaria'
        )

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': CertificadoSerializer(qs, many=True).data})

class VerificarCertificadoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, codigo):
        cert = Certificado.objects.filter(codigo_autenticidade=codigo).select_related('aluno', 'escola').first()
        if not cert:
            return Response({
                'success': False,
                'autentico': False,
                'message': 'Documento não encontrado ou código de autenticidade inválido.'
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'success': True,
            'autentico': True,
            'data': {
                'tipo': cert.tipo,
                'codigo': cert.codigo_autenticidade,
                'aluno': cert.aluno.nome,
                'matricula': cert.aluno.matricula,
                'escola': cert.escola.nome,
                'emitido_em': cert.emitido_em,
                'emitido_por': cert.emitido_por
            }
        })
