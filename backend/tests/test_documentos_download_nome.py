import pytest
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.disciplinas.models import Disciplina
from apps.alunos.models import Aluno
from apps.notas.models import Nota
from apps.pagamentos.models import Pagamento
from apps.documentos.views import (
    _sanitizar_para_nome_arquivo,
    _obter_nome_completo_aluno,
    _obter_ano_letivo_documento,
    _gerar_nome_documento_aluno
)
from django.conf import settings

@pytest.mark.django_db
class TestDocumentosDownloadNome:
    def setup_method(self):
        self.client = APIClient()
        self.plano = Plano.objects.create(nome='PLANO_TESTE_NOMES', preco=1500, duracao_dias=30)
        self.escola = Escola.objects.create(
            nome='Escola Secundaria de Massinga',
            nif_cnpj='99887766',
            email='massinga@sige.mz',
            status='ATIVA',
            plano=self.plano,
            ano_letivo_ativo='2026'
        )
        self.user = Usuario.objects.create_user(
            email='admin.massinga@sige.mz',
            password='TestPassword123!',
            role='ADMIN_ESCOLA',
            escola=self.escola
        )

        self.turma = Turma.objects.create(
            escola=self.escola,
            nome='10ª A',
            grau_ano='10ª Classe',
            ano_letivo='2026'
        )
        self.disc = Disciplina.objects.create(
            escola=self.escola,
            nome='Matemática',
            codigo='MAT-10',
            ano_letivo='2026'
        )

        self.aluno = Aluno.objects.create(
            escola=self.escola,
            turma=self.turma,
            matricula='2026101',
            nome='João Manuel',
            apelido='Silva',
            data_nascimento='2009-05-20',
            genero='M'
        )

        Nota.objects.create(
            escola=self.escola,
            aluno=self.aluno,
            turma=self.turma,
            disciplina=self.disc,
            periodo='1_TRIMESTRE',
            media_final=16,
            resultado='Aprovado'
        )

        self.pagamento = Pagamento.objects.create(
            escola=self.escola,
            aluno=self.aluno,
            descricao='Propina Escolar Março',
            valor=1200,
            valor_pago=1200,
            mes_referencia='03/2026',
            data_vencimento='2026-03-31',
            data_pagamento='2026-03-10',
            status='PAGO',
            metodo_pagamento='M-Pesa',
            recibo_numero='REC-2026-001'
        )

        login_res = self.client.post(
            '/api/v1/auth/login/',
            {'email': 'admin.massinga@sige.mz', 'password': 'TestPassword123!'},
            format='json'
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['token']}")

    def test_cors_expose_headers_configurado(self):
        """Verifica se CORS expõe content-disposition para o frontend ler o nome do ficheiro"""
        assert hasattr(settings, 'CORS_EXPOSE_HEADERS')
        assert 'content-disposition' in settings.CORS_EXPOSE_HEADERS

    def test_helpers_sanitizacao_e_padronizacao(self):
        """Testa geração de nome do arquivo: Nome do documento - Nome do aluno - Ano.ext"""
        # Sanitização pura
        assert _sanitizar_para_nome_arquivo("João Manuel Silva / Especial") == "Joao Manuel Silva Especial"
        assert _sanitizar_para_nome_arquivo("Declaração Oficial") == "Declaracao Oficial"

        # Nome completo do aluno
        nome_completo = _obter_nome_completo_aluno(self.aluno)
        assert nome_completo == "Joao Manuel Silva"

        # Ano letivo
        ano = _obter_ano_letivo_documento(self.aluno, self.escola)
        assert ano == "2026"

        # Geração padronizada
        nome_arq = _gerar_nome_documento_aluno("Boletim", self.aluno, ano, "pdf")
        assert nome_arq == "Boletim - Joao Manuel Silva - 2026.pdf"

        nome_decl = _gerar_nome_documento_aluno("Declaracao", self.aluno, ano, "docx")
        assert nome_decl == "Declaracao - Joao Manuel Silva - 2026.docx"

    def test_download_boletim_nome_padronizado(self):
        """Testa endpoint de download do Boletim em PDF, DOCX e XLSX"""
        # PDF
        res_pdf = self.client.get(f'/api/v1/impressao/boletim/{self.aluno.id}/pdf')
        assert res_pdf.status_code == 200
        disposition_pdf = res_pdf['Content-Disposition']
        assert 'filename="Boletim - Joao Manuel Silva - 2026.pdf"' in disposition_pdf

        # DOCX
        res_docx = self.client.get(f'/api/v1/impressao/boletim/{self.aluno.id}/docx')
        assert res_docx.status_code == 200
        disposition_docx = res_docx['Content-Disposition']
        assert 'filename="Boletim - Joao Manuel Silva - 2026.docx"' in disposition_docx

        # XLSX
        res_xlsx = self.client.get(f'/api/v1/impressao/boletim/{self.aluno.id}/xlsx')
        assert res_xlsx.status_code == 200
        disposition_xlsx = res_xlsx['Content-Disposition']
        assert 'filename="Boletim - Joao Manuel Silva - 2026.xlsx"' in disposition_xlsx

    def test_download_declaracao_nome_padronizado(self):
        """Testa endpoint de download da Declaração"""
        res_pdf = self.client.get(f'/api/v1/impressao/declaracao/{self.aluno.id}/pdf')
        assert res_pdf.status_code == 200
        disposition_pdf = res_pdf['Content-Disposition']
        assert 'filename="Declaracao - Joao Manuel Silva - 2026.pdf"' in disposition_pdf

        res_docx = self.client.get(f'/api/v1/impressao/declaracao/{self.aluno.id}/docx')
        assert res_docx.status_code == 200
        disposition_docx = res_docx['Content-Disposition']
        assert 'filename="Declaracao - Joao Manuel Silva - 2026.docx"' in disposition_docx

        res_xlsx = self.client.get(f'/api/v1/impressao/declaracao/{self.aluno.id}/xlsx')
        assert res_xlsx.status_code == 200
        disposition_xlsx = res_xlsx['Content-Disposition']
        assert 'filename="Declaracao - Joao Manuel Silva - 2026.xlsx"' in disposition_xlsx

    def test_download_certificado_nome_padronizado(self):
        """Testa endpoint de download do Certificado"""
        res_pdf = self.client.get(f'/api/v1/impressao/certificado/{self.aluno.id}/pdf')
        assert res_pdf.status_code == 200
        disposition_pdf = res_pdf['Content-Disposition']
        assert 'filename="Certificado - Joao Manuel Silva - 2026.pdf"' in disposition_pdf

        res_docx = self.client.get(f'/api/v1/impressao/certificado/{self.aluno.id}/docx')
        assert res_docx.status_code == 200
        disposition_docx = res_docx['Content-Disposition']
        assert 'filename="Certificado - Joao Manuel Silva - 2026.docx"' in disposition_docx

        res_xlsx = self.client.get(f'/api/v1/impressao/certificado/{self.aluno.id}/xlsx')
        assert res_xlsx.status_code == 200
        disposition_xlsx = res_xlsx['Content-Disposition']
        assert 'filename="Certificado - Joao Manuel Silva - 2026.xlsx"' in disposition_xlsx

    def test_download_recibo_nome_padronizado(self):
        """Testa endpoint de download do Recibo de pagamento"""
        res_pdf = self.client.get(f'/api/v1/impressao/recibo/{self.pagamento.id}/pdf')
        assert res_pdf.status_code == 200
        disposition_pdf = res_pdf['Content-Disposition']
        assert 'filename="Recibo - Joao Manuel Silva - 2026.pdf"' in disposition_pdf

        res_docx = self.client.get(f'/api/v1/impressao/recibo/{self.pagamento.id}/docx')
        assert res_docx.status_code == 200
        disposition_docx = res_docx['Content-Disposition']
        assert 'filename="Recibo - Joao Manuel Silva - 2026.docx"' in disposition_docx

    def test_download_ficha_aluno_nome_padronizado(self):
        """Testa endpoint de download da Ficha Biográfica do Aluno"""
        res_pdf = self.client.get(f'/api/v1/impressao/ficha/{self.aluno.id}/pdf')
        assert res_pdf.status_code == 200
        disposition_pdf = res_pdf['Content-Disposition']
        assert 'filename="Ficha - Joao Manuel Silva - 2026.pdf"' in disposition_pdf

        res_docx = self.client.get(f'/api/v1/impressao/ficha/{self.aluno.id}/docx')
        assert res_docx.status_code == 200
        disposition_docx = res_docx['Content-Disposition']
        assert 'filename="Ficha - Joao Manuel Silva - 2026.docx"' in disposition_docx
