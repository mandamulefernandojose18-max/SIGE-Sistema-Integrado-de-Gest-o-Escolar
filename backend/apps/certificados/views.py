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
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(self.request)
        if escola:
            qs = Certificado.objects.filter(escola=escola)
        else:
            qs = Certificado.objects.none()
        return qs.select_related('aluno', 'escola').order_by('-emitido_em')

    def perform_create(self, serializer):
        from common.utils.tenant import get_tenant_escola
        from rest_framework import serializers as drf_serializers
        aluno = serializer.validated_data.get('aluno')
        escola = get_tenant_escola(self.request) or (getattr(aluno, 'escola', None) if aluno else None)
        if not escola:
            raise drf_serializers.ValidationError({'escola': 'Nenhuma instituição identificada para emissão do certificado.'})
        if aluno and aluno.escola_id != escola.id:
            raise drf_serializers.ValidationError({'aluno': 'O aluno selecionado pertence a uma escola diferente da ativa.'})

        codigo = f"CERT-{uuid.uuid4().hex[:10].upper()}"
        domain_base = os.environ.get('SIGE_PUBLIC_URL', 'https://sigesaas.duckdns.org').rstrip('/')
        origin = self.request.META.get('HTTP_ORIGIN')
        if not origin or 'localhost' in origin or '127.0.0.1' in origin:
            origin = domain_base
        else:
            origin = origin.rstrip('/')
        qr_url = f"{origin}/verificar-certificado.html?codigo={codigo}"
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




def _nome_abreviado(aluno):
    """Primeiro nome por extenso e iniciais dos restantes (a página pública não expõe o nome completo)."""
    partes = f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".split()
    if not partes:
        return ''
    return partes[0] + ''.join(f' {p[0].upper()}.' for p in partes[1:])


def _matricula_mascarada(matricula):
    m = (matricula or '').strip()
    return ('••••' + m[-3:]) if len(m) > 3 else '••••'


class VerificarCertificadoView(APIView):
    """Verificação pública (QR do certificado).

    Só aceita um código EXISTENTE em `Certificado` (correspondência exacta) e devolve dados mínimos:
    escola, tipo, data, nome abreviado e matrícula mascarada. Nunca devolve BI/documento nem notas,
    nunca "adivinha" o aluno a partir do código e nunca inventa valores em falta.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'verificacao'

    def get(self, request, codigo):
        codigo_limpo = (codigo or '').strip()
        cert = None
        if codigo_limpo:
            cert = (Certificado.objects.filter(codigo_autenticidade__iexact=codigo_limpo)
                    .select_related('aluno', 'aluno__turma', 'escola').first())

        if not cert or not cert.aluno:
            return Response({
                'success': False,
                'autentico': False,
                'data': {
                    'autentico': False,
                    'mensagem': 'O código informado não corresponde a nenhum certificado emitido no sistema.'
                },
                'message': 'Documento não encontrado ou código de autenticidade inválido.'
            }, status=status.HTTP_404_NOT_FOUND)

        aluno, escola = cert.aluno, cert.escola
        turma = getattr(aluno, 'turma', None)
        grau_ano = (turma.grau_ano if turma and turma.grau_ano else getattr(aluno, 'classe', None)) or ''
        area = (turma.area if turma and turma.area else getattr(aluno, 'area', None)) or ''
        payload = {
            'autentico': True,
            'codigo': cert.codigo_autenticidade,
            'tipo': cert.tipo,
            'emitido_em': cert.emitido_em,
            'emitido_por': cert.emitido_por or '',
            'grau_ano': grau_ano,
            'area': area,
            'aluno': {
                'nome': _nome_abreviado(aluno),
                'matricula': _matricula_mascarada(aluno.matricula),
                'classe': grau_ano,
                'area': area,
            },
            'escola': {
                'nome': escola.nome if escola else '',
                'nif_cnpj': (getattr(escola, 'nuit', None) or getattr(escola, 'nif_cnpj', None) or '') if escola else '',
                'provincia': (getattr(escola, 'provincia', '') or '') if escola else '',
                'distrito': (getattr(escola, 'distrito', '') or '') if escola else '',
            },
        }
        return Response({'success': True, 'autentico': True, 'data': {**payload, 'certificado': payload}})
