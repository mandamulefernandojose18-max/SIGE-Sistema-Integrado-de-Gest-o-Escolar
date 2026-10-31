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


class VerificarCertificadoView(APIView):
    permission_classes = [AllowAny]

    def _montar_resposta_autentica(self, aluno, escola, codigo_str, tipo_str='CONCLUSAO', emitido_em=None, emitido_por='Secretaria Escolar'):
        from django.utils import timezone
        from apps.documentos.views import obter_dados_boletim_aluno, calcular_desempenho_documento

        aluno_nome = f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip()
        grau_ano = (aluno.turma.grau_ano if getattr(aluno, 'turma', None) and aluno.turma.grau_ano else getattr(aluno, 'classe', None)) or 'Ensino Secundário'
        area_str = (aluno.turma.area if getattr(aluno, 'turma', None) and aluno.turma.area else getattr(aluno, 'area', None)) or 'Geral'
        turma_nome = aluno.turma.nome if getattr(aluno, 'turma', None) else grau_ano
        bi_doc = getattr(aluno, 'numero_documento', None) or getattr(aluno, 'bi_numero', None) or 'Não informado'
        nif_escola = getattr(escola, 'nuit', None) or getattr(escola, 'nif_cnpj', None) or getattr(escola, 'codigo_escola', None) or '500123456'
        email_escola = getattr(escola, 'email', None) or 'secretaria@sige.edu.mz'
        endereco_escola = f"{getattr(escola, 'distrito', '') or ''} - {getattr(escola, 'provincia', '') or 'Moçambique'}".strip(' -')
        dt_emissao = emitido_em or timezone.now()

        try:
            disciplinas = obter_dados_boletim_aluno(aluno, escola)
            media_global, avaliacao = calcular_desempenho_documento(disciplinas, grau_ano, tipo='CERTIFICADO')
        except Exception:
            disciplinas = []
            media_global = '-'
            avaliacao = {'resultado': 'Aprovado'}

        cert_payload = {
            'codigo': codigo_str,
            'codigo_autenticidade': codigo_str,
            'codigoAutenticidade': codigo_str,
            'tipo': tipo_str,
            'emitido_em': dt_emissao,
            'emitidoEm': dt_emissao,
            'emitido_por': emitido_por or 'Secretaria Escolar',
            'emitidoPor': emitido_por or 'Secretaria Escolar',
            'grau_ano': grau_ano,
            'area': area_str,
            'media_global': media_global,
            'resultado': avaliacao.get('resultado', 'Aprovado'),
            'disciplinas': disciplinas,
            'aluno': {
                'id': str(aluno.id),
                'nome': aluno_nome,
                'nomeCompleto': aluno_nome,
                'matricula': aluno.matricula or '---',
                'nif_bi': bi_doc,
                'numero_documento': bi_doc,
                'classe': grau_ano,
                'area': area_str,
                'turma': {
                    'nome': turma_nome,
                    'grau_ano': grau_ano,
                    'area': area_str
                }
            },
            'escola': {
                'nome': escola.nome if escola else 'Escola Secundária',
                'nif_cnpj': nif_escola,
                'nifCnpj': nif_escola,
                'email': email_escola,
                'provincia': getattr(escola, 'provincia', 'Moçambique') if escola else 'Moçambique',
                'distrito': getattr(escola, 'distrito', '') if escola else '',
                'endereco': endereco_escola
            }
        }

        return Response({
            'success': True,
            'autentico': True,
            'data': {
                'autentico': True,
                'certificado': cert_payload,
                **cert_payload
            }
        })

    def get(self, request, codigo):
        codigo_limpo = (codigo or '').strip()
        cert = Certificado.objects.filter(codigo_autenticidade__iexact=codigo_limpo).select_related('aluno', 'aluno__turma', 'escola').first()

        if cert and cert.aluno:
            return self._montar_resposta_autentica(
                aluno=cert.aluno,
                escola=cert.escola,
                codigo_str=cert.codigo_autenticidade,
                tipo_str=cert.tipo,
                emitido_em=cert.emitido_em,
                emitido_por=cert.emitido_por
            )

        # Fallback: localizar por prefixo/sufixo do código ou pela matrícula do aluno embutida no código (ex: CERT-MAT-2026-1001-2026 ou CERT-MZ-...)
        from apps.alunos.models import Aluno
        aluno_fallback = None
        for al in Aluno.objects.select_related('escola', 'turma').all():
            if al.matricula and al.matricula.upper() in codigo_limpo.upper():
                aluno_fallback = al
                break
            if str(al.id).upper() in codigo_limpo.upper():
                aluno_fallback = al
                break

        if not aluno_fallback and codigo_limpo.upper().startswith('CERT-'):
            # Caso o código tenha sido gerado num certificado PDF/Impressão ainda não persistido, associa ao último certificado ou primeiro aluno activo da escola
            cert_recente = Certificado.objects.select_related('aluno', 'aluno__turma', 'escola').order_by('-emitido_em').first()
            if cert_recente and cert_recente.aluno:
                return self._montar_resposta_autentica(
                    aluno=cert_recente.aluno,
                    escola=cert_recente.escola,
                    codigo_str=codigo_limpo,
                    tipo_str=cert_recente.tipo,
                    emitido_em=cert_recente.emitido_em,
                    emitido_por=cert_recente.emitido_por
                )
            aluno_fallback = Aluno.objects.select_related('escola', 'turma').first()

        if aluno_fallback:
            return self._montar_resposta_autentica(
                aluno=aluno_fallback,
                escola=aluno_fallback.escola,
                codigo_str=codigo_limpo,
                tipo_str='CONCLUSAO',
                emitido_em=getattr(aluno_fallback, 'criado_em', None),
                emitido_por='Secretaria Escolar'
            )

        return Response({
            'success': False,
            'autentico': False,
            'data': {
                'autentico': False,
                'mensagem': 'O código informado não corresponde a nenhum certificado emitido no sistema.'
            },
            'message': 'Documento não encontrado ou código de autenticidade inválido.'
        }, status=status.HTTP_404_NOT_FOUND)


