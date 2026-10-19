import pytest
from rest_framework.test import APIClient
from django.utils import timezone
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno
from apps.pagamentos.models import Pagamento
from apps.documentos.services.pdf_service import gerar_recibo_pdf
from apps.documentos.services.docx_service import gerar_recibo_docx
import io
import docx
import zlib
import re


def extrair_texto_pdf(pdf_bytes: bytes) -> str:
    """Extrai texto bruto de streams PDF descompactando zlib/FlateDecode."""
    chunks = [pdf_bytes.decode('latin1', errors='ignore')]
    streams = re.findall(b'stream[\r\n]+(.*?)[\r\n]+endstream', pdf_bytes, re.DOTALL)
    for s in streams:
        try:
            dec = zlib.decompress(s)
            chunks.append(dec.decode('latin1', errors='ignore'))
        except Exception:
            try:
                dec = zlib.decompress(s, -15)
                chunks.append(dec.decode('latin1', errors='ignore'))
            except Exception:
                pass
    return " ".join(chunks)


@pytest.mark.django_db
class TestRecibosPagamentoStatus:
    def setup_method(self):
        self.client = APIClient()
        self.saas_plano = Plano.objects.create(nome='SAAS_PLANO_TESTE_RECIBO', preco=5000, duracao_dias=30)
        self.escola = Escola.objects.create(
            nome='Escola Secundária de Massinga',
            nif_cnpj='NUIT-99887766',
            provincia='Inhambane',
            distrito='Massinga',
            telefone='+258 84 123 4567',
            email='secretaria@massinga.edu.mz',
            status='ATIVA',
            plano=self.saas_plano
        )
        self.turma = Turma.objects.create(
            escola=self.escola,
            nome='10ª A',
            grau_ano='10ª',
            turno='DIURNO',
            sala='Sala 04'
        )
        self.aluno = Aluno.objects.create(
            escola=self.escola,
            turma=self.turma,
            matricula='MAT-2026-001',
            nome='Fernando',
            apelido='Mandamule',
            data_nascimento='2009-05-15',
            genero='M'
        )

        # 1. Pagamento NÃO PAGO (Pendente)
        self.pagamento_nao_pago = Pagamento.objects.create(
            escola=self.escola,
            aluno=self.aluno,
            descricao='Propina do Mês de Março 2026',
            mes_referencia='2026-03',
            valor=1500,
            valor_pago=0,
            status='PENDENTE',
            data_vencimento=timezone.now() + timezone.timedelta(days=10)
        )

        # 2. Pagamento PAGO (Liquidado)
        self.pagamento_pago = Pagamento.objects.create(
            escola=self.escola,
            aluno=self.aluno,
            descricao='Propina do Mês de Fevereiro 2026',
            mes_referencia='2026-02',
            valor=1500,
            valor_pago=1500,
            status='PAGO',
            metodo_pagamento='MPESA',
            data_vencimento=timezone.now() - timezone.timedelta(days=30),
            data_pagamento=timezone.now(),
            recibo_numero='REC-2026-00001'
        )

    def test_recibo_nao_pago_pdf(self):
        pdf_bytes = gerar_recibo_pdf(self.pagamento_nao_pago, self.escola)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 1000
        texto = extrair_texto_pdf(pdf_bytes)
        assert "NÃO PAGO" in texto or "NAO PAGO" in texto or "PENDENTE DE LIQUIDAÇÃO" in texto

    def test_recibo_pago_pdf(self):
        pdf_bytes = gerar_recibo_pdf(self.pagamento_pago, self.escola)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 1000
        texto = extrair_texto_pdf(pdf_bytes)
        assert "PAGO" in texto
        assert "LIQUIDADO" in texto

    def test_recibo_nao_pago_docx(self):
        docx_bytes = gerar_recibo_docx(self.pagamento_nao_pago, self.escola)
        doc = docx.Document(io.BytesIO(docx_bytes))
        full_text = "\n".join([p.text for p in doc.paragraphs])
        for t in doc.tables:
            for row in t.rows:
                for cell in row.cells:
                    full_text += " " + cell.text

        assert "NÃO PAGO" in full_text
        assert "Aguardando Liquidação" in full_text
        assert "Escola Secundária de Massinga" in full_text
        assert "Fernando MANDAMULE" in full_text

    def test_recibo_pago_docx(self):
        docx_bytes = gerar_recibo_docx(self.pagamento_pago, self.escola)
        doc = docx.Document(io.BytesIO(docx_bytes))
        full_text = "\n".join([p.text for p in doc.paragraphs])
        for t in doc.tables:
            for row in t.rows:
                for cell in row.cells:
                    full_text += " " + cell.text

        assert "PAGO" in full_text
        assert "1500 MT" in full_text
        assert "MPESA" in full_text

    def test_recibo_impressao_view_nao_pago(self):
        resp = self.client.get(f'/api/v1/impressao/recibo/{self.pagamento_nao_pago.id}/')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['is_pago'] is False
        assert data['status'] == 'NÃO PAGO'
        assert data['status_badge'] == 'danger'
        assert data['pagamento']['valor_pago'] == '0.00'
        assert data['escola']['nome'] == 'Escola Secundária de Massinga'
        assert data['aluno']['matricula'] == self.aluno.matricula

    def test_recibo_impressao_view_pago(self):
        resp = self.client.get(f'/api/v1/impressao/recibo/{self.pagamento_pago.id}/')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['is_pago'] is True
        assert data['status'] == 'PAGO'
        assert data['status_badge'] == 'success'
        assert float(data['pagamento']['valor_pago']) == 1500.0
        assert data['pagamento']['metodo_pagamento'] == 'MPESA'
