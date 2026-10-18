import pytest
import json
from decimal import Decimal
from unittest.mock import patch
from django.utils import timezone
from django.test import Client
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno
from apps.pagamentos.models import Pagamento
from apps.ferramentas.models import (
    MensagemSMS,
    TransacaoGatewayMovel,
    ConfiguracaoGateway,
    MensagemWhatsApp,
    ReconciliacaoSmsMovel
)

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def superadmin_user(db):
    u = Usuario.objects.filter(email='admin.prompt@sige.com').first()
    if not u:
        u = Usuario.objects.create_user(
            email='admin.prompt@sige.com',
            username='admin.prompt@sige.com',
            password='testpassword123',
            role='SUPERADMIN',
            nome='Super Administrador Teste'
        )
    return u

@pytest.fixture
def aluno_user(db):
    u = Usuario.objects.filter(email='aluno.prompt@sige.com').first()
    if not u:
        u = Usuario.objects.create_user(
            email='aluno.prompt@sige.com',
            username='aluno.prompt@sige.com',
            password='testpassword123',
            role='ALUNO',
            nome='Aluno Teste'
        )
    return u

@pytest.fixture
def financeiro_user(db):
    u = Usuario.objects.filter(email='fin.prompt@sige.com').first()
    if not u:
        u = Usuario.objects.create_user(
            email='fin.prompt@sige.com',
            username='fin.prompt@sige.com',
            password='testpassword123',
            role='FINANCEIRO',
            nome='Gestor Financeiro Teste'
        )
    return u

@pytest.mark.django_db
def test_prompt_gateway_sem_sessao(client):
    """Sem sessão: a página redireciona (ou 401) e o download retorna 401."""
    resp_page = client.get('/ferramentas/prompt-gateway')
    assert resp_page.status_code in [302, 401]

    resp_down = client.get('/ferramentas/prompt-gateway/descarregar')
    assert resp_down.status_code == 401
    assert resp_down.headers.get('Cache-Control') is not None
    assert 'no-store' in resp_down.headers.get('Cache-Control')

@pytest.mark.django_db
def test_prompt_gateway_sem_permissao_aluno(client, aluno_user):
    """Com sessão mas sem permissão (ALUNO): retorna 403 Forbidden."""
    client.force_login(aluno_user)

    resp_page = client.get('/ferramentas/prompt-gateway')
    assert resp_page.status_code == 403

    resp_down = client.get('/ferramentas/prompt-gateway/descarregar')
    assert resp_down.status_code == 403

@pytest.mark.django_db
def test_prompt_gateway_com_superadmin(client, superadmin_user):
    """Com administrador: página devolve 200, texto escapado e cabeçalhos de segurança."""
    client.force_login(superadmin_user)

    resp_page = client.get('/ferramentas/prompt-gateway')
    assert resp_page.status_code == 200
    html = resp_page.content.decode('utf-8')
    assert 'Gateway SMS, USSD' in html
    assert 'noindex' in html
    assert resp_page.headers.get('X-Robots-Tag') == 'noindex, nofollow'
    assert 'no-store' in resp_page.headers.get('Cache-Control')

    # Validação do download
    resp_down = client.get('/ferramentas/prompt-gateway/descarregar')
    assert resp_down.status_code == 200
    assert resp_down.headers.get('Content-Type') == 'text/plain; charset=utf-8'
    assert 'prompt-gateway-sms-ussd.txt' in resp_down.headers.get('Content-Disposition')
    assert len(resp_down.content) > 100

@pytest.mark.django_db
def test_prompt_gateway_financeiro(client, financeiro_user):
    """Com perfil Financeiro: acesso autorizado."""
    client.force_login(financeiro_user)

    resp_page = client.get('/ferramentas/prompt-gateway')
    assert resp_page.status_code == 200
    assert 'Gateway SMS, USSD' in resp_page.content.decode('utf-8')

