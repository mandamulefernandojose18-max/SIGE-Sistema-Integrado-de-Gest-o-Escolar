import base64
import io
import os
import uuid
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from common.permissions.rbac import IsDirectorEscola
from .models import Certificado, DocumentoCarimbado
from .serializers import CertificadoSerializer
from .carimbo import NIVEIS, gerar_previa_base64, nome_abreviado, verificar_assinatura

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
            raise drf_serializers.ValidationError({'escola': 'Nenhuma instituiÃ§Ã£o identificada para emissÃ£o do certificado.'})
        if aluno and aluno.escola_id != escola.id:
            raise drf_serializers.ValidationError({'aluno': 'O aluno selecionado pertence a uma escola diferente da ativa.'})

        if aluno:
            from apps.documentos.views import classe_permite_certificado
            classe = aluno.turma.grau_ano if aluno.turma else None
            if not classe_permite_certificado(escola, classe):
                raise drf_serializers.ValidationError({'aluno': 'O certificado só está disponível para classes com exame.'})

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




_nome_abreviado = nome_abreviado  # primeiro nome por extenso e iniciais dos restantes


def _matricula_mascarada(matricula):
    m = (matricula or '').strip()
    return ('â€¢â€¢â€¢â€¢' + m[-3:]) if len(m) > 3 else 'â€¢â€¢â€¢â€¢'


