"""Carimbo digital da escola: pergunta obrigatória em cada emissão, níveis A/B/C e verificação pública."""
import base64
import io

import pytest
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos.models import Aluno
from apps.certificados.carimbo import verificar_assinatura
from apps.certificados.models import ChaveAssinaturaEscola, DocumentoCarimbado
from apps.disciplinas.models import Disciplina
from apps.notas.models import Nota
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma


def _png_uri(cor=(30, 58, 138, 255), formato='PNG'):
    buf = io.BytesIO()
    Image.new('RGBA' if formato == 'PNG' else 'RGB', (60, 60), cor if formato == 'PNG' else cor[:3]).save(buf, format=formato)
    return f"data:image/{formato.lower()};base64," + base64.b64encode(buf.getvalue()).decode()


def _cliente(email, senha):
    c = APIClient()
    r = c.post('/api/v1/auth/login/', {'email': email, 'password': senha}, format='json')
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['token']}")
    return c


@pytest.mark.django_db
class TestCarimbo:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_CARIMBO', preco=1500, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Secundária de Teste', nif_cnpj='NIF_CAR1', email='car1@escola.mz',
                                            status='ATIVA', plano=plano)
        self.outra = Escola.objects.create(nome='Outra Escola', nif_cnpj='NIF_CAR2', email='car2@escola.mz',
                                           status='ATIVA', plano=plano)
        Usuario.objects.create_user(email='dir@escola.mz', password='CarPassword123!', role='DIRECTOR_ESCOLA', escola=self.escola)
        Usuario.objects.create_user(email='sec@escola.mz', password='CarPassword123!', role='SECRETARIA', escola=self.escola)
        turma = Turma.objects.create(escola=self.escola, nome='10ª A', grau_ano='10ª Classe', ano_letivo='2026')
        disc = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT-10', ano_letivo='2026')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=turma, matricula='2026001', nome='Maria Joaquina Santos',
                                          data_nascimento='2009-03-15', genero='F')
        Nota.objects.create(escola=self.escola, aluno=self.aluno, turma=turma, disciplina=disc,
                            periodo='1_TRIMESTRE', media_final=16, resultado='Aprovado')
        self.dir = _cliente('dir@escola.mz', 'CarPassword123!')
        self.sec = _cliente('sec@escola.mz', 'CarPassword123!')

    def _url(self, doc='boletim', fmt='pdf', extra=''):
        return f'/api/v1/impressao/{doc}/{self.aluno.id}/{fmt}{extra}'

    def _nivel(self, nivel):
        self.escola.carimbo_nivel = nivel
        self.escola.save()

    # -- pergunta obrigatória -------------------------------------------------------------
    @pytest.mark.parametrize('doc', ['boletim', 'declaracao', 'certificado', 'ficha'])
    @pytest.mark.parametrize('fmt', ['pdf', 'docx'])
    def test_sem_resposta_nunca_assume(self, doc, fmt):
        res = self.dir.get(self._url(doc, fmt))
        assert res.status_code == 409
        assert res.data['requer_decisao_carimbo'] is True
        assert DocumentoCarimbado.objects.count() == 0

    def test_resposta_invalida_tambem_pergunta(self):
        assert self.dir.get(self._url(extra='?carimbo=talvez')).status_code == 409

    def test_sem_carimbo_devolve_documento_intacto(self):
        self._nivel('ASSINATURA')
        res = self.dir.get(self._url(extra='?carimbo=nao'))
        assert res.status_code == 200 and res.content[:4] == b'%PDF'
        assert DocumentoCarimbado.objects.count() == 0
        assert ChaveAssinaturaEscola.objects.count() == 0

    # -- nível A ---------------------------------------------------------------------------
    def test_nivel_a_so_imagem_sem_registo(self):
        self._nivel('IMAGEM')
        sem = self.dir.get(self._url(extra='?carimbo=nao')).content
        com = self.dir.get(self._url(extra='?carimbo=sim'))
        assert com.status_code == 200 and com.content[:4] == b'%PDF'
        assert com.content != sem
        assert DocumentoCarimbado.objects.count() == 0

    def test_nivel_a_com_imagem_carregada(self):
        self.escola.carimbo_origem = 'CARREGADO'
        self.escola.carimbo_imagem_base64 = _png_uri()
        self.escola.carimbo_nivel = 'IMAGEM'
        self.escola.save()
        assert self.dir.get(self._url(extra='?carimbo=sim')).status_code == 200

    # -- nível B ---------------------------------------------------------------------------
    def test_nivel_b_regista_selo_e_verifica_publicamente(self):
        self._nivel('SELO')
        assert self.dir.get(self._url(extra='?carimbo=sim')).status_code == 200
        doc = DocumentoCarimbado.objects.get()
        assert doc.codigo.startswith('SEL-') and doc.assinatura == ''
        # Reemitir o mesmo documento mantém o código
        self.dir.get(self._url(extra='?carimbo=sim'))
        assert DocumentoCarimbado.objects.count() == 1
        pub = APIClient().get(f'/api/v1/certificados/verificar/{doc.codigo}/')
        assert pub.status_code == 200 and pub.data['autentico'] is True
        corpo = str(pub.data)
        assert pub.data['data']['selo'] is True
        assert 'Maria J. S.' in corpo
        assert 'Maria Joaquina Santos' not in corpo and '2026001' not in corpo
        assert pub.data['data']['assinatura_digital']['presente'] is False

    def test_nivel_b_word(self):
        self._nivel('SELO')
        res = self.dir.get(self._url(fmt='docx', extra='?carimbo=sim'))
        assert res.status_code == 200 and res.content[:2] == b'PK'
        assert DocumentoCarimbado.objects.count() == 1

    # -- nível C ---------------------------------------------------------------------------
    def test_nivel_c_assina_e_deteta_adulteracao(self):
        self._nivel('ASSINATURA')
        assert self.dir.get(self._url('certificado', extra='?carimbo=sim')).status_code == 200
        doc = DocumentoCarimbado.objects.get()
        assert doc.assinatura and ChaveAssinaturaEscola.objects.filter(escola=self.escola).exists()
        assert verificar_assinatura(doc) is True
        pub = APIClient().get(f'/api/v1/certificados/verificar/{doc.codigo}/')
        assert pub.status_code == 200
        assert pub.data['data']['assinatura_digital'] == {
            'presente': True, 'valida': True,
            'impressao_digital_chave': doc.impressao_digital_chave[:16].upper()}
        # Adulterar o registo invalida a assinatura
        DocumentoCarimbado.objects.filter(pk=doc.pk).update(tipo='DECLARACAO')
        pub2 = APIClient().get(f'/api/v1/certificados/verificar/{doc.codigo}/')
        assert pub2.status_code == 409 and pub2.data['autentico'] is False

    def test_chave_privada_nao_fica_em_claro(self):
        self._nivel('ASSINATURA')
        self.dir.get(self._url(extra='?carimbo=sim'))
        chave = ChaveAssinaturaEscola.objects.get(escola=self.escola)
        assert 'PRIVATE KEY' not in chave.chave_privada_cifrada
        assert 'PUBLIC KEY' in chave.chave_publica_pem

    def test_subir_de_nivel_assina_documento_ja_selado(self):
        self._nivel('SELO')
        self.dir.get(self._url(extra='?carimbo=sim'))
        self._nivel('ASSINATURA')
        self.dir.get(self._url(extra='?carimbo=sim'))
        doc = DocumentoCarimbado.objects.get()
        assert doc.nivel == 'ASSINATURA' and verificar_assinatura(doc) is True

    def test_codigo_de_outra_escola_nao_mistura_dados(self):
        self._nivel('SELO')
        self.dir.get(self._url(extra='?carimbo=sim'))
        doc = DocumentoCarimbado.objects.get()
        pub = APIClient().get(f'/api/v1/certificados/verificar/{doc.codigo}/')
        assert pub.data['data']['escola']['nome'] == 'Escola Secundária de Teste'
        assert 'Outra Escola' not in str(pub.data)
        assert APIClient().get('/api/v1/certificados/verificar/SEL-INEXISTENTE/').status_code == 404

    # -- configuração ----------------------------------------------------------------------
    def test_so_director_configura(self):
        assert self.sec.put('/api/v1/certificados/carimbo/', {'nivel': 'IMAGEM'}, format='json').status_code == 403
        assert APIClient().put('/api/v1/certificados/carimbo/', {'nivel': 'IMAGEM'}, format='json').status_code in (401, 403)
        ok = self.dir.put('/api/v1/certificados/carimbo/', {'nivel': 'ASSINATURA'}, format='json')
        assert ok.status_code == 200 and ok.data['data']['nivel'] == 'ASSINATURA'
        self.escola.refresh_from_db()
        assert self.escola.carimbo_nivel == 'ASSINATURA'

    def test_configuracao_valida_entradas(self):
        url = '/api/v1/certificados/carimbo/'
        assert self.dir.put(url, {'nivel': 'OURO'}, format='json').status_code == 400
        assert self.dir.put(url, {'origem': 'CARREGADO'}, format='json').status_code == 400  # sem imagem
        assert self.dir.put(url, {'imagem_base64': 'data:image/png;base64,AAAA'}, format='json').status_code == 400
        assert self.dir.put(url, {'imagem_base64': 'texto'}, format='json').status_code == 400
        ok = self.dir.put(url, {'imagem_base64': _png_uri(), 'origem': 'CARREGADO'}, format='json')
        assert ok.status_code == 200 and ok.data['data']['tem_imagem'] is True
        rem = self.dir.put(url, {'remover_imagem': True, 'origem': 'GERADO'}, format='json')
        assert rem.data['data']['tem_imagem'] is False

    @pytest.mark.parametrize('nivel', ['IMAGEM', 'SELO', 'ASSINATURA'])
    def test_previa_nao_grava_nada(self, nivel):
        res = self.dir.get(f'/api/v1/certificados/carimbo/?previa=1&nivel={nivel}')
        assert res.status_code == 200 and res.data['data']['previa'].startswith('data:image/png;base64,')
        assert DocumentoCarimbado.objects.count() == 0
        assert ChaveAssinaturaEscola.objects.count() == 0

    def test_carimbo_nao_se_altera_por_escola_admin_info(self):
        # A secretaria acede a escola-admin/info, mas o carimbo é exclusivo do director/administrador.
        self.sec.put('/api/v1/escola-admin/info', {'carimbo_nivel': 'ASSINATURA', 'carimbo_origem': 'CARREGADO',
                                                    'carimbo_imagem_base64': _png_uri()}, format='json')
        self.escola.refresh_from_db()
        assert self.escola.carimbo_nivel == 'SELO' and self.escola.carimbo_origem == 'GERADO'
        assert not self.escola.carimbo_imagem_base64
        info = self.dir.get('/api/v1/escola-admin/info')
        assert 'carimbo_imagem_base64' not in info.data['data']