@pytest.mark.django_db
def test_prompt_gateway_ficheiro_em_falta(client, superadmin_user):
    """Ficheiro de conteúdo em falta: resposta 500 genérica sem vazar caminhos internos."""
    client.force_login(superadmin_user)

    with patch('apps.ferramentas.views._ler_conteudo_prompt', return_value=None):
        resp_page = client.get('/ferramentas/prompt-gateway')
        assert resp_page.status_code == 500
        html = resp_page.content.decode('utf-8')
        assert '500 — Ocorreu um erro' in html
        assert 'Traceback' not in html
        assert 'Exception' not in html
        assert 'prompt-gateway.txt' not in html


@pytest.fixture
def escola_teste(db):
    plano, _ = Plano.objects.get_or_create(nome='PLANO_TESTE_GW', defaults={'preco': 1000, 'duracao_dias': 30})
    esc, _ = Escola.objects.get_or_create(
        nome='Escola Secundária de Massinga',
        defaults={'nif_cnpj': 'NIF_GW_001', 'email': 'massinga.gw@sige.edu.mz', 'status': 'ATIVA', 'plano': plano}
    )
    return esc


@pytest.fixture
def turma_teste(db, escola_teste):
    turma, _ = Turma.objects.get_or_create(escola=escola_teste, nome='10ª A - GW', defaults={'grau_ano': '10ª'})
    return turma


@pytest.fixture
def aluno_teste(db, escola_teste, turma_teste):
    aluno, _ = Aluno.objects.get_or_create(
        matricula='MAT-GW-001',
        defaults={
            'escola': escola_teste,
            'turma': turma_teste,
            'nome': 'Armando',
            'apelido': 'Guebuza',
            'contato_responsavel': '841234567',
            'data_nascimento': '2008-01-01',
            'genero': 'M',
            'status': 'ATIVO'
        }
    )
    return aluno


@pytest.fixture
def pagamento_pendente_teste(db, escola_teste, aluno_teste):
    pag, _ = Pagamento.objects.get_or_create(
        escola=escola_teste,
        aluno=aluno_teste,
        descricao='Propina de Outubro 2026',
        defaults={
            'mes_referencia': '2026-10',
            'valor': Decimal('1200.00'),
            'status': 'PENDENTE',
            'data_vencimento': timezone.now().date() + timezone.timedelta(days=15)
        }
    )
    return pag


@pytest.mark.django_db
def test_api_gateway_stats(client, superadmin_user, aluno_user):
    """Testa endpoint de métricas e estado das operadoras."""
    # Sem autenticação
    resp_anon = client.get('/api/v1/ferramentas/stats/')
    assert resp_anon.status_code == 401

    # Sem permissão (ALUNO)
    client.force_login(aluno_user)
    resp_aluno = client.get('/api/v1/ferramentas/stats/')
    assert resp_aluno.status_code == 403

    # Superadmin
    client.force_login(superadmin_user)
    resp = client.get('/api/v1/ferramentas/stats/')
    assert resp.status_code == 200
    dados = resp.json()
    assert dados['success'] is True
    assert 'operadoras' in dados
    assert dados['saldo_creditos_sms'] >= 0


