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
        escola = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'escola', None)
        is_super = getattr(self.request.user, 'role', '') == 'SUPERADMIN'
        if escola and not is_super:
            qs = Certificado.objects.filter(escola=escola)
        else:
            qs = Certificado.objects.all()
        return qs.select_related('aluno', 'escola').order_by('-emitido_em')

    def perform_create(self, serializer):
        aluno = serializer.validated_data.get('aluno')
        escola = (getattr(aluno, 'escola', None) if aluno else None) or getattr(self.request, 'tenant', None) or getattr(self.request.user, 'escola', None)
        codigo = f"CERT-{uuid.uuid4().hex[:10].upper()}"
        qr_url = f"https://sige.co.mz/verificar-certificado.html?codigo={codigo}"
        serializer.save(
            escola=escola,
            codigo_autenticidade=codigo,
            qrcode_data=qr_url,
            emitido_por=getattr(self.request.user, 'nome', None) or 'Secretaria'
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'success': True, 'data': serializer.data}, status=status.HTTP_201_CREATED)

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
