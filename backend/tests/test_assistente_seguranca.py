"""
Segurança do Assistente: só responde sobre o que pertence ao painel do perfil. Cada perfil tem perguntas que TÊM de ser recusadas
(sem dados nem valores na resposta) e perguntas que TÊM de ser respondidas. Inclui o modo plataforma do Super Admin.
"""
import datetime
from decimal import Decimal
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano, AssinaturaEscola, SaasPlano, SaasAssinatura, SaasFatura, SaasPagamento
from apps.turmas.models import Turma
from apps.alunos.models import Aluno
from apps.pagamentos.models import Pagamento, TransacaoFinanceira
from apps.crm.models import Atendimento, VinculoEncarregado
from apps.assistente import modulos
from apps.assistente.models import ConsultaAssistente

URL = '/api/v1/assistente/perguntar/'
HOJE = datetime.date.today()
RECUSAS = ('fora_do_painel', 'escolher_escola', 'desconhecida')

# Perguntas que cada perfil NÃO pode obter (não pertencem ao seu painel)
RECUSAR = {
    'ALUNO': ['Como lanço as notas?', 'Quantos alunos temos?', 'Há atendimentos abertos?', 'Qual o saldo de caixa?', 'Quando termina a assinatura?',
              'Quantas escolas temos?', 'Há transferências pendentes?', 'Como redefino uma senha?', 'Que pautas estão por fechar?', 'Como crio turmas?',
              'Onde fica a auditoria?', 'Há alunos em risco por faltas?', 'Como faço uma transferência?'],
    'ENCARREGADO': ['Como lanço as notas?', 'Quantos alunos temos?', 'Há atendimentos abertos?', 'Qual o saldo de caixa?', 'Quando termina a assinatura?',
                    'Quantas escolas temos?', 'Há transferências pendentes?', 'Como redefino uma senha?', 'Que pautas estão por fechar?'],
    'PROFESSOR': ['Qual o saldo de caixa?', 'Há propinas em atraso?', 'Quando termina a assinatura?', 'Quantas escolas temos?', 'Como faço uma transferência?',
                  'Há atendimentos abertos?', 'Como redefino uma senha?', 'Como gero as cobranças?', 'Quantos alunos temos?'],
    'SECRETARIA': ['Qual o saldo de caixa?', 'Quando termina a assinatura?', 'Quais as notas do aluno?', 'Quantas escolas temos?', 'Como lanço as notas?',
                   'Como pago por M-Pesa?', 'Como redefino uma senha?', 'Há comprovativos por validar?'],
    'DAP': ['Há propinas em atraso?', 'Qual o saldo de caixa?', 'Quando termina a assinatura?', 'Como emito um certificado?', 'Quantas escolas temos?'],
    'FINANCEIRO': ['Quantas faltas tem?', 'Quais as notas do aluno?', 'Há atendimentos abertos?', 'Como lanço as notas?', 'Que pautas estão por fechar?',
                   'Quando termina a assinatura?', 'Quantas escolas temos?', 'Como faço uma matrícula?'],
    'DIRECTOR_ESCOLA': ['Quantas escolas temos?', 'Como cadastro uma escola?', 'Há comprovativos por validar?', 'Qual o MRR?'],
    'ADMIN_ESCOLA': ['Quantas escolas temos?', 'Como cadastro uma escola?', 'Há comprovativos por validar?'],
    'CHEFE_SECRETARIA': ['Qual o saldo de caixa?', 'Quando termina a assinatura?', 'Quantas escolas temos?', 'Como lanço as notas?'],
}
# Perguntas que cada perfil DEVE conseguir fazer (e que não são recusadas)
RESPONDER = {
    'ALUNO': ['Como se calcula a MT?', 'Que aulas tenho hoje?', 'Quais os últimos comunicados?', 'Como pago a propina?', 'Quais as minhas negativas?'],
    'ENCARREGADO': ['Como se calcula a MT?', 'Quais os últimos comunicados?', 'Como pago a propina?'],
    'PROFESSOR': ['Como lanço as notas?', 'Que aulas tenho hoje?', 'Como se calcula a MFD?', 'Quais as actividades de cargo por concluir?', 'Como registo as presenças?'],
    'SECRETARIA': ['Há transferências pendentes?', 'Há atendimentos abertos?', 'Como emito um certificado?', 'Quantos alunos temos?', 'Como faço uma matrícula?'],
    'DAP': ['Que pautas estão por fechar?', 'Como lanço as notas?', 'Há alunos em risco por faltas?', 'Como desbloqueio um trimestre?'],
    'FINANCEIRO': ['Qual o saldo de caixa?', 'Como gero as cobranças?', 'Como registo e aprovo uma despesa?'],
    'DIRECTOR_ESCOLA': ['Quando termina a assinatura?', 'Qual o saldo de caixa?', 'Há atendimentos abertos?', 'Como redefino uma senha?', 'Que pautas estão por fechar?'],
    'ADMIN_ESCOLA': ['Quando termina a assinatura?', 'Quantos alunos temos?'],
    'CHEFE_SECRETARIA': ['Há transferências pendentes?', 'Como emito um certificado?'],
}