@pytest.mark.django_db
def test_api_enviar_sms_unitario(client, superadmin_user, escola_teste):
    """Testa envio de SMS unitário com normalização de número de Moçambique."""
    client.force_login(superadmin_user)

    payload = {
        'modo': 'MANUAL',
        'destinatarios': '841234567',
        'mensagem': 'SIGE: Informamos que a reunião terá lugar amanhã.',
        'tipo': 'AVISO'
    }
    resp = client.post('/api/v1/ferramentas/sms/enviar/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    dados = resp.json()
    assert dados['success'] is True
    assert dados['total_enviados'] == 1
    assert dados['operadoras']['VODACOM'] == 1

    # Valida registo na base de dados
    msg = MensagemSMS.objects.filter(destinatario='+258841234567').first()
    assert msg is not None
    assert msg.operadora == 'VODACOM'
    assert msg.status == 'ENTREGUE'
    assert msg.segmentos_sms == 1


@pytest.mark.django_db
def test_api_enviar_sms_lote_turma(client, superadmin_user, turma_teste, aluno_teste):
    """Testa envio de SMS em lote por turma escolar."""
    client.force_login(superadmin_user)

    payload = {
        'modo': 'TURMA',
        'turma_id': str(turma_teste.id),
        'mensagem': 'Prezados pais da turma, o trimestre termina nesta sexta.',
        'tipo': 'AVISO'
    }
    resp = client.post('/api/v1/ferramentas/sms/enviar/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    dados = resp.json()
    assert dados['success'] is True
    assert dados['total_enviados'] >= 1


@pytest.mark.django_db
def test_api_enviar_sms_validacao(client, superadmin_user):
    """Testa validações de parâmetros e número no envio de SMS."""
    client.force_login(superadmin_user)

    # Mensagem vazia
    resp = client.post('/api/v1/ferramentas/sms/enviar/', data=json.dumps({'modo': 'MANUAL', 'destinatarios': '841234567', 'mensagem': ''}), content_type='application/json')
    assert resp.status_code == 400

    # Número não informado
    resp2 = client.post('/api/v1/ferramentas/sms/enviar/', data=json.dumps({'modo': 'MANUAL', 'destinatarios': '', 'mensagem': 'Olá'}), content_type='application/json')
    assert resp2.status_code == 400


@pytest.mark.django_db
def test_api_iniciar_pagamento_movel_mpesa(client, superadmin_user, aluno_teste, pagamento_pendente_teste):
    """Testa cobrança móvel via Vodacom M-Pesa com liquidação automática e recibo."""
    client.force_login(superadmin_user)

    payload = {
        'metodo': 'MPESA',
        'telefone': '841234567',
        'valor': 1200,
        'aluno_id': str(aluno_teste.id),
        'pagamento_id': str(pagamento_pendente_teste.id),
        'descricao': 'Propina Escolar de Outubro'
    }
    resp = client.post('/api/v1/ferramentas/pagamentos-moveis/iniciar/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    dados = resp.json()
    assert dados['success'] is True
    assert 'transacao' in dados
    assert dados['transacao']['metodo'] == 'MPESA'
    assert dados['transacao']['recibo'].startswith('REC-')

    # Valida atualização do pagamento na base de dados
    pagamento_pendente_teste.refresh_from_db()
    assert pagamento_pendente_teste.status == 'PAGO'
    assert pagamento_pendente_teste.metodo_pagamento == 'MPESA'
    assert pagamento_pendente_teste.recibo_numero.startswith('REC-')

    # Valida criação do registo em TransacaoGatewayMovel
    trx = TransacaoGatewayMovel.objects.filter(telefone='+258841234567', metodo='MPESA').first()
    assert trx is not None
    assert trx.status == 'CONCLUIDO'
    assert trx.valor == Decimal('1200.00')

    # Valida emissão automática do SMS de recibo
    sms_rec = MensagemSMS.objects.filter(destinatario='+258841234567', tipo='RECIBO').first()
    assert sms_rec is not None
    assert 'REC-' in sms_rec.mensagem


@pytest.mark.django_db
def test_api_iniciar_pagamento_movel_emola(client, superadmin_user, aluno_teste):
    """Testa cobrança móvel via Movitel e-Mola."""
    client.force_login(superadmin_user)

    payload = {
        'metodo': 'EMOLA',
        'telefone': '861234567',
        'valor': 850,
        'aluno_id': str(aluno_teste.id),
        'descricao': 'Taxa de Documentos'
    }
    resp = client.post('/api/v1/ferramentas/pagamentos-moveis/iniciar/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    dados = resp.json()
    assert dados['success'] is True
    assert dados['transacao']['metodo'] == 'EMOLA'

    trx = TransacaoGatewayMovel.objects.filter(telefone='+258861234567', metodo='EMOLA').first()
    assert trx is not None
    assert trx.valor == Decimal('850.00')


@pytest.mark.django_db
def test_api_iniciar_pagamento_movel_validacoes(client, superadmin_user):
    """Testa validações de prefixo de rede e valores inválidos."""
    client.force_login(superadmin_user)

    # M-Pesa com número Movitel (86) deve falhar com 400
    resp_mpesa_err = client.post(
        '/api/v1/ferramentas/pagamentos-moveis/iniciar/',
        data=json.dumps({'metodo': 'MPESA', 'telefone': '861234567', 'valor': 500}),
        content_type='application/json'
    )
    assert resp_mpesa_err.status_code == 400

    # e-Mola com número Vodacom (84) deve falhar com 400
    resp_emola_err = client.post(
        '/api/v1/ferramentas/pagamentos-moveis/iniciar/',
        data=json.dumps({'metodo': 'EMOLA', 'telefone': '841234567', 'valor': 500}),
        content_type='application/json'
    )
    assert resp_emola_err.status_code == 400

    # Valor zero ou negativo deve falhar com 400
    resp_val_err = client.post(
        '/api/v1/ferramentas/pagamentos-moveis/iniciar/',
        data=json.dumps({'metodo': 'MPESA', 'telefone': '841234567', 'valor': -10}),
        content_type='application/json'
    )
    assert resp_val_err.status_code == 400


@pytest.mark.django_db
def test_api_simulador_ussd_menu_e_subopcoes(client, superadmin_user, aluno_teste, pagamento_pendente_teste):
    """Testa o simulador interativo USSD (*...#) para consulta e pagamentos."""
    client.force_login(superadmin_user)

    # Menu Principal
    resp_menu = client.post(
        '/api/v1/ferramentas/ussd/simular/',
        data=json.dumps({'text': '', 'phoneNumber': '+258841234567'}),
        content_type='application/json'
    )
    assert resp_menu.status_code == 200
    dados = resp_menu.json()
    assert dados['type'] == 'CON'
    assert '1. Consultar Notas' in dados['response']
    assert '2. Propinas' in dados['response']

    # Submenu 1: Solicitação de Matrícula
    resp_sub1 = client.post(
        '/api/v1/ferramentas/ussd/simular/',
        data=json.dumps({'text': '1', 'phoneNumber': '+258841234567'}),
        content_type='application/json'
    )
    assert 'CON Digite o' in resp_sub1.json()['response']
    assert 'Matr' in resp_sub1.json()['response']

    # Submenu 1 com matrícula do aluno
    resp_sub1_aluno = client.post(
        '/api/v1/ferramentas/ussd/simular/',
        data=json.dumps({'text': f'1*{aluno_teste.matricula}', 'phoneNumber': '+258841234567'}),
        content_type='application/json'
    )
    assert resp_sub1_aluno.status_code == 200
    assert resp_sub1_aluno.json()['type'] == 'END'
    assert aluno_teste.nome in resp_sub1_aluno.json()['response']

    # Submenu 5: Contactos da Secretaria
    resp_sub5 = client.post(
        '/api/v1/ferramentas/ussd/simular/',
        data=json.dumps({'text': '5', 'phoneNumber': '+258841234567'}),
        content_type='application/json'
    )
    assert resp_sub5.status_code == 200
    assert resp_sub5.json()['type'] == 'END'
    assert 'Secretaria' in resp_sub5.json()['response']


@pytest.mark.django_db
def test_api_enviar_whatsapp(client, superadmin_user, aluno_teste):
    """Testa geração de link directo wa.me e registo de mensagem WhatsApp."""
    client.force_login(superadmin_user)

    payload = {
        'telefone': '841234567',
        'mensagem': 'SIGE Massinga: Aviso de propinas do estudante.',
        'aluno_id': str(aluno_teste.id),
        'tipo': 'PROPINA'
    }
    resp = client.post('/api/v1/ferramentas/whatsapp/enviar/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    dados = resp.json()
    assert dados['success'] is True
    assert 'wa_link' in dados
    assert 'wa.me/258841234567' in dados['wa_link']

    # Valida persistência
    msg_wa = MensagemWhatsApp.objects.filter(destinatario='+258841234567').first()
    assert msg_wa is not None
    assert msg_wa.status == 'ENVIADO'


@pytest.mark.django_db
def test_api_liquidar_pagamento_manual(client, superadmin_user, aluno_teste, pagamento_pendente_teste):
    """Testa liquidação manual de propina com inserção de comprovativo ou código bancário."""
    client.force_login(superadmin_user)

    payload = {
        'pagamento_id': str(pagamento_pendente_teste.id),
        'aluno_id': str(aluno_teste.id),
        'metodo': 'TRANSFERENCIA',
        'referencia_transacao': 'TRF-BIM-998877',
        'valor': 1200,
        'observacoes': 'Comprovativo de depósito Millennium BIM validado pela secretaria.'
    }
    resp = client.post('/api/v1/ferramentas/pagamentos/liquidar-manual/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    dados = resp.json()
    assert dados['success'] is True
    assert dados['recibo'].startswith('REC-')

    # Valida atualização do modelo Pagamento
    pagamento_pendente_teste.refresh_from_db()
    assert pagamento_pendente_teste.status == 'PAGO'
    assert pagamento_pendente_teste.metodo_pagamento == 'TRANSFERENCIA'
    assert pagamento_pendente_teste.recibo_numero.startswith('REC-')

    # Valida registo em TransacaoGatewayMovel
    trx = TransacaoGatewayMovel.objects.filter(referencia_transacao='TRF-BIM-998877').first()
    assert trx is not None
    assert trx.status == 'CONCLUIDO'


@pytest.mark.django_db
def test_api_reconciliacao_sms_webhook_mpesa(client, aluno_teste, pagamento_pendente_teste):
    """Testa processamento de SMS oficial de confirmação do M-Pesa recebido no telemóvel da escola."""
    sms_texto_real = (
        "Confirmado. Recebeu 1,200.00MT de 841234567 - ARMANDO GUEBUZA aos 18/10/2026 as 10:20. "
        "Ref: PP261018.1023.A12345. Saldo actual: 25,400.00MT."
    )
    payload = {
        'from': 'MPesa',
        'message': sms_texto_real
    }
    resp = client.post('/api/v1/ferramentas/reconciliacao/sms-webhook/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    dados = resp.json()
    assert dados['success'] is True
    assert dados['status'] == 'RECONCILIADO'
    assert dados['valor'] == 1200.0
    assert dados['codigo_transacao'] == 'PP261018.1023.A12345'
    assert dados['recibo'].startswith('REC-')

    # Valida liquidação da propina do aluno correspondente
    pagamento_pendente_teste.refresh_from_db()
    assert pagamento_pendente_teste.status == 'PAGO'
    assert pagamento_pendente_teste.recibo_numero == dados['recibo']

    # Valida prevenção de duplicação caso o mesmo SMS seja retransmitido
    resp_dup = client.post('/api/v1/ferramentas/reconciliacao/sms-webhook/', data=json.dumps(payload), content_type='application/json')
    assert resp_dup.status_code == 200
    assert resp_dup.json()['status'] == 'DUPLICADO'


@pytest.mark.django_db
def test_api_configuracao_gateway(client, superadmin_user, escola_teste):
    """Testa consulta e salvamento de configurações do gateway (Android, WhatsApp e M-Pesa)."""
    client.force_login(superadmin_user)

    # Obter configuração inicial
    resp_get = client.get('/api/v1/ferramentas/configuracao/')
    assert resp_get.status_code == 200
    assert resp_get.json()['success'] is True

    # Salvar nova configuração com URL do telemóvel Android da escola
    payload = {
        'modo_sms': 'ANDROID_GATEWAY',
        'android_gateway_url': 'http://192.168.1.50:8080/message',
        'whatsapp_ativo': True,
        'mpesa_shortcode': '123456'
    }
    resp_post = client.post('/api/v1/ferramentas/configuracao/', data=json.dumps(payload), content_type='application/json')
    assert resp_post.status_code == 200
    assert resp_post.json()['success'] is True

    cfg = ConfiguracaoGateway.objects.first()
    assert cfg is not None
    assert cfg.android_gateway_url == 'http://192.168.1.50:8080/message'
    assert cfg.modo_sms == 'ANDROID_GATEWAY'


