import pytest
import datetime
import base64
from rest_framework.test import APIClient
from apps.tenants.models import Escola, Plano
from apps.accounts.models import Usuario
from apps.documentos.models import CalendarioEscolar, DocumentoCalendarioOficial

@pytest.fixture
def escola_a(db):
    plano = Plano.objects.create(nome='Profissional A', max_alunos=1000, preco=3500)
    return Escola.objects.create(
        nome='Escola Secundária de Massinga',
        codigo_escola='0101S001',
        nif_cnpj='100000001',
        email='massinga.escola@sige.mz',
        plano=plano,
        status='ATIVA'
    )

@pytest.fixture
def escola_b(db):
    plano = Plano.objects.create(nome='Profissional B', max_alunos=1000, preco=3500)
    return Escola.objects.create(
        nome='Escola Secundária de Vilankulo',
        codigo_escola='0101S002',
        nif_cnpj='100000002',
        email='vilankulo.escola@sige.mz',
        plano=plano,
        status='ATIVA'
    )

@pytest.fixture
def director_a(db, escola_a):
    return Usuario.objects.create_user(
        email='director.a@sige.mz',
        nome='Director Massinga',
        role='DIRECTOR_ESCOLA',
        escola=escola_a,
        password='password123'
    )

@pytest.fixture
def director_b(db, escola_b):
    return Usuario.objects.create_user(
        email='director.b@sige.mz',
        nome='Director Vilankulo',
        role='DIRECTOR_ESCOLA',
        escola=escola_b,
        password='password123'
    )

