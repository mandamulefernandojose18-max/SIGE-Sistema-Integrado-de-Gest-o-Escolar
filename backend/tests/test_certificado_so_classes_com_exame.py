import pytest
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno


@pytest.mark.django_db
class TestCertificadoSoClassesComExame:
    def setup_method(self):
        self.client = APIClient()
        plano = Plano.objects.create(nome='PLANO_CERT_EXAME', preco=1500, duracao_dias=30)
        self.escola = Escola.objects.create(
            nome='Escola Cert Exame', nif_cnpj='55443322', email='certexame@sige.mz',
            status='ATIVA', plano=plano, ano_letivo_ativo='2026',
            config_classes_exames={'8ª Classe': False, '10ª Classe': True},
        )
        Usuario.objects.create_user(
            email='admin.certexame@sige.mz', password='TestPassword123!',
            role='ADMIN_ESCOLA', escola=self.escola,
        )
        self.turma_sem = Turma.objects.create(escola=self.escola, nome='8ª A', grau_ano='8ª Classe', ano_letivo='2026')
        self.turma_com = Turma.objects.create(escola=self.escola, nome='10ª A', grau_ano='10ª Classe', ano_letivo='2026')
        self.aluno_sem = Aluno.objects.create(
            escola=self.escola, turma=self.turma_sem, matricula='2026801',
            nome='Ana', apelido='Mucavele', data_nascimento='2012-05-20', genero='F',
        )
        self.aluno_com = Aluno.objects.create(
            escola=self.escola, turma=self.turma_com, matricula='2026101',
            nome='Joao', apelido='Silva', data_nascimento='2009-05-20', genero='M',
        )
        res = self.client.post(
            '/api/v1/auth/login/',
            {'email': 'admin.certexame@sige.mz', 'password': 'TestPassword123!'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")

    def test_certificado_individual_bloqueado_sem_exame(self):
        for sufixo in ('', '/pdf', '/docx', '/xlsx'):
            r = self.client.get(f'/api/v1/impressao/certificado/{self.aluno_sem.id}{sufixo}?carimbo=nao')
            assert r.status_code == 403, sufixo

    def test_certificado_individual_permitido_com_exame(self):
        r = self.client.get(f'/api/v1/impressao/certificado/{self.aluno_com.id}/pdf?carimbo=nao')
        assert r.status_code == 200

    def test_certificado_lote_bloqueado_sem_exame(self):
        r = self.client.get(f'/api/v1/impressao/lote/turma/{self.turma_sem.id}/pdf?tipo=CERTIFICADO')
        assert r.status_code == 403
        r = self.client.get(f'/api/v1/impressao/lote/turma/{self.turma_sem.id}?tipo=CERTIFICADO')
        assert r.status_code == 403

    def test_outros_documentos_mantem_se_sem_exame(self):
        assert self.client.get(f'/api/v1/impressao/boletim/{self.aluno_sem.id}/pdf?carimbo=nao').status_code == 200
        assert self.client.get(f'/api/v1/impressao/declaracao/{self.aluno_sem.id}/pdf?carimbo=nao').status_code == 200
        assert self.client.get(f'/api/v1/impressao/lote/turma/{self.turma_sem.id}?tipo=BOLETIM').status_code == 200

    def test_emissao_registo_certificado_bloqueada_sem_exame(self):
        r = self.client.post('/api/v1/certificados/', {'aluno': str(self.aluno_sem.id), 'tipo': 'CONCLUSAO'}, format='json')
        assert r.status_code in (400, 403)

    def test_lista_de_classes_marca_exame(self):
        r = self.client.get('/api/v1/impressao/classes')
        assert r.status_code == 200
        por_classe = {c['classe']: c['tem_exame'] for c in r.data['data']}
        assert por_classe == {'8ª Classe': False, '10ª Classe': True}

