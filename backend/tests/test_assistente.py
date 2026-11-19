import datetime
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano, AssinaturaEscola
from apps.turmas.models import Turma, HorarioEscolar
from apps.alunos.models import Aluno, PresencaAluno, TransferenciaAnulacao
from apps.pagamentos.models import Pagamento, TransacaoFinanceira
from apps.disciplinas.models import Disciplina
from apps.notas.models import Nota, CalendarioExame
from apps.documentos.models import CalendarioEscolar, ComunicadoEscolar
from apps.professores.models import Professor, AlocacaoDocente
from apps.atribuicoes.models import AtribuicaoCargo
from apps.crm.models import Atendimento
from apps.assistente.models import ConsultaAssistente
from apps.assistente.engine import classificar

URL = '/api/v1/assistente/perguntar/'
HOJE = datetime.date.today()


@pytest.mark.django_db
class TestAssistente:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_ASS', preco=2000, duracao_dias=30)
        self.plano = plano
        self.escola = Escola.objects.create(nome='Escola Ass', nif_cnpj='NIF_ASS1', email='ass1@sige.mz', status='ATIVA', plano=plano)
        self.outra = Escola.objects.create(nome='Outra Ass', nif_cnpj='NIF_ASS2', email='ass2@sige.mz', status='ATIVA', plano=plano)
        self.turma = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2026', capacidade_maxima=2)
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='AS_001', nome='Aluno Um',
                                          data_nascimento='2012-01-01', genero='M')
        self.outro_aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='AS_002', nome='Aluno Dois',
                                                data_nascimento='2012-01-01', genero='F')
        self.aluno_outra = Aluno.objects.create(escola=self.outra, matricula='AS_003', nome='Aluno Outra',
                                                data_nascimento='2012-01-01', genero='F')
        self.sec = self._cliente('SECRETARIA', 'sec.ass@sige.mz')

    def _cliente(self, role, email, **extra):
        u = Usuario.objects.create_user(email=email, password='PassTeste123!', role=role, escola=self.escola, **extra)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def _p(self, cli, pergunta, **extra):
        return cli.post(URL, {'pergunta': pergunta, **extra}, format='json')

    def _r(self, cli, pergunta, **extra):
        r = self._p(cli, pergunta, **extra)
        assert r.status_code == 200, r.data
        return r.data

    # ------------------------------------------------------------ classificação
    def test_classificacao(self):
        casos = {
            'Quantas faltas tem o aluno?': 'faltas', 'Há propinas em atraso?': 'propinas', 'Como se calcula a MFD?': 'faq_mfd',
            'Regras de aprovação da 12ª classe': 'faq_aprovacao', 'Quanto preciso para passar?': 'quanto_preciso',
            'Quais as minhas negativas?': 'notas', 'Que turmas estão lotadas?': 'turmas', 'Quantos alunos temos?': 'alunos_resumo',
            'Quando são os exames?': 'exames_calendario', 'Qual a nota mínima do exame?': 'faq_exames', 'Há atendimentos abertos?': 'crm',
            'Quando termina a assinatura?': 'assinatura', 'Qual o saldo de caixa deste mês?': 'caixa', 'Há alunos em risco por faltas?': 'risco',
            'Como lanço as notas?': 'guia_lancar_notas', 'Como faço uma transferência?': 'guia_transferencia', 'Como pago por M-Pesa?': 'guia_pagar_propina',
            'Como redefino uma senha?': 'guia_senhas', 'Como emito um certificado?': 'guia_certificados', 'Como gero as cobranças?': 'guia_cobrar_propina',
            'Como faço uma matrícula?': 'guia_matricula', 'Como crio turmas em lote?': 'guia_turmas', 'Como registo presenças?': 'guia_registar_presencas',
            'Como funcionam as faltas em aula dupla?': 'aula_dupla', 'Como se calcula a média trimestral (MT)?': 'faq_mt',
            'Que aulas tenho hoje?': 'horario', 'Quais os últimos comunicados?': 'comunicados', 'qual a capital da França': 'desconhecida',
        }
        for pergunta, esperado in casos.items():
            assert classificar(pergunta)[0] == esperado, pergunta

    def test_onde_fica_devolve_atalho(self):
        d = self._r(self.sec, 'Onde fica a central de impressão?')
        assert d['intencao'] == 'navegacao' and d['acao']['destino'] == 'impressao'

    # ------------------------------------------------------------ regras e guias
    def test_regras_e_guias_sem_aluno(self):
        d = self._r(self.sec, 'Como se calcula a média trimestral (MT)?')
        assert '2 × MAC' in d['resposta'] and 'acao' not in d
        assert 'no máximo 2' in self._r(self.sec, 'Qual a regra de aprovação na 12ª classe?')['resposta']
        g = self._r(self.sec, 'Como lanço as notas?')
        assert 'Só o professor lança notas' in g['resposta'] and g['acao']['destino'] == 'caderneta'
        assert self._r(self.sec, 'Como faço uma transferência?')['acao']['destino'] == 'transferencias'

    def test_desconhecida_nao_inventa(self):
        d = self._r(self.sec, 'qual a capital da França')
        assert d['intencao'] == 'desconhecida' and 'Ainda não sei' in d['resposta']

    # ------------------------------------------------------------ faltas e propinas (regressão)
    def test_faltas_pede_aluno_estado_vazio_e_aula_dupla(self):
        assert self._r(self.sec, 'Quantas faltas tem?')['precisa_aluno'] is True
        d = self._r(self.sec, 'Quantas faltas tem?', aluno_id=str(self.aluno.id))
        assert d['dados']['faltas_efectivas'] == 0
        PresencaAluno.objects.create(escola=self.escola, aluno=self.aluno, turma=self.turma, data=HOJE, status='FALTA_INJUSTIFICADA',
                                     aulas=2, aulas_justificadas=1)
        assert self._r(self.sec, 'Quantas faltas tem?', aluno_id=str(self.aluno.id))['dados'] == {'faltas_efectivas': 1, 'por_justificar': 1}

    def test_propinas_reais(self):
        assert self._r(self.sec, 'tem propinas em atraso?', aluno_id=str(self.aluno.id))['dados']['em_atraso'] == 0
        Pagamento.objects.create(escola=self.escola, aluno=self.aluno, mes_referencia='2026-01', valor=1000, status='PENDENTE',
                                 descricao='Propina 2026-01', data_vencimento=timezone.now() - datetime.timedelta(days=30))
        d = self._r(self.sec, 'tem propinas em atraso?', aluno_id=str(self.aluno.id))
        assert d['dados']['em_atraso'] == 1 and d['dados']['valor_em_atraso'] == '1000.00'

    # ------------------------------------------------------------ notas e "quanto preciso"
    def _notas(self, disc, mt1, mt2=None, mt3=None):
        for per, v in (('1_TRIMESTRE', mt1), ('2_TRIMESTRE', mt2), ('3_TRIMESTRE', mt3)):
            if v:
                Nota.objects.create(escola=self.escola, aluno=self.aluno, disciplina=disc, turma=self.turma, periodo=per, media_final=v)

    def _disc(self, nome, codigo, classe='7ª Classe', area='Geral'):
        return Disciplina.objects.create(escola=self.escola, nome=nome, codigo=codigo, classe=classe, area=area, ano_letivo='2026')

    def test_notas_e_negativas_vazio_e_real(self):
        d = self._r(self.sec, 'Quais as notas do aluno?', aluno_id=str(self.aluno.id))
        assert 'ainda não tem notas' in d['resposta']
        mat, fis = self._disc('Matemática', 'MAT'), self._disc('Física', 'FIS')
        self._notas(mat, 12), self._notas(fis, 8)
        d = self._r(self.sec, 'Quais as notas do aluno?', aluno_id=str(self.aluno.id))
        assert d['dados']['1_TRIMESTRE'] == {'avaliadas': 2, 'negativas': 1} and 'Física 8' in d['resposta']

    def test_quanto_preciso_para_passar(self):
        mat, fis, qui = self._disc('Matemática', 'MAT'), self._disc('Física', 'FIS'), self._disc('Química', 'QUI')
        self._notas(mat, 8, 9)      # 28,5 - 17 = 11,5 -> MT3 >= 12
        self._notas(fis, 14, 15)    # já garantida
        self._notas(qui, 2, 3)      # 28,5 - 5 = 23,5 -> impossível
        d = self._r(self.sec, 'Quanto preciso para passar?', aluno_id=str(self.aluno.id))
        assert d['dados']['precisa'] == {'Matemática': 12} and d['dados']['garantidas'] == 1 and d['dados']['impossiveis'] == ['Química']

    def test_aluno_so_ve_notas_publicadas(self):
        self._notas(self._disc('Matemática', 'MAT'), 12, 14)
        cli = self._cliente('ALUNO', 'aluno.notas@sige.mz', aluno_id=self.aluno.id)
        self.escola.publicacao_notas_trimestre = '1_TRIMESTRE'
        self.escola.save()
        d = self._r(cli, 'Quais as minhas notas?')
        assert list(d['dados']) == ['1_TRIMESTRE']
        self.escola.permitir_visualizacao_notas = False
        self.escola.save()
        assert 'suspensa' in self._r(cli, 'Quais as minhas notas?')['resposta']
        assert 'suspensa' in self._r(cli, 'Quanto preciso para passar?')['resposta']

    # ------------------------------------------------------------ dados da escola
    def test_alunos_e_turmas(self):
        d = self._r(self.sec, 'Quantos alunos temos?')
        assert d['dados']['por_estado'] == {'ATIVO': 2} and '1 H / 1 M' in d['resposta']
        t = self._r(self.sec, 'Que turmas estão lotadas?')
        assert t['dados']['lotadas'] == 1 and t['dados']['sem_director_turma'] == 1 and t['dados']['vagas'] == 0
        assert t['acao']['destino'] == 'turmas'
        assert self._r(self.sec, 'turmas da 9ª classe')['dados']['turmas'] == 0

    def test_horario_do_aluno_e_do_professor(self):
        prof = Professor.objects.create(escola=self.escola, nome='Prof', email='prof.hor@sige.mz', especialidade='Matemática')
        mat = self._disc('Matemática', 'MAT')
        dia = HOJE.isoweekday() if HOJE.isoweekday() < 7 else 1
        HorarioEscolar.objects.create(escola=self.escola, turma=self.turma, disciplina=mat, professor=prof, dia_semana=dia, tempo=1,
                                      hora_inicio='08:00', hora_fim='08:45', sala='3')
        aluno_cli = self._cliente('ALUNO', 'aluno.hor@sige.mz', aluno_id=self.aluno.id)
        d = self._r(aluno_cli, 'Que aulas tenho hoje?' if HOJE.isoweekday() < 7 else 'Que aulas tenho amanhã?')
        if HOJE.isoweekday() < 7:
            assert 'Matemática' in d['resposta'] and '08:00' in d['resposta']
        prof_cli = APIClient()
        prof_cli.force_authenticate(Usuario.objects.get(professor_id=prof.id))
        if HOJE.isoweekday() < 7:
            assert 'Matemática (A)' in self._r(prof_cli, 'Que aulas tenho hoje?')['resposta']
        assert 'página Horários' in self._r(self.sec, 'Que aulas tenho hoje?')['resposta']

    def test_calendario_e_exames(self):
        assert 'Não há eventos futuros' in self._r(self.sec, 'Quais os próximos eventos?')['resposta']
        CalendarioEscolar.objects.create(escola=self.escola, titulo='Início do 2.º trimestre', tipo='AVALIACAO_TESTE',
                                         data_inicio=HOJE + datetime.timedelta(days=5))
        assert 'Início do 2.º trimestre' in self._r(self.sec, 'Quais os próximos eventos?')['resposta']
        assert 'Não há exames agendados' in self._r(self.sec, 'Quando são os exames?')['resposta']
        CalendarioExame.objects.create(escola=self.escola, ano_letivo='2026', classe='10ª Classe', disciplina='Física', epoca=1,
                                       data=HOJE + datetime.timedelta(days=9), hora_inicio=datetime.time(8, 0), duracao_minutos=120)
        d = self._r(self.sec, 'Quando é o exame de Física?')
        assert '10ª Classe, Física' in d['resposta']
        assert 'Não há exames agendados' in self._r(self._cliente('ALUNO', 'aluno.ex@sige.mz', aluno_id=self.aluno.id), 'Quando são os exames?')['resposta']

    def test_transferencias_crm_assinatura_e_caixa(self):
        adm = Usuario.objects.create_user(email='dir.ass@sige.mz', password='PassTeste123!', role='DIRECTOR_ESCOLA', escola=self.escola)
        dirc = APIClient()
        dirc.force_authenticate(adm)
        assert 'Não há processos' in self._r(dirc, 'Há transferências pendentes?')['resposta']
        TransferenciaAnulacao.objects.create(escola=self.escola, aluno=self.aluno, tipo='ANULACAO_MATRICULA', motivo='desistência', solicitado_por=adm)
        assert self._r(dirc, 'Há transferências pendentes?')['dados']['pendentes'] == 1
        assert self._r(dirc, 'Há transferências pendentes?', aluno_id=str(self.aluno.id))['dados']['pendentes'] == 1  # resumo, mesmo com aluno
        assert 'Pendente' in self._r(dirc, 'Em que estado está a transferência deste aluno?', aluno_id=str(self.aluno.id))['resposta']

        assert 'Não há atendimentos' in self._r(dirc, 'Há atendimentos abertos?')['resposta']
        Atendimento.objects.create(escola=self.escola, assunto='Pedido', prioridade='ALTA')
        assert self._r(dirc, 'Há atendimentos abertos?')['dados'] == {'abertos': 1, 'em_curso': 0, 'antigos': 0, 'prioridade_alta': 1}

        assert 'Não há assinatura' in self._r(dirc, 'Quando termina a assinatura?')['resposta']
        AssinaturaEscola.objects.create(escola=self.escola, plano=self.plano, data_fim=timezone.now() + datetime.timedelta(days=10), valor=100)
        assert 'faltam 10 dia' in self._r(dirc, 'Quando termina a assinatura?')['resposta']

        assert 'Ainda não há movimentos' in self._r(dirc, 'Qual o saldo de caixa?')['resposta']
        TransacaoFinanceira.objects.create(escola=self.escola, tipo='RECEITA', categoria='Outras', descricao='Taxa', valor=500, data=HOJE,
                                           status_aprovacao='APROVADO_DIRECTOR')
        TransacaoFinanceira.objects.create(escola=self.escola, tipo='DESPESA', categoria='Material', descricao='Giz', valor=120, data=HOJE,
                                           status_aprovacao='APROVADO_DIRECTOR')
        assert 'saldo 380.00 MZN' in self._r(dirc, 'Qual o saldo de caixa?')['resposta']

    def test_risco_plano_curricular_material_cargos_pautas_comunicados(self):
        for i in range(6):
            PresencaAluno.objects.create(escola=self.escola, aluno=self.aluno, turma=self.turma, data=HOJE - datetime.timedelta(days=i + 1),
                                         status='FALTA_INJUSTIFICADA', aulas=2)
        assert self._r(self.sec, 'Há alunos em risco?')['dados']['por_faltas'] == 1

        assert 'Não há disciplinas' in self._r(self.sec, 'Que disciplinas tem a 7ª classe?')['resposta']
        self._disc('Matemática', 'MAT'), self._disc('História', 'HIS', classe='10ª Classe')
        d = self._r(self.sec, 'Que disciplinas tem a 7ª classe?')
        assert 'Matemática' in d['resposta'] and 'História' not in d['resposta']
        assert 'Indique a classe' in self._r(self.sec, 'Que disciplinas existem?')['resposta']

        assert 'Ainda não há material' in self._r(self.sec, 'Que material escolar existe?')['resposta']

        prof = Professor.objects.create(escola=self.escola, nome='Prof', email='prof.cargo@sige.mz', especialidade='Matemática')
        AtribuicaoCargo.objects.create(escola=self.escola, ano_letivo='2026', cargo='DIRECTOR_TURMA', professor=prof, turma=self.turma,
                                       titulo='Reunião de pais', prazo=HOJE - datetime.timedelta(days=1))
        assert self._r(self.sec, 'Quais as actividades de cargo por concluir?')['dados'] == {'por_concluir': 1, 'em_atraso': 1}

        assert 'Ainda não há pautas' in self._r(self.sec, 'Que pautas estão por fechar?')['resposta']

        assert 'Não há comunicados' in self._r(self.sec, 'Quais os últimos comunicados?')['resposta']
        ComunicadoEscolar.objects.create(escola=self.escola, titulo='Reunião geral', conteudo='x', publico_alvo='PROFESSORES', status='PUBLICADO')
        pergunta = 'Quais os últimos comunicados?'
        assert 'Reunião geral' not in self._r(self._cliente('ALUNO', 'aluno.com@sige.mz', aluno_id=self.aluno.id), pergunta)['resposta']
        assert 'Reunião geral' not in self._r(self.sec, pergunta)['resposta']          # secretaria não é o público-alvo
        prof_user = Usuario.objects.create_user(email='prof.com@sige.mz', password='PassTeste123!', role='PROFESSOR', escola=self.escola)
        prof_cli = APIClient()
        prof_cli.force_authenticate(prof_user)
        assert 'Reunião geral' in self._r(prof_cli, pergunta)['resposta']
        ComunicadoEscolar.objects.create(escola=self.outra, titulo='De outra escola', conteudo='x', publico_alvo='TODOS', status='PUBLICADO')
        assert 'De outra escola' not in self._r(prof_cli, pergunta)['resposta']

    # ------------------------------------------------------------ permissões e isolamento
    def test_nao_cruza_escolas_nem_id_invalido(self):
        assert 'Não encontrei' in self._r(self.sec, 'faltas', aluno_id=str(self.aluno_outra.id))['resposta']
        assert self._p(self.sec, 'faltas', aluno_id='nao-e-uuid').status_code == 400
        assert 'Não há atendimentos' in self._r(self.sec, 'atendimentos abertos')['resposta']
        Atendimento.objects.create(escola=self.outra, assunto='Outra escola')
        assert 'Não há atendimentos' in self._r(self.sec, 'atendimentos abertos')['resposta']

    def test_aluno_so_ve_o_proprio(self):
        cli = self._cliente('ALUNO', 'aluno.ass@sige.mz', aluno_id=self.aluno.id)
        r = self._r(cli, 'faltas', aluno_id=str(self.outro_aluno.id))  # tentativa de ver outro aluno
        assert 'Aluno Um' in r['resposta'] and 'Aluno Dois' not in r['resposta']
        assert r['acao']['destino'] == 'aluno-faltas'
        sem = self._cliente('ENCARREGADO', 'enc.sem@sige.mz')
        assert 'não está associada' in self._r(sem, 'faltas')['resposta']

    def test_perfis_sem_permissao(self):
        fin = self._cliente('FINANCEIRO', 'fin.ass@sige.mz')
        assert 'permissão' in self._r(fin, 'faltas', aluno_id=str(self.aluno.id))['resposta']
        assert 'dados' in self._r(fin, 'propinas', aluno_id=str(self.aluno.id))
        prof = self._cliente('PROFESSOR', 'prof.ass@sige.mz')
        assert 'permissão' in self._r(prof, 'faltas', aluno_id=str(self.aluno.id))['resposta']
        assert 'permissão' in self._r(prof, 'propinas', aluno_id=str(self.aluno.id))['resposta']
        aluno = self._cliente('ALUNO', 'aluno.perm@sige.mz', aluno_id=self.aluno.id)
        for pergunta in ('Há atendimentos abertos?', 'Quando termina a assinatura?', 'Qual o saldo de caixa?', 'Quantos alunos temos?', 'transferências pendentes'):
            assert 'permissão' in self._r(aluno, pergunta)['resposta'], pergunta
        assert 'permissão' in self._r(prof, 'Qual o saldo de caixa?')['resposta']

    def test_professor_ve_faltas_so_das_suas_turmas(self):
        prof = Professor.objects.create(escola=self.escola, nome='Prof', email='prof.falt@sige.mz', especialidade='Matemática')
        AlocacaoDocente.objects.create(escola=self.escola, professor=prof, disciplina=self._disc('Matemática', 'MAT'), turma=self.turma)
        cli = APIClient()
        cli.force_authenticate(Usuario.objects.get(professor_id=prof.id))
        assert 'faltas efectivas' in self._r(cli, 'faltas', aluno_id=str(self.aluno.id))['resposta']
        outra_turma = Turma.objects.create(escola=self.escola, nome='B', grau_ano='7ª Classe', ano_letivo='2026')
        fora = Aluno.objects.create(escola=self.escola, turma=outra_turma, matricula='AS_009', nome='Aluno Fora', data_nascimento='2012-01-01', genero='M')
        assert 'permissão' in self._r(cli, 'faltas', aluno_id=str(fora.id))['resposta']

    # ------------------------------------------------------------ contexto, feedback, auditoria
    def test_sugestoes_por_perfil_e_pagina(self):
        r = self.sec.get('/api/v1/assistente/sugestoes/?pagina=transferencias')
        assert r.status_code == 200 and r.data['sugestoes'][0] == 'Quantas transferências estão pendentes?' and len(r.data['sugestoes']) <= 6
        d = self._r(self.sec, 'Como lanço as notas?', pagina='caderneta')
        assert d['sugestoes'][0] == 'Como lanço as notas?'

    def test_feedback_e_auditoria(self):
        assert self._p(self.sec, '   ').status_code == 400
        assert self._p(self.sec, 'x' * 501).status_code == 400
        assert APIClient().post(URL, {'pergunta': 'faltas'}, format='json').status_code == 401
        d = self._r(self.sec, 'Como se calcula a MFD?', pagina='caderneta')
        c = ConsultaAssistente.objects.get()
        assert c.escola == self.escola and c.intencao == 'faq_mfd' and c.pagina == 'caderneta' and c.util is None
        fb = '/api/v1/assistente/feedback/'
        assert self.sec.post(fb, {'consulta_id': d['consulta_id'], 'util': True}, format='json').status_code == 200
        c.refresh_from_db()
        assert c.util is True
        assert self.sec.post(fb, {'consulta_id': d['consulta_id'], 'util': 'sim'}, format='json').status_code == 400
        outro = self._cliente('SECRETARIA', 'sec2.ass@sige.mz')
        assert outro.post(fb, {'consulta_id': d['consulta_id'], 'util': False}, format='json').status_code == 400  # só o autor
        c.refresh_from_db()
        assert c.util is True