class VerificarCertificadoView(APIView):
    """VerificaÃ§Ã£o pÃºblica (QR do certificado).

    SÃ³ aceita um cÃ³digo EXISTENTE em `Certificado` (correspondÃªncia exacta) e devolve dados mÃ­nimos:
    escola, tipo, data, nome abreviado e matrÃ­cula mascarada. Nunca devolve BI/documento nem notas,
    nunca "adivinha" o aluno a partir do cÃ³digo e nunca inventa valores em falta.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'verificacao'

    @staticmethod
    def _responder_selo(selo):
        """Documento emitido com carimbo de nÃ­vel B/C: sÃ³ dados mÃ­nimos, nunca notas nem identificaÃ§Ã£o completa."""
        escola = selo.escola
        valida = verificar_assinatura(selo)
        payload = {
            'autentico': valida is not False,
            'selo': True,
            'codigo': selo.codigo,
            'tipo': selo.tipo,
            'descricao': selo.descricao,
            'nivel': selo.nivel,
            'emitido_em': selo.emitido_em,
            'emitido_por': selo.emitido_por,
            'assinatura_digital': {
                'presente': valida is not None,
                'valida': valida,
                'impressao_digital_chave': (selo.impressao_digital_chave or '')[:16].upper(),
            },
            'escola': {
                'nome': escola.nome,
                'nif_cnpj': escola.nif_cnpj or '',
                'provincia': escola.provincia or '',
                'distrito': escola.distrito or '',
            },
        }
        if valida is False:
            return Response({'success': False, 'autentico': False, 'data': {
                **payload, 'mensagem': 'A assinatura digital deste documento nÃ£o confere com o registo.'},
                'message': 'Assinatura digital invÃ¡lida.'}, status=status.HTTP_409_CONFLICT)
        return Response({'success': True, 'autentico': True, 'data': {**payload, 'certificado': payload}})

    def get(self, request, codigo):
        codigo_limpo = (codigo or '').strip()
        cert = None
        if codigo_limpo:
            cert = (Certificado.objects.filter(codigo_autenticidade__iexact=codigo_limpo)
                    .select_related('aluno', 'aluno__turma', 'escola').first())

        if not cert and codigo_limpo:
            selo = DocumentoCarimbado.objects.filter(codigo__iexact=codigo_limpo).select_related('escola').first()
            if selo:
                return self._responder_selo(selo)

        if not cert or not cert.aluno:
            return Response({
                'success': False,
                'autentico': False,
                'data': {
                    'autentico': False,
                    'mensagem': 'O cÃ³digo informado nÃ£o corresponde a nenhum certificado emitido no sistema.'
                },
                'message': 'Documento nÃ£o encontrado ou cÃ³digo de autenticidade invÃ¡lido.'
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


class CarimboConfigView(APIView):
    """ConfiguraÃ§Ã£o do carimbo da escola (sÃ³ administraÃ§Ã£o da escola)."""
    permission_classes = [IsAuthenticated, IsDirectorEscola]
    TAMANHO_MAX_IMAGEM = 1_500_000  # bytes

    @staticmethod
    def _escola(request):
        from common.utils.tenant import get_tenant_escola
        return get_tenant_escola(request)

    @staticmethod
    def _estado(escola):
        return {
            'nivel': escola.carimbo_nivel,
            'origem': escola.carimbo_origem,
            'tem_imagem': bool(escola.carimbo_imagem_base64),
            'niveis': [{'codigo': c, 'rotulo': r} for c, r in escola._meta.get_field('carimbo_nivel').choices],
        }

    def get(self, request):
        escola = self._escola(request)
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola associada.'}, status=status.HTTP_404_NOT_FOUND)
        dados = self._estado(escola)
        if request.query_params.get('previa'):
            nivel = request.query_params.get('nivel') or escola.carimbo_nivel
            if nivel not in NIVEIS:
                return Response({'success': False, 'message': 'NÃ­vel de carimbo invÃ¡lido.'}, status=status.HTTP_400_BAD_REQUEST)
            dados['previa'] = gerar_previa_base64(escola, nivel)
        return Response({'success': True, 'data': dados})

    def put(self, request):
        escola = self._escola(request)
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola associada.'}, status=status.HTTP_404_NOT_FOUND)
        d = request.data
        nivel = d.get('nivel', escola.carimbo_nivel)
        origem = d.get('origem', escola.carimbo_origem)
        if nivel not in NIVEIS:
            return Response({'success': False, 'message': 'NÃ­vel de carimbo invÃ¡lido.'}, status=status.HTTP_400_BAD_REQUEST)
        if origem not in ('GERADO', 'CARREGADO'):
            return Response({'success': False, 'message': 'Origem do carimbo invÃ¡lida.'}, status=status.HTTP_400_BAD_REQUEST)

        imagem = d.get('imagem_base64')
        if d.get('remover_imagem'):
            escola.carimbo_imagem_base64 = None
        elif imagem:
            if not isinstance(imagem, str) or not imagem.startswith('data:image/') or ',' not in imagem:
                return Response({'success': False, 'message': 'Envie a imagem do carimbo em PNG ou JPEG.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                bruto = base64.b64decode(imagem.split(',', 1)[1], validate=False)
                from PIL import Image
                im = Image.open(io.BytesIO(bruto))
                formato = (im.format or '').upper()
                im.verify()
            except Exception:
                return Response({'success': False, 'message': 'A imagem do carimbo nÃ£o Ã© vÃ¡lida.'}, status=status.HTTP_400_BAD_REQUEST)
            if formato not in ('PNG', 'JPEG'):
                return Response({'success': False, 'message': 'A imagem do carimbo tem de ser PNG ou JPEG.'}, status=status.HTTP_400_BAD_REQUEST)
            if len(bruto) > self.TAMANHO_MAX_IMAGEM:
                return Response({'success': False, 'message': 'A imagem do carimbo excede 1,5 MB.'}, status=status.HTTP_400_BAD_REQUEST)
            escola.carimbo_imagem_base64 = imagem
        if origem == 'CARREGADO' and not escola.carimbo_imagem_base64:
            return Response({'success': False, 'message': 'Carregue a imagem do carimbo antes de escolher Â«Imagem carregada pela escolaÂ».'}, status=status.HTTP_400_BAD_REQUEST)

        escola.carimbo_nivel = nivel
        escola.carimbo_origem = origem
        escola.save(update_fields=['carimbo_nivel', 'carimbo_origem', 'carimbo_imagem_base64', 'updated_at'])
        return Response({'success': True, 'data': self._estado(escola)})



class CarimbarFicheiroView(APIView):
    """Carimba um ficheiro PDF/Excel/Word gerado no navegador (listas e relatórios exportados no painel).
    Recebe o ficheiro, devolve-o carimbado com o carimbo da escola do utilizador. Aluno/encarregado não carimbam."""
    permission_classes = [IsAuthenticated]
    TAMANHO_MAX = 15 * 1024 * 1024
    TIPOS = {
        'pdf': 'application/pdf',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }

    def post(self, request):
        import hashlib
        from django.http import HttpResponse
        from common.utils.tenant import get_tenant_escola
        from .carimbo import carimbar_documento
        if str(getattr(request.user, 'role', '') or '').upper() in ('ALUNO', 'ENCARREGADO'):
            return Response({'success': False, 'message': 'Este perfil não emite documentos carimbados.'}, status=status.HTTP_403_FORBIDDEN)
        escola = get_tenant_escola(request)
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola associada.'}, status=status.HTTP_400_BAD_REQUEST)
        f = request.FILES.get('ficheiro')
        if not f:
            return Response({'success': False, 'message': 'Envie o ficheiro a carimbar.'}, status=status.HTTP_400_BAD_REQUEST)
        if f.size > self.TAMANHO_MAX:
            return Response({'success': False, 'message': 'O ficheiro excede 15 MB.'}, status=status.HTTP_400_BAD_REQUEST)
        formato = (f.name.rsplit('.', 1)[-1] if '.' in f.name else '').lower()
        if formato not in self.TIPOS:
            return Response({'success': False, 'message': 'Só se carimbam ficheiros PDF, Excel (xlsx) e Word (docx).'}, status=status.HTTP_400_BAD_REQUEST)
        dados = f.read()
        magia = {'pdf': b'%PDF', 'xlsx': b'PK', 'docx': b'PK'}[formato]
        if not dados.startswith(magia):
            return Response({'success': False, 'message': 'O ficheiro não é válido.'}, status=status.HTTP_400_BAD_REQUEST)
        rotulo = (request.data.get('tipo') or 'Documento').strip()[:40] or 'Documento'
        referencia = 'ficheiro:' + hashlib.sha256(dados).hexdigest()   # o mesmo ficheiro mantém o mesmo código
        try:
            saida = carimbar_documento(True, dados, formato, escola, 'EXPORTACAO', referencia, rotulo,
                                       getattr(request.user, 'nome', None) or 'Secretaria')
        except Exception:
            return Response({'success': False, 'message': 'Não foi possível aplicar o carimbo ao documento.'}, status=500)
        resposta = HttpResponse(saida, content_type=self.TIPOS[formato])
        resposta['Content-Disposition'] = 'attachment; filename="carimbado.' + formato + '"'
        return resposta
