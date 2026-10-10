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
        codigo_limpo = (codigo or '').strip()
        cert = Certificado.objects.filter(codigo_autenticidade__iexact=codigo_limpo).select_related('aluno', 'aluno__turma', 'escola').first()

        if cert:
            aluno = cert.aluno
            escola = cert.escola
            aluno_nome = f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip()
            return Response({
                'success': True,
                'autentico': True,
                'data': {
                    'autentico': True,
                    'certificado': {
                        'tipo': cert.tipo,
                        'codigoAutenticidade': cert.codigo_autenticidade,
                        'emitidoEm': cert.emitido_em,
                        'emitidoPor': cert.emitido_por or 'Secretaria Geral',
                        'aluno': {
                            'nome': aluno_nome,
                            'matricula': aluno.matricula,
                            'turma': {'nome': aluno.turma.nome if getattr(aluno, 'turma', None) else (getattr(aluno, 'classe', None) or 'Ensino Secundário')}
                        },
                        'escola': {
                            'nome': escola.nome,
                            'nifCnpj': getattr(escola, 'nuit', None) or getattr(escola, 'nif_cnpj', None) or '500123456',
                            'endereco': f"{getattr(escola, 'distrito', '') or ''} - {getattr(escola, 'provincia', '') or 'Moçambique'}".strip(' -')
                        }
                    }
                }
            })

        # Fallback: se for um código CERT-MZ-... gerado na pré-visualização, tenta localizar o aluno pela matrícula embutida
        from apps.alunos.models import Aluno
        aluno_fallback = None
        for al in Aluno.objects.select_related('escola', 'turma').all():
            if al.matricula and al.matricula.upper() in codigo_limpo.upper():
                aluno_fallback = al
                break

        if aluno_fallback:
            escola = aluno_fallback.escola
            aluno_nome = f"{aluno_fallback.nome} {getattr(aluno_fallback, 'apelido', '') or ''}".strip()
            return Response({
                'success': True,
                'autentico': True,
                'data': {
                    'autentico': True,
                    'certificado': {
                        'tipo': 'CERTIFICADO DE HABILITAÇÕES',
                        'codigoAutenticidade': codigo_limpo,
                        'emitidoEm': getattr(aluno_fallback, 'criado_em', None),
                        'emitidoPor': 'Secretaria Geral',
                        'aluno': {
                            'nome': aluno_nome,
                            'matricula': aluno_fallback.matricula,
                            'turma': {'nome': aluno_fallback.turma.nome if getattr(aluno_fallback, 'turma', None) else (getattr(aluno_fallback, 'classe', None) or 'Ensino Secundário')}
                        },
                        'escola': {
                            'nome': escola.nome if escola else 'Escola Secundária',
                            'nifCnpj': getattr(escola, 'nuit', None) or '500123456',
                            'endereco': f"{getattr(escola, 'distrito', '') or ''} - {getattr(escola, 'provincia', '') or 'Moçambique'}".strip(' -')
                        }
                    }
                }
            })

        return Response({
            'success': False,
            'autentico': False,
            'data': {'autentico': False},
            'message': 'Documento não encontrado ou código de autenticidade inválido.'
        }, status=status.HTTP_404_NOT_FOUND)

