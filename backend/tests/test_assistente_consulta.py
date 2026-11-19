"""
Perguntas NOVAS (fora do conjunto de perguntas já previstas) que cabem nos dados do painel: o motor de consulta por parâmetros
(entidade + operação + filtros) tem de responder com os números certos, dentro do âmbito do perfil, e recusar o que não é do painel.
"""
import datetime
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno, PresencaAluno, TransferenciaAnulacao
from apps.pagamentos.models import Pagamento, TransacaoFinanceira
from apps.disciplinas.models import Disciplina
from apps.notas.models import Nota, CalendarioExame
from apps.professores.models import Professor, AlocacaoDocente
from apps.crm.models import Atendimento, VinculoEncarregado
from apps.pautas.models import Pauta
from apps.certificados.models import Certificado

URL = '/api/v1/assistente/perguntar/'
HOJE = datetime.date.today()
ANO = HOJE.year


@pytest.mark.django_db
class TestConsultaPorParametros:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_CON', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Con', nif_cnpj='NIF_CON1', email='con1@sige.mz', status='ATIVA', plano=plano, ano_letivo_ativo=str(ANO))
        mk_t = lambda classe, nome: Turma.objects.create(escola=self.escola, nome=nome, grau_ano=classe, ano_letivo=str(ANO))
        self.t7a, self.t7b, self.t8a = mk_t('7ª Classe', 'A'), mk_t('7ª Classe', 'B'), mk_t('8ª Classe', 'A')
        n = [0]

        def mk(nome, ap, g, turma, status='ATIVO'):
            n[0] += 1
            return Aluno.objects.create(escola=self.escola, turma=turma, matricula=f'CQ_{n[0]:03d}', nome=nome, apelido=ap, data_nascimento='2012-01-01', genero=g, status=status)
        self.ana, self.bela, self.carlos = mk('Ana', 'Lima', 'F', self.t7a), mk('Bela', 'Costa', 'F', self.t7a), mk('Carlos', 'Dias', 'M', self.t7a)
        self.daniel, self.elisa, self.fatima = mk('Daniel', 'Evora', 'M', self.t7b), mk('Elisa', 'Faria', 'F', self.t8a), mk('Fatima', 'Gomes', 'F', self.t8a)
        self.gil = mk('Gil', 'Horta', 'M', self.t7a, status='TRANSFERIDO')
        self.mat = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT', classe='7ª Classe', area='Geral', ano_letivo=str(ANO))
        self.fis = Disciplina.objects.create(escola=self.escola, nome='Física', codigo='FIS', classe='7ª Classe', area='Geral', ano_letivo=str(ANO))
        notas = {self.ana: (14, 8), self.bela: (9, 12), self.carlos: (16, 7), self.daniel: (5, 10), self.elisa: (11, 13), self.fatima: (18, 6)}
        for a, (m, f) in notas.items():
            for d, v in ((self.mat, m), (self.fis, f)):
                Nota.objects.create(escola=self.escola, aluno=a, disciplina=d, turma=a.turma, periodo='1_TRIMESTRE', media_final=v)
        # faltas (com disciplina, para o âmbito do professor)
        mkf = lambda a, dias, status, aulas, just=0, disc=None: PresencaAluno.objects.create(escola=self.escola, aluno=a, turma=a.turma, disciplina=disc or self.mat, data=HOJE - datetime.timedelta(days=dias),
                                                                                   status=status, aulas=aulas, aulas_justificadas=just)
        mkf(self.ana, 0, 'FALTA_INJUSTIFICADA', 2), mkf(self.ana, 0, 'FALTA_JUSTIFICADA', 1, 1, disc=self.fis)
        mkf(self.carlos, 40, 'FALTA_INJUSTIFICADA', 2), mkf(self.carlos, 41, 'FALTA_INJUSTIFICADA', 2)
        mkf(self.daniel, 0, 'FALTA_INJUSTIFICADA', 1)
        # propinas
        mkp = lambda a, mes, valor, st, pago=0, dias=60: Pagamento.objects.create(
            escola=self.escola, aluno=a, mes_referencia=f'{ANO}-{mes:02d}', valor=valor, valor_pago=pago, status=st, descricao=f'Propina {mes}',
            data_vencimento=timezone.now() - datetime.timedelta(days=dias), data_pagamento=timezone.now() if st == 'PAGO' else None)
        mkp(self.ana, 1, 1000, 'PENDENTE'), mkp(self.ana, 2, 1000, 'PAGO', 1000), mkp(self.bela, 1, 800, 'PENDENTE')
        mkp(self.daniel, 3, 500, 'PENDENTE'), mkp(self.carlos, 1, 1000, 'PAGO', 1000)
        # transferências
        adm = Usuario.objects.create_user(email='adm.con@sige.mz', password='PassTeste123!', role='ADMIN_ESCOLA', escola=self.escola)
        for aluno, tipo, estado in ((self.gil, 'TRANSFERENCIA_SAIDA', 'APROVADO'), (self.carlos, 'ANULACAO_MATRICULA', 'PENDENTE'), (self.daniel, 'TRANSFERENCIA_ENTRADA', 'PENDENTE')):
            t = TransferenciaAnulacao.objects.create(escola=self.escola, aluno=aluno, tipo=tipo, motivo='x', solicitado_por=adm)
            TransferenciaAnulacao.objects.filter(id=t.id).update(status=estado)
        # atendimentos, pautas, movimentos, certificados, exames, professores
        Atendimento.objects.create(escola=self.escola, assunto='A1', prioridade='ALTA')
        Atendimento.objects.create(escola=self.escola, assunto='A2', prioridade='NORMAL')
        Atendimento.objects.create(escola=self.escola, assunto='A3', prioridade='NORMAL', estado='RESOLVIDO', canal='TELEFONE')
        Pauta.objects.create(escola=self.escola, turma=self.t7a, ano_letivo=str(ANO), periodo='1_TRIMESTRE', status='FECHADA')
        Pauta.objects.create(escola=self.escola, turma=self.t8a, ano_letivo=str(ANO), periodo='1_TRIMESTRE', status='ABERTA')
        mkm = lambda tipo, valor, st: TransacaoFinanceira.objects.create(escola=self.escola, tipo=tipo, categoria='X', descricao=f'{tipo} {valor}', valor=valor, data=HOJE, status_aprovacao=st)
        mkm('RECEITA', 5000, 'APROVADO_DIRECTOR'), mkm('DESPESA', 1200, 'APROVADO_DIRECTOR'), mkm('DESPESA', 300, 'PENDENTE')
        for i in range(2):
            Certificado.objects.create(escola=self.escola, aluno=self.ana, tipo='DECLARACAO', codigo_autenticidade=f'COD{i}', qrcode_data='x')
        old = Certificado.objects.create(escola=self.escola, aluno=self.bela, tipo='CONCLUSAO', codigo_autenticidade='COD_OLD', qrcode_data='x')
        Certificado.objects.filter(id=old.id).update(emitido_em=timezone.now() - datetime.timedelta(days=60))
        CalendarioExame.objects.create(escola=self.escola, ano_letivo=str(ANO), classe='10ª Classe', disciplina='Física', epoca=1, data=HOJE + datetime.timedelta(days=5),
                                       hora_inicio=datetime.time(8, 0), duracao_minutos=120)
        CalendarioExame.objects.create(escola=self.escola, ano_letivo=str(ANO), classe='7ª Classe', disciplina='Matemática', epoca=1, data=HOJE + datetime.timedelta(days=10),
                                       hora_inicio=datetime.time(9, 0), duracao_minutos=120)
        self.p1 = Professor.objects.create(escola=self.escola, nome='Paula Prof', email='p1.con@sige.mz', especialidade='Matemática', genero='F')
        self.p2 = Professor.objects.create(escola=self.escola, nome='Pedro Prof', email='p2.con@sige.mz', especialidade='Física', genero='M')
        AlocacaoDocente.objects.create(escola=self.escola, professor=self.p1, disciplina=self.mat, turma=self.t7a)

    def _cli(self, role, email, **extra):
        u = Usuario.objects.create_user(email=email, password='PassTeste123!', role=role, escola=self.escola, **extra)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def _r(self, cli, pergunta, **extra):
        r = cli.post(URL, {'pergunta': pergunta, **extra}, format='json')
        assert r.status_code == 200, r.data
        return r.data

    def _recusada(self, d):
        return d['intencao'] in ('fora_do_painel', 'desconhecida') and 'dados' not in d

    # ------------------------------------------------------------ Direcção: perguntas novas, números exactos
    def test_alunos_filtros_e_agrupamentos(self):
        dr = self._cli('DIRECTOR_ESCOLA', 'dir.con@sige.mz')
        assert self._r(dr, 'quantas alunas há na 8ª classe?')['dados']['total'] == 2
        assert self._r(dr, 'quantos rapazes na 7ª classe')['dados']['total'] == 2
        assert self._r(dr, 'quantos alunos do sexo feminino?')['dados']['total'] == 4
        assert self._r(dr, 'e quantos alunos transferidos?')['dados']['total'] == 1
        lista = self._r(dr, 'lista os alunos da turma 7ª A')
        assert lista['dados']['total'] == 3 and 'Ana Lima' in lista['resposta'] and 'Daniel' not in lista['resposta']
        grupos = self._r(dr, 'alunos por classe')['resposta']
        assert '7ª Classe: 4' in grupos and '8ª Classe: 2' in grupos
        assert 'género feminino' in self._r(dr, 'quantas alunas existem?')['resposta']           # repete como entendeu a pergunta

    def test_notas_media_extremos_negativas_e_listas(self):
        dr = self._cli('DIRECTOR_ESCOLA', 'dir2.con@sige.mz')
        assert self._r(dr, 'qual a média de matemática no 1º trimestre?')['dados']['media'] == 12.2
        assert self._r(dr, 'quantas negativas a física?')['dados']['notas'] == 3
        assert self._r(dr, 'quantos alunos têm negativa a matemática?')['dados']['alunos'] == 2
        abaixo = self._r(dr, 'que alunos têm nota abaixo de 10 em matemática?')
        assert abaixo['dados']['notas'] == 2 and 'Daniel Evora: 5' in abaixo['resposta']
        assert self._r(dr, 'qual a maior nota de física?')['dados']['nota'] == 13
        assert 'Matemática: 14.5' in self._r(dr, 'média por disciplina da 8ª classe')['resposta']
        assert self._r(dr, 'qual a média da turma 7ª A a matemática?')['dados']['media'] == 13.0

    def test_faltas_ranking_limiares_e_periodos(self):
        dr = self._cli('DIRECTOR_ESCOLA', 'dir3.con@sige.mz')
        assert self._r(dr, 'quantas faltas injustificadas?')['dados']['faltas'] == 7
        assert 'Carlos Dias: 4; Ana Lima: 2' in self._r(dr, 'quem tem mais faltas?')['resposta']
        r = self._r(dr, 'que alunos têm mais de 3 faltas?')
        assert r['dados']['alunos'] == 1 and 'Carlos Dias: 4' in r['resposta']
        assert self._r(dr, 'quantas faltas houve este mês?')['dados']['faltas'] == 3         # Ana 2 + Daniel 1 (as de há 40 dias ficam de fora)
        assert self._r(dr, 'quantas faltas tem a turma 7ª B?')['dados']['faltas'] == 1
        d = self._r(dr, 'quantas faltas tem o Carlos Dias?')['dados']
        assert d.get('faltas', d.get('faltas_efectivas')) == 4                                  # nome escrito na pergunta

    def test_propinas_somas_estados_e_meses(self):
        dr = self._cli('DIRECTOR_ESCOLA', 'dir4.con@sige.mz')
        assert self._r(dr, 'quanto devem os alunos da 7ª classe?')['dados']['valor'] == '2300.00'
        assert self._r(dr, 'quantas propinas pagas em janeiro?')['dados']['total'] == 1
        assert self._r(dr, 'qual o valor total recebido?')['dados']['valor'] == '2000.00'
        assert self._r(dr, 'quantos alunos têm propinas em atraso?')['dados']['alunos'] == 3
        por_turma = self._r(dr, 'propinas em atraso por turma')['resposta']
        assert '7ª Classe A: 2 (1800.00 MZN)' in por_turma and '7ª Classe B: 1 (500.00 MZN)' in por_turma
        assert self._r(dr, 'quanto deve a Bela Costa?')['dados']['valor'] == '800.00'

    def test_transferencias_atendimentos_pautas_movimentos_certificados_exames(self):
        dr = self._cli('DIRECTOR_ESCOLA', 'dir5.con@sige.mz')
        assert self._r(dr, 'quantas transferências de saída?')['dados']['total'] == 1
        assert self._r(dr, 'quantas transferências aprovadas?')['dados']['total'] == 1
        assert self._r(dr, 'quantas anulações pendentes?')['dados']['total'] == 1
        assert self._r(dr, 'quantos atendimentos resolvidos?')['dados']['total'] == 1
        assert self._r(dr, 'atendimentos de prioridade alta')['dados']['total'] == 1
        assert self._r(dr, 'quantas pautas fechadas?')['dados']['total'] == 1
        assert self._r(dr, 'quanto gastamos este mês?')['dados']['valor'] == '1200.00'
        assert self._r(dr, 'qual o total das receitas deste mês?')['dados']['valor'] == '5000.00'
        assert self._r(dr, 'quanto há de despesas pendentes de aprovação?')['dados']['valor'] == '300.00'
        assert self._r(dr, 'quantos certificados foram emitidos este mês?')['dados']['total'] == 2
        ex = self._r(dr, 'que exames há de matemática?')
        assert ex['dados']['total'] == 1 and '7ª Classe, Matemática' in ex['resposta']

    def test_professores_e_turmas(self):
        dr = self._cli('DIRECTOR_ESCOLA', 'dir6.con@sige.mz')
        assert self._r(dr, 'quantos professores do sexo masculino?')['dados']['total'] == 1
        assert 'Pedro Prof' in self._r(dr, 'que professores estão sem turma?')['resposta']
        assert self._r(dr, 'quantas turmas tem a 7ª classe?')['dados']['turmas'] == 2
        assert '8ª Classe A' in self._r(dr, 'que turmas são da 8ª classe?')['resposta']

    # ------------------------------------------------------------ cada perfil só vê o seu painel e o seu âmbito
    def test_professor_so_as_suas_turmas_e_nada_de_dinheiro(self):
        prof = APIClient()
        prof.force_authenticate(Usuario.objects.get(professor_id=self.p1.id))
        r = self._r(prof, 'quantas negativas tenho nas minhas turmas?')
        assert r['dados']['notas'] == 1 and 'nas suas turmas' in r['resposta']                 # Bela (9) a Matemática na 7ª A
        assert self._r(prof, 'qual a média das minhas turmas a matemática?')['dados']['media'] == 13.0
        f = self._r(prof, 'que alunos têm mais de 3 faltas?')
        assert f['dados']['alunos'] == 1 and 'Carlos Dias' in f['resposta'] and 'Daniel' not in f['resposta']
        assert 'nas suas turmas' in self._r(prof, 'quantos alunos há na 8ª classe?')['resposta']         # âmbito indicado: 0 nas SUAS turmas
        for pergunta in ('quanto devem os alunos?', 'quanto gastamos este mês?', 'quantos atendimentos resolvidos?', 'quantas transferências de saída?',
                         'quantos professores do sexo masculino?', 'quantas pautas fechadas?'):
            assert self._recusada(self._r(prof, pergunta)), pergunta

    def test_secretaria_sem_notas_nem_movimentos(self):
        sec = self._cli('SECRETARIA', 'sec.con@sige.mz')
        assert self._r(sec, 'quantas alunas há na 8ª classe?')['dados']['total'] == 2
        assert self._r(sec, 'quanto devem os alunos da 7ª classe?')['dados']['valor'] == '2300.00'
        assert self._r(sec, 'quantas transferências aprovadas?')['dados']['total'] == 1
        for pergunta in ('qual a média de matemática?', 'quantas negativas a física?', 'quanto gastamos este mês?', 'qual o total das receitas?'):
            assert self._recusada(self._r(sec, pergunta)), pergunta

    def test_dap_sem_dinheiro_e_financeiro_sem_pedagogia(self):
        dap = self._cli('DAP', 'dap.con@sige.mz')
        assert self._r(dap, 'qual a média de matemática?')['dados']['media'] == 12.2
        assert self._r(dap, 'quantas pautas fechadas?')['dados']['total'] == 1
        for pergunta in ('quanto devem os alunos?', 'quanto gastamos este mês?', 'quantos certificados foram emitidos?'):
            assert self._recusada(self._r(dap, pergunta)), pergunta
        fin = self._cli('FINANCEIRO', 'fin.con@sige.mz')
        assert self._r(fin, 'quanto devem os alunos da 7ª classe?')['dados']['valor'] == '2300.00'
        assert self._r(fin, 'quanto gastamos este mês?')['dados']['valor'] == '1200.00'
        for pergunta in ('quantas faltas houve este mês?', 'qual a média de matemática?', 'quantos atendimentos resolvidos?', 'quantas pautas fechadas?'):
            assert self._recusada(self._r(fin, pergunta)), pergunta

    def test_aluno_so_os_seus_dados_e_nunca_estatisticas_da_turma(self):
        al = self._cli('ALUNO', 'aluno.con@sige.mz', aluno_id=self.ana.id)
        assert self._r(al, 'quantas faltas tenho este mês?')['dados']['faltas'] == 2
        assert self._r(al, 'qual a minha média a matemática?')['dados']['media'] == 14.0
        assert self._r(al, 'quantas propinas em atraso tenho?')['dados']['total'] == 1
        assert self._r(al, 'quanto devo de propinas?')['dados']['valor'] == '1000.00'
        assert self._r(al, 'que exames há de matemática?')['dados']['total'] == 1
        for pergunta in ('quantos alunos há na 8ª classe?', 'qual a média da turma a matemática?', 'quantas alunas há na minha turma?', 'quanto devem os colegas?',
                         'quantas faltas tem o Carlos Dias?', 'quem tem mais faltas?', 'quanto gastamos este mês?', 'quantas notas negativas há na escola?'):
            d = self._r(al, pergunta)
            assert 'Carlos' not in d['resposta'] and 'Daniel' not in d['resposta'], pergunta
            assert self._recusada(d) or d['dados'].get('faltas') in (None,) and False or self._recusada(d), pergunta

    def test_encarregado_escolhe_o_filho_pelo_nome(self):
        enc = self._cli('ENCARREGADO', 'enc.con@sige.mz')
        for a in (self.ana, self.bela):
            VinculoEncarregado.objects.create(escola=self.escola, usuario=Usuario.objects.get(email='enc.con@sige.mz'), aluno=a)
        assert self._r(enc, 'quanto deve a Bela?')['dados']['valor'] == '800.00'
        assert self._r(enc, 'quantas propinas em atraso tem a Ana?')['dados']['total'] == 1
        d = self._r(enc, 'quanto devo de propinas?')                                           # dois filhos e nenhum escolhido
        assert d['precisa_aluno'] is True
        assert 'Carlos' not in self._r(enc, 'quanto deve o Carlos Dias?')['resposta']            # não é seu filho
        assert self._recusada(self._r(enc, 'quantos alunos há na 7ª classe?'))

    def test_perguntas_sem_sentido_nao_viram_consulta(self):
        dr = self._cli('DIRECTOR_ESCOLA', 'dir7.con@sige.mz')
        for pergunta in ('receita de bolo de chocolate', 'qual a capital da França', 'xyzabc qwerty'):
            assert self._r(dr, pergunta)['intencao'] in ('desconhecida', 'fora_do_painel'), pergunta
        # março é um mês e não um aluno (nome de aluno nunca vem de palavras da consulta)
        Aluno.objects.create(escola=self.escola, turma=self.t7a, matricula='CQ_900', nome='Marco', apelido='Teste', data_nascimento='2012-01-01', genero='M')
        assert self._r(dr, 'quantas propinas em atraso em março?')['dados']['total'] == 1
