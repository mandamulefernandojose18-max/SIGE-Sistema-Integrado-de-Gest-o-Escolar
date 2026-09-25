import pytest
import base64
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.disciplinas.models import Disciplina
from apps.alunos.models import Aluno
from apps.notas.models import Nota
from apps.material_escolar.models import MaterialEscolar

@pytest.mark.django_db
class TestPautasEDocumentos:
    def setup_method(self):
        self.client = APIClient()
        self.plano = Plano.objects.create(nome='PLANO_DOCS', preco=1500, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Primaria e Secundaria', nif_cnpj='11223344', email='docs@escola.mz', status='ATIVA', plano=self.plano)
        self.user = Usuario.objects.create_user(email='admin.docs@escola.mz', password='DocPassword123!', role='ADMIN_ESCOLA', escola=self.escola)

        self.turma = Turma.objects.create(escola=self.escola, nome='10ª A', grau_ano='10ª Classe', ano_letivo='2026')
        self.disc1 = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT-10', ano_letivo='2026')
        self.disc2 = Disciplina.objects.create(escola=self.escola, nome='Física', codigo='FIS-10', ano_letivo='2026')

        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='2026999', nome='Estudante Exemplar', data_nascimento='2009-03-15', genero='M')
        
        Nota.objects.create(escola=self.escola, aluno=self.aluno, turma=self.turma, disciplina=self.disc1, periodo='1_TRIMESTRE', media_final=16, resultado='Aprovado')
        Nota.objects.create(escola=self.escola, aluno=self.aluno, turma=self.turma, disciplina=self.disc2, periodo='1_TRIMESTRE', media_final=15, resultado='Aprovado')

        login_res = self.client.post('/api/v1/auth/login/', {'email': 'admin.docs@escola.mz', 'password': 'DocPassword123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['token']}")

    def test_health_check(self):
        res = self.client.get('/health/')
        assert res.status_code == 200
        assert res.json()['status'] == 'ok'

    def test_gerar_e_consultar_pauta_completa(self):
        res_gerar = self.client.post('/api/v1/pautas/gerar/', {'turma_id': str(self.turma.id), 'periodo': '1_TRIMESTRE'}, format='json')
        assert res_gerar.status_code == 200
        assert res_gerar.data['success'] is True

        res_comp = self.client.get(f'/api/v1/pautas/turma/{self.turma.id}/completa/?periodo=1_TRIMESTRE')
        assert res_comp.status_code == 200
        assert res_comp.data['success'] is True
        assert len(res_comp.data['alunos']) == 1
        assert res_comp.data['alunos'][0]['media_geral'] == 16

    def test_emissao_pauta_pdf_xlsx_docx(self):
        # PDF
        res_pdf = self.client.get(f'/api/v1/pautas/turma/{self.turma.id}/pdf/?periodo=1_TRIMESTRE')
        assert res_pdf.status_code == 200
        assert res_pdf['Content-Type'] == 'application/pdf'
        assert len(res_pdf.content) > 1000

        # XLSX
        res_xlsx = self.client.get(f'/api/v1/pautas/turma/{self.turma.id}/export-xlsx/?periodo=1_TRIMESTRE')
        assert res_xlsx.status_code == 200
        assert 'spreadsheetml' in res_xlsx['Content-Type']
        assert len(res_xlsx.content) > 1000

        # DOCX
        res_docx = self.client.get(f'/api/v1/pautas/turma/{self.turma.id}/docx/?periodo=1_TRIMESTRE')
        assert res_docx.status_code == 200
        assert 'wordprocessingml' in res_docx['Content-Type']
        assert len(res_docx.content) > 1000

    def test_material_escolar_crud_e_download(self):
        sample_b64 = base64.b64encode(b"%PDF-1.4 sample content").decode('utf-8')
        res_create = self.client.post('/api/v1/material-escolar/', {
            'titulo': 'Manual de Teste',
            'classe': '10ª Classe',
            'disciplina': str(self.disc1.id),
            'tipo': 'MANUAL',
            'conteudo_base64': f"data:application/pdf;base64,{sample_b64}",
            'nome_arquivo': 'manual_teste.pdf'
        }, format='json')
        assert res_create.status_code == 201
        mat_id = res_create.data['data']['id']

        # Download do material
        res_down = self.client.get(f'/api/v1/material-escolar/{mat_id}/download/')
        assert res_down.status_code == 200
        assert b"sample content" in res_down.content