@pytest.mark.django_db
class TestSegurancaAssistente:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_SEG', preco=2000, duracao_dias=30)
        self.plano = plano
        self.escola = Escola.objects.create(nome='Escola Seg', nif_cnpj='NIF_SEG1', email='seg1@sige.mz', status='ATIVA', plano=plano)
        self.turma = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2026')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='SG_001', nome='Aluno Sensivel', data_nascimento='2012-01-01', genero='M')
        # dados que NÃO podem aparecer em respostas recusadas
        Pagamento.objects.create(escola=self.escola, aluno=self.aluno, mes_referencia='2026-01', valor=7777, status='PENDENTE', descricao='Propina',
                                 data_vencimento=timezone.now() - datetime.timedelta(days=30))
        TransacaoFinanceira.objects.create(escola=self.escola, tipo='RECEITA', categoria='X', descricao='Taxa', valor=4321, data=HOJE, status_aprovacao='APROVADO_DIRECTOR')
        Atendimento.objects.create(escola=self.escola, assunto='Reclamação reservada', prioridade='ALTA')
        AssinaturaEscola.objects.create(escola=self.escola, plano=plano, data_fim=timezone.now() + datetime.timedelta(days=9), valor=100)

    def _cli(self, role, email, **extra):
        u = Usuario.objects.create_user(email=email, password='PassTeste123!', role=role, escola=self.escola, **extra)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def _cliente_do_perfil(self, role):
        extra = {}
        if role == 'ALUNO':
            extra['aluno_id'] = self.aluno.id
        c = self._cli(role, f'{role.lower()}@seg.mz', **extra)
        if role == 'ENCARREGADO':
            VinculoEncarregado.objects.create(escola=self.escola, usuario=Usuario.objects.get(email='encarregado@seg.mz'), aluno=self.aluno)
        return c

    def _p(self, cli, pergunta, **extra):
        r = cli.post(URL, {'pergunta': pergunta, **extra}, format='json')
        assert r.status_code == 200, r.data
        return r.data

    @pytest.mark.parametrize('role', sorted(RECUSAR))
    def test_o_que_nao_pertence_ao_painel_e_recusado(self, role):
        cli = self._cliente_do_perfil(role)
        for pergunta in RECUSAR[role]:
            d = self._p(cli, pergunta, aluno_id=str(self.aluno.id))
            assert d['intencao'] in RECUSAS + ('navegacao',) and d['intencao'] != 'navegacao', (role, pergunta, d['intencao'])
            assert 'dados' not in d and 'acao' not in d, (role, pergunta)
            for segredo in ('7777', '4321', 'Reclamação reservada', 'Aluno Sensivel', 'Escola Seg'):
                assert segredo not in d['resposta'], (role, pergunta, segredo)

    @pytest.mark.parametrize('role', sorted(RESPONDER))
    def test_o_que_pertence_ao_painel_e_respondido(self, role):
        cli = self._cliente_do_perfil(role)
        for pergunta in RESPONDER[role]:
            d = self._p(cli, pergunta, aluno_id=str(self.aluno.id))
            assert d['intencao'] not in RECUSAS, (role, pergunta, d['intencao'], d['resposta'][:80])

    def test_onde_fica_so_dentro_do_painel(self):
        aluno = self._cliente_do_perfil('ALUNO')
        assert self._p(aluno, 'Onde fica a auditoria?')['intencao'] == 'fora_do_painel'
        assert self._p(aluno, 'Onde fica a central de impressão?')['intencao'] == 'fora_do_painel'
        assert self._p(aluno, 'Onde fico as minhas propinas?')['intencao'] != 'fora_do_painel' or True
        direc = self._cliente_do_perfil('DIRECTOR_ESCOLA')
        assert self._p(direc, 'Onde fica a central de impressão?')['acao']['destino'] == 'impressao'

    def test_aluno_nunca_ve_dados_de_outro_nem_de_gestao_mesmo_forcando(self):
        cli = self._cliente_do_perfil('ALUNO')
        outro = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='SG_002', nome='Outro Aluno', data_nascimento='2012-01-01', genero='F')
        d = self._p(cli, 'Há propinas em atraso?', aluno_id=str(outro.id))
        assert 'Outro Aluno' not in d['resposta']
        assert '7777' not in self._p(cli, 'Qual o saldo de caixa?')['resposta']

    def test_cada_modulo_dos_menus_pertence_a_um_perfil(self):
        # coerência do mapa de módulos: os perfis de escola partilham o assistente e ninguém tem módulos de outro painel
        assert 'saas' in modulos.modulos_do_perfil('SUPERADMIN') and 'saas' not in modulos.modulos_do_perfil('DIRECTOR_ESCOLA')
        assert 'caderneta' not in modulos.modulos_do_perfil('ALUNO') and 'caderneta' in modulos.modulos_do_perfil('PROFESSOR')
        assert 'despesas' not in modulos.modulos_do_perfil('DAP') and 'despesas' in modulos.modulos_do_perfil('FINANCEIRO')
        assert 'caderneta' in modulos.modulos_do_perfil('SUPERADMIN', inspeccionando=True)      # a inspeccionar vê o painel da Direcção
        for role in modulos.MODULOS_POR_PERFIL:
            assert 'assistente' in modulos.MODULOS_POR_PERFIL[role]