def test_aluno_e_encarregado_nunca_obtem_carimbo_nem_sao_perguntados():
    from types import SimpleNamespace as NS
    from apps.certificados.carimbo import decidir_carimbo
    for papel in ('ALUNO', 'ENCARREGADO'):
        for valor in ('sim', 'nao', ''):
            req = NS(user=NS(role=papel), query_params={'carimbo': valor} if valor else {})
            assert decidir_carimbo(req) is False


@pytest.mark.django_db
class TestCarimboPdfIntegro:
    setup_method = TestCarimbo.setup_method
    _url = TestCarimbo._url
    _nivel = TestCarimbo._nivel

    @pytest.mark.parametrize('doc', ['boletim', 'declaracao', 'certificado'])
    def test_carimbo_nao_remove_texto_nem_muda_paginas(self, doc):
        import pymupdf
        self._nivel('ASSINATURA')
        sem = pymupdf.open(stream=self.dir.get(self._url(doc, extra='?carimbo=nao')).content, filetype='pdf')
        com = pymupdf.open(stream=self.dir.get(self._url(doc, extra='?carimbo=sim')).content, filetype='pdf')
        assert len(sem) == len(com)
        palavras_sem = {p[4] for pg in sem for p in pg.get_text('words')}
        palavras_com = {p[4] for pg in com for p in pg.get_text('words')}
        assert palavras_sem <= palavras_com
        assert any(p.startswith('SEL-') for p in palavras_com)
