import datetime
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno, PresencaAluno
from apps.pagamentos.models import Pagamento
from apps.disciplinas.models import Disciplina
from apps.notas.models import Nota
from apps.professores.models import Professor, AlocacaoDocente
from apps.crm.models import VinculoEncarregado

URL = '/api/v1/assistente/perguntar/'
HOJE = datetime.date.today()


@pytest.mark.django_db
class TestInteligencia:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_INT', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Int', nif_cnpj='NIF_INT1', email='int1@sige.mz', status='ATIVA', plano=plano,
                                            telefone='840000001', endereco='Rua Central 10')
        self.turma = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2026')
        self.outra_turma = Turma.objects.create(escola=self.escola, nome='B', grau_ano='8ª Classe', ano_letivo='2026')
        mk = lambda mat, nome, turma, ap=None: Aluno.objects.create(escola=self.escola, turma=turma, matricula=mat, nome=nome, apelido=ap,
                                                                    data_nascimento='2012-01-01', genero='M', nome_responsavel='Pai Teste', contato_responsavel='841111111')
        self.joao_silva = mk('IN_001', 'João', self.turma, 'Silva')
        self.joao_costa = mk('IN_002', 'João', self.turma, 'Costa')
        self.maria = mk('IN_003', 'Maria Fernanda', self.outra_turma)
        self.dir = self._cli('DIRECTOR_ESCOLA', 'dir.int@sige.mz')

    def _cli(self, role, email, **extra):
        u = Usuario.objects.create_user(email=email, password='PassTeste123!', role=role, escola=self.escola, **extra)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def _r(self, cli, pergunta, **extra):
        r = cli.post(URL, {'pergunta': pergunta, **extra}, format='json')
        assert r.status_code == 200, r.data
        return r.data

    def _atraso(self, aluno, mes, valor=1000):
        Pagamento.objects.create(escola=self.escola, aluno=aluno, mes_referencia=mes, valor=valor, status='PENDENTE', descricao=f'Propina {mes}',
                                 data_vencimento=timezone.now() - datetime.timedelta(days=30))

    def _professor(self, email='prof.int@sige.mz', turmas=()):
        prof = Professor.objects.create(escola=self.escola, nome='Prof Teste', email=email, especialidade='Matemática')
        disc = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT', classe='7ª Classe', area='Geral', ano_letivo='2026')
        for t in turmas:
            AlocacaoDocente.objects.create(escola=self.escola, professor=prof, disciplina=disc, turma=t)
        cli = APIClient()
        cli.force_authenticate(Usuario.objects.get(professor_id=prof.id))
        return cli, disc

    # ------------------------------------------------------------ compreensão
    def test_erros_de_escrita_e_variacoes(self):
        PresencaAluno.objects.create(escola=self.escola, aluno=self.joao_silva, turma=self.turma, data=HOJE, status='FALTA_INJUSTIFICADA', aulas=1)
        aid = str(self.joao_silva.id)
        assert self._r(self.dir, 'Há propnias em atraso?', aluno_id=aid)['intencao'] == 'propinas'
        assert self._r(self.dir, 'quantas faltass tem', aluno_id=aid)['intencao'] == 'faltas'
        assert self._r(self.dir, 'quando termina a asinatura?')['intencao'] == 'assinatura'
        assert self._r(self.dir, 'como redefino uma senha')['intencao'] == 'guia_senhas'          # sem acentos nem pontuação
        assert self._r(self.dir, 'COMO CRIO TURMAS EM LOTE???')['intencao'] == 'guia_turmas'
        assert self._r(self.dir, 'como cadastro um aluno novo')['intencao'] == 'guia_matricula'

    def test_nome_do_aluno_na_pergunta(self):
        PresencaAluno.objects.create(escola=self.escola, aluno=self.joao_silva, turma=self.turma, data=HOJE, status='FALTA_INJUSTIFICADA', aulas=2)
        d = self._r(self.dir, 'Quantas faltas tem o João Silva?')                  # sem escolher o aluno na lista
        assert d['dados']['faltas_efectivas'] == 2 and 'João Silva' in d['resposta']
        d = self._r(self.dir, 'faltas da maria fernanda')                         # sem acentos nem maiúsculas
        assert d['dados']['faltas_efectivas'] == 0 and 'Maria Fernanda' in d['resposta']
        amb = self._r(self.dir, 'quantas faltas tem o joao?')                     # dois João: pede esclarecimento, não adivinha
        assert amb['precisa_aluno'] is True and {c['nome'] for c in amb['candidatos']} == {'João Silva', 'João Costa'} and 'dados' not in amb
        assert {c['id'] for c in amb['candidatos']} == {str(self.joao_silva.id), str(self.joao_costa.id)}

    def test_nome_respeita_o_ambito_do_perfil(self):
        prof, _ = self._professor(turmas=[self.turma])                            # só a turma A
        assert 'faltas efectivas' in self._r(prof, 'faltas do joao silva')['resposta']
        d = self._r(prof, 'faltas da maria fernanda')                             # Maria está na turma B: fora do âmbito
        assert 'Maria Fernanda' not in d['resposta'] and 'dados' not in d
        fin = self._cli('FINANCEIRO', 'fin.int@sige.mz')
        self._atraso(self.maria, '2026-01', 900)
        assert self._r(fin, 'propinas da maria fernanda')['dados']['valor_em_atraso'] == '900.00'
        assert 'dados' not in self._r(fin, 'faltas da maria fernanda')           # financeiro não vê faltas

    def test_encarregado_escreve_o_nome_do_filho(self):
        enc = self._cli('ENCARREGADO', 'enc.int@sige.mz')
        for a in (self.joao_silva, self.maria):
            VinculoEncarregado.objects.create(escola=self.escola, usuario=Usuario.objects.get(email='enc.int@sige.mz'), aluno=a)
        self._atraso(self.maria, '2026-02', 400)
        assert self._r(enc, 'há propinas em atraso da maria?')['dados']['valor_em_atraso'] == '400.00'
        d = self._r(enc, 'propinas do joao costa')                               # João Costa não é seu filho
        assert 'Costa' not in d['resposta']

    def test_pergunta_de_seguimento(self):
        d1 = self._r(self.dir, 'Quantas faltas tem?')
        assert d1['precisa_aluno'] is True and d1['intencao'] == 'faltas'
        d2 = self._r(self.dir, 'Maria Fernanda', anterior=d1['intencao'])         # só o nome
        assert d2['intencao'] == 'faltas' and 'Maria Fernanda' in d2['resposta']
        d3 = self._r(self.dir, 'e as propinas?', anterior='faltas', aluno_id=str(self.maria.id))
        assert d3['intencao'] == 'propinas'
        # texto sem sentido NÃO herda a capacidade anterior (antes respondia lixo, por exemplo 'receita de bolo' → caixa)
        for lixo in ('receita de bolo de chocolate', 'xyzabc qwerty', 'como faço magia negra no sistema'):
            r = self._r(self.dir, lixo, anterior='risco')
            assert r['intencao'] != 'risco' and 'dados' not in r, lixo
        assert self._r(self.dir, 'e do Joao Costa?', anterior='faltas')['intencao'] == 'faltas'          # marcador + nome
        # um seguimento nunca ultrapassa o painel: o aluno não pode continuar uma capacidade que não é sua
        aluno = self._cli('ALUNO', 'aluno.int@sige.mz', aluno_id=self.maria.id)
        assert self._r(aluno, 'Maria Fernanda', anterior='assinatura')['intencao'] == 'desconhecida'

    def test_desconhecida_sugere_perguntas_do_proprio_painel(self):
        aluno = self._cli('ALUNO', 'aluno.sug@sige.mz', aluno_id=self.maria.id)
        d = self._r(aluno, 'quero ver as minhas propinas atrasadas por favor xyz')
        assert d['sugestoes'] and all('assinatura' not in s.lower() and 'caixa' not in s.lower() for s in d['sugestoes'])
        d = self._r(aluno, 'asdfgh qwerty')
        assert d['intencao'] == 'desconhecida' and d['sugestoes']

    # ------------------------------------------------------------ ajuda por perfil
    def test_ajuda_personalizada(self):
        d = self._r(self.dir, 'O que posso perguntar?')
        assert d['intencao'] == 'guia_assistente_guia' and 'Consultas:' in d['resposta'] and 'Guias passo a passo:' in d['resposta']
        assert d['sugestoes'] and len(d['sugestoes']) <= 6
        aluno = self._cli('ALUNO', 'aluno.aj@sige.mz', aluno_id=self.maria.id)
        r = self._r(aluno, 'o que sabes fazer?')['resposta'].lower()
        assert 'assinatura' not in r and 'saldo de caixa' not in r and 'transferências' not in r
        prof, _ = self._professor()
        assert 'caixa' not in self._r(prof, 'ajuda')['resposta'].lower()

    # ------------------------------------------------------------ novas capacidades
    def test_perfil_e_resumo_do_aluno_por_perfil(self):
        PresencaAluno.objects.create(escola=self.escola, aluno=self.maria, turma=self.outra_turma, data=HOJE, status='FALTA_INJUSTIFICADA', aulas=1)
        self._atraso(self.maria, '2026-01', 700)
        p = self._r(self.dir, 'Em que turma está a Maria Fernanda?')
        assert '8ª Classe' in p['resposta'] and 'turma B' in p['resposta'] and 'Pai Teste' in p['resposta']
        resumo = self._r(self.dir, 'como está a maria fernanda?')
        assert '1 falta' in resumo['resposta'] and '700.00 MZN' in resumo['resposta']                  # direcção: faltas + propinas (+ notas)
        sec = self._cli('SECRETARIA', 'sec.int@sige.mz')
        rs = self._r(sec, 'como está a maria fernanda?')['resposta']
        assert '700.00 MZN' in rs and 'nota' not in rs.lower()                                          # secretaria: sem notas (Caderneta não é do painel)
        fin = self._cli('FINANCEIRO', 'fin2.int@sige.mz')
        rf = self._r(fin, 'como está a maria fernanda?')['resposta']
        assert '700.00 MZN' in rf and 'falta' not in rf.lower()                                         # financeiro: só propinas
        prof, _ = self._professor('prof2.int@sige.mz', turmas=[self.outra_turma])
        rp = self._r(prof, 'como está a maria fernanda?')['resposta']
        assert 'falta' in rp.lower() and '700' not in rp                                               # professor: sem propinas

    def test_turmas_do_professor_e_aproveitamento(self):
        prof, disc = self._professor(turmas=[self.turma])
        d = self._r(prof, 'Que turmas tenho?')
        assert d['dados']['turmas'] == 1 and '7ª Classe A' in d['resposta'] and '2 aluno(s)' in d['resposta']
        assert 'Ainda não há notas' in self._r(prof, 'Como está o aproveitamento?')['resposta']
        Nota.objects.create(escola=self.escola, aluno=self.joao_silva, disciplina=disc, turma=self.turma, periodo='1_TRIMESTRE', media_final=7)
        Nota.objects.create(escola=self.escola, aluno=self.joao_costa, disciplina=disc, turma=self.turma, periodo='1_TRIMESTRE', media_final=14)
        outra = Disciplina.objects.create(escola=self.escola, nome='Física', codigo='FIS', classe='8ª Classe', area='Geral', ano_letivo='2026')
        Nota.objects.create(escola=self.escola, aluno=self.maria, disciplina=outra, turma=self.outra_turma, periodo='1_TRIMESTRE', media_final=5)
        d = self._r(prof, 'Como está o aproveitamento?')                                   # professor: só as suas turmas/disciplinas
        assert d['dados'] == {'periodo': '1_TRIMESTRE', 'avaliacoes': 2, 'negativas': 1}
        dd = self._r(self.dir, 'Como está o aproveitamento?')                              # direcção: a escola toda
        assert dd['dados']['avaliacoes'] == 3 and dd['dados']['negativas'] == 2
        dap = self._cli('DAP', 'dap.int@sige.mz')
        assert self._r(dap, 'taxa de negativas por classe')['dados']['negativas'] == 2

    def test_professores_resumo_resumo_escola_e_devedores(self):
        self._professor('p1.int@sige.mz', turmas=[self.turma])
        Professor.objects.create(escola=self.escola, nome='Sem Turma', email='sem.int@sige.mz', especialidade='Física')
        d = self._r(self.dir, 'Quantos professores estão sem turma?')
        assert d['dados'] == {'professores': 2, 'sem_atribuicao': 1} and 'Sem Turma' in d['resposta']
        self._atraso(self.joao_silva, '2026-01', 500), self._atraso(self.joao_silva, '2026-02', 500), self._atraso(self.maria, '2026-01', 300)
        r = self._r(self.dir, 'Dê-me um resumo da escola')['resposta']
        assert '3 aluno(s) activo(s)' in r and '3 propina(s) em atraso (1300.00 MZN)' in r
        dev = self._r(self.dir, 'Quem tem dívidas?')
        assert dev['dados'] == {'devedores': 2, 'valor': '1300.00'} and 'João' not in dev['resposta']      # sem classe: só totais por turma
        d7 = self._r(self.dir, 'alunos devedores da 7ª classe')
        assert 'João Silva (A): 1000.00 MZN, 2 mês(es)' in d7['resposta'] and 'Maria' not in d7['resposta']
        for role in ('FINANCEIRO', 'SECRETARIA', 'CHEFE_SECRETARIA'):
            assert 'dados' in self._r(self._cli(role, f'{role.lower()}.dev@sige.mz'), 'quem deve?')
        for role in ('DAP', 'PROFESSOR', 'ALUNO', 'ENCARREGADO'):
            u = self._cli(role, f'{role.lower()}.dev@sige.mz')
            assert 'dados' not in self._r(u, 'quem deve?'), role

    def test_contactos_e_trimestres_para_todos(self):
        self.escola.data_inicio_t1, self.escola.data_fim_t1 = datetime.date(2026, 1, 12), datetime.date(2026, 4, 17)
        self.escola.save()
        for role in ('ALUNO', 'PROFESSOR', 'DAP', 'FINANCEIRO', 'SECRETARIA'):
            u = self._cli(role, f'{role.lower()}.ct@sige.mz', **({'aluno_id': self.maria.id} if role == 'ALUNO' else {}))
            c = self._r(u, 'Qual o contacto da escola?')
            assert '840000001' in c['resposta'] and 'Rua Central 10' in c['resposta'], role
            t = self._r(u, 'Quais as datas dos trimestres?')
            assert '1.º trimestre: 12/01/2026 a 17/04/2026' in t['resposta'], role

    def test_horario_de_uma_turma_para_a_gestao(self):
        from apps.turmas.models import HorarioEscolar
        prof, disc = self._professor('prof.hor@sige.mz', turmas=[self.turma])
        dia = HOJE.isoweekday() if HOJE.isoweekday() < 7 else 1
        HorarioEscolar.objects.create(escola=self.escola, turma=self.turma, disciplina=disc, professor=Professor.objects.get(email='prof.hor@sige.mz'),
                                      dia_semana=dia, tempo=1, hora_inicio='09:00', hora_fim='09:45')
        if HOJE.isoweekday() < 7:
            r = self._r(self.dir, 'horário da 7ª classe turma A')['resposta']
            assert '09:00' in r and 'Matemática' in r