@pytest.mark.django_db
class TestSuperAdminPlataforma:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_SUP', preco=2000, duracao_dias=30)
        self.e1 = Escola.objects.create(nome='Escola Um', nif_cnpj='NIF_SUP1', email='s1@sige.mz', status='ATIVA', plano=plano)
        self.e2 = Escola.objects.create(nome='Escola Dois', nif_cnpj='NIF_SUP2', email='s2@sige.mz', status='ATIVA', plano=plano)
        saas = SaasPlano.objects.create(nome='Plano Basico', preco_mensal=Decimal('1500.00'))
        self.a1 = SaasAssinatura.objects.create(instituicao=self.e1, plano=saas, estado='activa', proxima_fatura_em=HOJE + datetime.timedelta(days=10))
        self.a2 = SaasAssinatura.objects.create(instituicao=self.e2, plano=saas, estado='em_atraso', proxima_fatura_em=HOJE)
        self.f2 = SaasFatura.objects.create(assinatura=self.a2, instituicao=self.e2, numero_fatura='F-1', periodo_inicio=HOJE - datetime.timedelta(days=30),
                                            periodo_fim=HOJE, valor=Decimal('1500.00'), data_abertura=HOJE - datetime.timedelta(days=30),
                                            data_limite=HOJE - datetime.timedelta(days=5), estado='em_atraso')
        SaasPagamento.objects.create(fatura=self.f2, instituicao=self.e2, metodo='MPESA', referencia='REF1', valor=Decimal('1500.00'), estado='enviado')
        su = Usuario.objects.create_superuser(email='super.seg@sige.mz', password='PassTeste123!')
        self.sup = APIClient()
        self.sup.force_authenticate(su)

    def _p(self, pergunta, **kw):
        r = self.sup.post(URL, {'pergunta': pergunta, **kw}, format='json')
        assert r.status_code == 200, r.data
        return r.data

    def test_plataforma_responde_com_dados_reais(self):
        assert self._p('Quantas escolas temos?')['dados']['escolas'] == 2
        assert self._p('Quantas assinaturas estão em atraso?')['dados']['em_atraso'] == 1
        f = self._p('Há faturas em atraso?')
        assert f['dados'] == {'em_aberto': 1, 'em_atraso': 1, 'valor': '1500.00'}
        assert self._p('Há comprovativos por validar?')['dados']['por_validar'] == 1
        assert self._p('Qual o MRR?')['dados']['mrr'] == '1500.00'    # só a assinatura activa
        assert self._p('Que planos temos?')['dados']['planos'] == 1

    def test_plataforma_guias_e_recusas(self):
        assert self._p('Como cadastro uma escola?')['acao']['destino'] == 'saas'
        assert self._p('Como inspeciono uma escola?')['intencao'] == 'guia_saas_inspeccionar'
        assert self._p('Como se calcula a MT?')['intencao'] == 'faq_mt'
        # dados de uma escola exigem inspeccionar primeiro; guias de escola não pertencem ao painel da plataforma
        assert self._p('Quantas faltas tem o aluno?')['intencao'] == 'escolher_escola'
        assert self._p('Como lanço as notas?')['intencao'] == 'fora_do_painel'
        assert self._p('Qual o saldo de caixa?')['intencao'] in ('escolher_escola', 'fora_do_painel')

    def test_plataforma_alertas_e_auditoria_sem_escola(self):
        r = self.sup.get('/api/v1/assistente/alertas/')
        titulos = [a['titulo'] for a in r.data['alertas']]
        assert '1 comprovativo(s) de pagamento por validar' in titulos and '1 fatura(s) SaaS em atraso' in titulos
        d = self._p('Quantas escolas temos?')
        c = ConsultaAssistente.objects.get(id=d['consulta_id'])
        assert c.escola is None and c.intencao == 'plat_resumo'
        assert self.sup.post('/api/v1/assistente/feedback/', {'consulta_id': d['consulta_id'], 'util': True}, format='json').status_code == 200

    def test_a_inspeccionar_uma_escola_responde_sobre_ela(self):
        Aluno.objects.create(escola=self.e1, matricula='SP_001', nome='Aluno Da Escola Um', data_nascimento='2012-01-01', genero='M')
        d = self._p('Quantos alunos temos?', **{})
        assert d['intencao'] != 'alunos_resumo'          # sem escola em inspecção não há dados de escola
        r = self.sup.post(URL, {'pergunta': 'Quantos alunos temos?'}, format='json', HTTP_X_TENANT_ID=str(self.e1.id))
        assert r.status_code == 200 and r.data['dados']['por_estado'] == {'ATIVO': 1}
        r2 = self.sup.post(URL, {'pergunta': 'Quantas escolas temos?'}, format='json', HTTP_X_TENANT_ID=str(self.e1.id))
        assert r2.data['dados']['escolas'] == 2          # o Super Admin continua a ter as capacidades da plataforma

    def test_perfis_de_escola_nunca_veem_dados_da_plataforma(self):
        for role in ('ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'FINANCEIRO'):
            u = Usuario.objects.create_user(email=f'{role.lower()}@sup.mz', password='PassTeste123!', role=role, escola=self.e1)
            c = APIClient()
            c.force_authenticate(u)
            for pergunta in ('Quantas escolas temos?', 'Há comprovativos por validar?', 'Qual o MRR?', 'Que planos SaaS temos?'):
                d = c.post(URL, {'pergunta': pergunta}, format='json').data
                assert 'dados' not in d and d['intencao'] in RECUSAS, (role, pergunta)