@pytest.mark.django_db
class TestCalendarioDocumentos:
    def test_upload_e_download_documento_oficial(self, escola_a, director_a):
        client = APIClient()
        client.force_authenticate(user=director_a)

        conteudo_exemplo = b"%PDF-1.4 Mock Official Mozambican Calendar Document Content"
        b64_doc = base64.b64encode(conteudo_exemplo).decode('utf-8')

        # 1. Carregar documento oficial via base64
        payload = {
            'titulo': 'Calendário Geral do Ano Lectivo 2026 - Diploma Ministerial',
            'ano_lectivo': '2026',
            'descricao': 'Circular nº 01/MINEDH/2026',
            'nome_arquivo': 'calendario_oficial_2026.pdf',
            'extensao': 'pdf',
            'tipo_mime': 'application/pdf',
            'tamanho_bytes': len(conteudo_exemplo),
            'conteudo_base64': b64_doc
        }

        res = client.post('/api/v1/documentos/calendario/carregar_documento_oficial/', payload, format='json')
        assert res.status_code == 200, res.data
        assert res.data['success'] is True

        # 2. Consultar documento oficial em vigor
        res_info = client.get('/api/v1/documentos/calendario/documento_oficial/')
        assert res_info.status_code == 200
        assert res_info.data['success'] is True
        assert res_info.data['data']['titulo'] == 'Calendário Geral do Ano Lectivo 2026 - Diploma Ministerial'
        assert res_info.data['data']['nome_arquivo'] == 'calendario_oficial_2026.pdf'

        # 3. Descarregar ficheiro binário
        res_down = client.get('/api/v1/documentos/calendario/download_documento_oficial/')
        assert res_down.status_code == 200
        assert res_down.content == conteudo_exemplo
        assert 'attachment' in res_down['Content-Disposition']

    def test_importar_eventos_por_csv(self, escola_a, director_a):
        client = APIClient()
        client.force_authenticate(user=director_a)

        csv_text = (
            "Data Início;Data Fim;Título do Evento;Tipo de Evento;Trimestre;Descrição\n"
            "2026-02-02;;Abertura Oficial das Aulas;EVENTO_ESCOLAR;1_TRIMESTRE;Boas-vindas\n"
            "2026-03-09;2026-03-13;1ª Ronda ACS;AVALIACAO_TESTE;1_TRIMESTRE;Provas contínuas\n"
            "2026-04-13;2026-04-17;Realização de ACP;AVALIACAO_TESTE;1_TRIMESTRE;Avaliação Trimestral\n"
        )
        b64_csv = base64.b64encode(csv_text.encode('utf-8')).decode('utf-8')

        payload = {
            'nome_arquivo': 'calendario_2026.csv',
            'conteudo_base64': b64_csv
        }

        res = client.post('/api/v1/documentos/calendario/importar_ficheiro/', payload, format='json')
        assert res.status_code == 200, res.data
        assert res.data['success'] is True
        assert res.data['count'] == 3

        # Validar persistência no banco de dados
        eventos = CalendarioEscolar.objects.filter(escola=escola_a).order_by('data_inicio')
        assert eventos.count() == 3
        assert eventos[0].titulo == 'Abertura Oficial das Aulas'
        assert eventos[0].data_inicio == datetime.date(2026, 2, 2)
        assert eventos[1].titulo == '1ª Ronda ACS'
        assert eventos[1].tipo == 'AVALIACAO_TESTE'

    def test_importar_eventos_por_json_direto(self, escola_a, director_a):
        client = APIClient()
        client.force_authenticate(user=director_a)

        payload = {
            'eventos': [
                {
                    'titulo': 'Conselho de Turma Geral',
                    'data_inicio': '2026-04-20',
                    'data_fim': '2026-04-24',
                    'tipo': 'CONSELHO_TURMA',
                    'trimestre': '1_TRIMESTRE',
                    'descricao': 'Validação final de notas'
                },
                {
                    'titulo': 'Exames Nacionais da 12ª Classe',
                    'data_inicio': '2026-11-16',
                    'data_fim': '2026-11-27',
                    'tipo': 'EXAME',
                    'trimestre': '3_TRIMESTRE',
                    'descricao': 'Exames da 12ª'
                }
            ]
        }

        res = client.post('/api/v1/documentos/calendario/importar_ficheiro/', payload, format='json')
        assert res.status_code == 200
        assert res.data['count'] == 2

    def test_modelo_csv_download(self, director_a):
        client = APIClient()
        client.force_authenticate(user=director_a)

        res = client.get('/api/v1/documentos/calendario/modelo_csv/')
        assert res.status_code == 200
        assert 'attachment' in res['Content-Disposition']
        assert b'Data In' in res.content

    def test_anexo_evento_individual(self, escola_a, director_a):
        client = APIClient()
        client.force_authenticate(user=director_a)

        pdf_bytes = b"%PDF-1.4 Event Attachment Guideline"
        b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

        ev = CalendarioEscolar.objects.create(
            escola=escola_a,
            titulo='Semana de Exames',
            data_inicio=datetime.date(2026, 11, 16),
            tipo='EXAME',
            trimestre='3_TRIMESTRE',
            nome_documento='edital_exames.pdf',
            documento_tipo='application/pdf',
            documento_tamanho=len(pdf_bytes),
            documento_base64=b64_pdf
        )

        res = client.get(f'/api/v1/documentos/calendario/{ev.id}/download_anexo/')
        assert res.status_code == 200
        assert res.content == pdf_bytes
        assert 'edital_exames.pdf' in res['Content-Disposition']

    def test_isolamento_multitenant_calendario(self, escola_a, escola_b, director_a, director_b):
        client_a = APIClient()
        client_a.force_authenticate(user=director_a)

        client_b = APIClient()
        client_b.force_authenticate(user=director_b)

        # Escola A cria documento oficial
        DocumentoCalendarioOficial.objects.create(
            escola=escola_a,
            titulo='Documento Exclusivo Escola A',
            nome_arquivo='doc_escola_a.pdf',
            conteudo_base64=base64.b64encode(b'Massinga Only').decode('utf-8'),
            publicado_por=director_a
        )

        # Escola B consulta o seu documento oficial
        res_b = client_b.get('/api/v1/documentos/calendario/documento_oficial/')
        assert res_b.status_code == 200
        assert res_b.data['data'] is None  # Escola B não tem documento
