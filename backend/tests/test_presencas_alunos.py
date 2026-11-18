import pytest
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno, PresencaAluno
from apps.disciplinas.models import Disciplina
from apps.professores.models import Professor, AlocacaoDocente


@pytest.mark.django_db
class TestPresencasAlunos:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_PRES_TEST', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Pres', nif_cnpj='NIF_PRES', email='pres@sige.mz', status='ATIVA', plano=plano)
        self.turma26 = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2026')
        self.turma25 = Turma.objects.create(escola=self.escola, nome='B', grau_ano='7ª Classe', ano_letivo='2025')
        self.disc = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT', classe='7ª Classe', area='Geral')
        self.outra_disc = Disciplina.objects.create(escola=self.escola, nome='Física', codigo='FIS', classe='7ª Classe', area='Geral')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma26, matricula='PR_001', nome='Aluno Um',
                                          data_nascimento='2012-01-01', genero='M')
        prof = Professor.objects.create(escola=self.escola, nome='Prof', email='prof.pres@sige.mz', especialidade='Matemática')
        AlocacaoDocente.objects.create(escola=self.escola, professor=prof, disciplina=self.disc, turma=self.turma26)
        self.user = Usuario.objects.get(professor_id=prof.id)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _lote(self, **extra):
        body = {'turma': str(self.turma26.id), 'disciplina': str(self.disc.id), 'data': '2026-03-02', 'aulas': 1,
                'registos': [{'aluno': str(self.aluno.id), 'status': 'FALTA_INJUSTIFICADA', 'observacao': 'sem aviso'}]}
        body.update(extra)
        return self.client.post('/api/v1/alunos/presencas/lote/', body, format='json')

    def test_lote_regista_e_actualiza(self):
        assert self._lote().status_code == 200
        assert self._lote(registos=[{'aluno': str(self.aluno.id), 'status': 'PRESENTE'}]).status_code == 200
        assert PresencaAluno.objects.count() == 1
        assert PresencaAluno.objects.get().status == 'PRESENTE'

    def test_professor_nao_lanca_em_disciplina_nao_atribuida(self):
        assert self._lote(disciplina=str(self.outra_disc.id)).status_code == 403

    def test_nao_aceita_data_futura(self):
        assert self._lote(data='2999-01-01').status_code == 400

    def test_listagem_filtra_por_ano_lectivo(self):
        self._lote()
        r26 = self.client.get('/api/v1/alunos/presencas/?ano_letivo=2026&turma_id=%s' % self.turma26.id)
        r25 = self.client.get('/api/v1/alunos/presencas/?ano_letivo=2025')
        assert r26.status_code == 200 and r25.status_code == 200
        n = lambda r: len(r.data['results'] if isinstance(r.data, dict) and 'results' in r.data else r.data)
        assert n(r26) == 1
        assert n(r25) == 0

    def _cliente(self, role, email):
        u = Usuario.objects.create_user(email=email, password='PassTeste123!', role=role, escola=self.escola)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_secretaria_justifica_falta_injustificada(self):
        self._lote()
        reg = PresencaAluno.objects.get()
        sec = self._cliente('SECRETARIA', 'sec.just@sige.mz')
        assert sec.post(f'/api/v1/alunos/presencas/{reg.id}/justificar/', {}, format='json').status_code == 400
        r = sec.post(f'/api/v1/alunos/presencas/{reg.id}/justificar/', {'motivo': 'doença'}, format='json')
        assert r.status_code == 200
        reg.refresh_from_db()
        assert reg.status == 'FALTA_JUSTIFICADA' and reg.justificacao == 'doença' and reg.justificada_em
        # já justificada: não repete
        assert sec.post(f'/api/v1/alunos/presencas/{reg.id}/justificar/', {'motivo': 'x'}, format='json').status_code == 400

    def test_professor_nao_justifica(self):
        self._lote()
        reg = PresencaAluno.objects.get()
        r = self.client.post(f'/api/v1/alunos/presencas/{reg.id}/justificar/', {'motivo': 'x'}, format='json')
        assert r.status_code == 403

    def test_justificar_nao_cruza_escolas(self):
        self._lote()
        reg = PresencaAluno.objects.get()
        plano = Plano.objects.create(nome='PLANO_PRES_2', preco=2000, duracao_dias=30)
        outra = Escola.objects.create(nome='Outra', nif_cnpj='NIF_OUTRA', email='outra@sige.mz', status='ATIVA', plano=plano)
        u = Usuario.objects.create_user(email='sec.outra@sige.mz', password='PassTeste123!', role='SECRETARIA', escola=outra)
        c = APIClient()
        c.force_authenticate(u)
        assert c.post(f'/api/v1/alunos/presencas/{reg.id}/justificar/', {'motivo': 'x'}, format='json').status_code == 404

    def test_resumo_agrega_faltas(self):
        self._lote()
        r = self.client.get('/api/v1/alunos/presencas/resumo/?ano_letivo=2026')
        assert r.status_code == 200
        linha = r.data['resultados'][0]
        assert linha['total'] == 1 and linha['injustificadas'] == 1 and linha['percent_faltas'] == 100.0
        assert self.client.get('/api/v1/alunos/presencas/resumo/?ano_letivo=2025').data['resultados'] == []

    def test_exportar_pdf_e_xlsx_apenas(self):
        self._lote()
        base = f'/api/v1/alunos/presencas/exportar/?ano_letivo=2026&turma_id={self.turma26.id}'
        pdf = self.client.get(base + '&formato=pdf&carimbo=nao')
        assert pdf.status_code == 200 and pdf['Content-Type'] == 'application/pdf' and pdf.content[:4] == b'%PDF'
        xl = self.client.get(base + '&formato=xlsx&carimbo=nao')
        assert xl.status_code == 200 and xl.content[:2] == b'PK'
        assert self.client.get(base + '&formato=docx').status_code == 400

    def test_exportar_sem_registos_gera_documento_vazio(self):
        r = self.client.get('/api/v1/alunos/presencas/exportar/?ano_letivo=2025&formato=pdf&carimbo=nao')
        assert r.status_code == 200 and r.content[:4] == b'%PDF'

    def _encarregado(self, aluno_id, email='enc.pres@sige.mz'):
        u = Usuario.objects.create_user(email=email, password='PassTeste123!', role='ENCARREGADO',
                                        escola=self.escola, aluno_id=aluno_id)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_encarregado_so_ve_o_proprio_educando(self):
        outro = Aluno.objects.create(escola=self.escola, turma=self.turma26, matricula='PR_002', nome='Aluno Dois',
                                     data_nascimento='2012-02-02', genero='F')
        self._lote(registos=[{'aluno': str(self.aluno.id), 'status': 'FALTA_INJUSTIFICADA'},
                             {'aluno': str(outro.id), 'status': 'PRESENTE'}])
        n = lambda r: len(r.data['results'] if isinstance(r.data, dict) and 'results' in r.data else r.data)
        assert n(self._encarregado(self.aluno.id).get('/api/v1/alunos/presencas/')) == 1
        # sem vínculo ao educando: nada
        assert n(self._encarregado(None, 'enc.sem@sige.mz').get('/api/v1/alunos/presencas/')) == 0

    def test_encarregado_pede_justificacao_e_secretaria_decide(self):
        self._lote()
        reg = PresencaAluno.objects.get()
        enc = self._encarregado(self.aluno.id)
        url = f'/api/v1/alunos/presencas/{reg.id}/pedir-justificacao/'
        assert enc.post(url, {}, format='json').status_code == 400
        assert enc.post(url, {'motivo': 'consulta médica'}, format='json').status_code == 200
        reg.refresh_from_db()
        assert reg.pedido_justificacao == 'consulta médica' and reg.status == 'FALTA_INJUSTIFICADA'
        # o pedido não justifica sozinho; a secretaria decide
        sec = self._cliente('SECRETARIA', 'sec.pedido@sige.mz')
        assert sec.post(f'/api/v1/alunos/presencas/{reg.id}/justificar/', {'motivo': 'atestado'}, format='json').status_code == 200

    def test_encarregado_de_outro_aluno_nao_pede(self):
        self._lote()
        reg = PresencaAluno.objects.get()
        outro = Aluno.objects.create(escola=self.escola, turma=self.turma26, matricula='PR_003', nome='Aluno Tres',
                                     data_nascimento='2012-03-03', genero='M')
        enc = self._encarregado(outro.id, 'enc.outro@sige.mz')
        assert enc.post(f'/api/v1/alunos/presencas/{reg.id}/pedir-justificacao/', {'motivo': 'x'}, format='json').status_code == 404

    def test_professor_nao_pede_justificacao(self):
        self._lote()
        reg = PresencaAluno.objects.get()
        assert self.client.post(f'/api/v1/alunos/presencas/{reg.id}/pedir-justificacao/', {'motivo': 'x'}, format='json').status_code == 403

    def test_limite_de_faltas_e_alerta_de_risco(self):
        self._lote()
        url = '/api/v1/alunos/presencas/resumo/?ano_letivo=2026'
        assert self.client.get(url).data['total_em_risco'] == 0  # alertas desactivados por omissão
        direcao = self._cliente('DIRECTOR_ESCOLA', 'dir.limite@sige.mz')
        assert direcao.post('/api/v1/alunos/presencas/limite/', {'limite_percent': 150}, format='json').status_code == 400
        assert direcao.post('/api/v1/alunos/presencas/limite/', {'limite_percent': 30}, format='json').status_code == 200
        r = direcao.get(url)
        assert r.data['limite_percent'] == 30 and r.data['total_em_risco'] == 1 and r.data['resultados'][0]['em_risco']
        # secretaria não altera o limite
        sec = self._cliente('SECRETARIA', 'sec.limite@sige.mz')
        assert sec.post('/api/v1/alunos/presencas/limite/', {'limite_percent': 5}, format='json').status_code == 403
        # desactivar
        assert direcao.post('/api/v1/alunos/presencas/limite/', {'limite_percent': ''}, format='json').data['limite_percent'] is None

    def test_faltas_do_trimestre_para_a_caderneta(self):
        self._lote()  # falta injustificada em 2026-03-02
        base = (f'/api/v1/alunos/presencas/faltas-trimestre/?aluno_id={self.aluno.id}'
                f'&disciplina_id={self.disc.id}&trimestre=1_TRIMESTRE')
        # datas do trimestre não configuradas: pede configuração em vez de inventar
        assert self.client.get(base).status_code == 400
        from datetime import date
        self.escola.data_inicio_t1, self.escola.data_fim_t1 = date(2026, 2, 1), date(2026, 4, 30)
        self.escola.save()
        self.user.escola = self.escola  # o utilizador autenticado em teste guarda a escola em cache
        r = self.client.get(base)
        assert r.status_code == 200 and r.data['faltas'] == 1 and r.data['aulas_registadas'] == 1
        # fora do intervalo do trimestre
        self.escola.data_inicio_t1, self.escola.data_fim_t1 = date(2026, 5, 1), date(2026, 6, 30)
        self.escola.save()
        self.user.escola = self.escola
        assert self.client.get(base).data['faltas'] == 0

    def test_tipo_de_aula_obrigatorio(self):
        for invalido in (None, 0, 3, 'x'):
            assert self._lote(aulas=invalido).status_code == 400
        assert PresencaAluno.objects.count() == 0

    def test_aula_dupla_conta_duas_faltas_por_trimestre(self):
        from datetime import date
        self.escola.data_inicio_t1, self.escola.data_fim_t1 = date(2026, 2, 1), date(2026, 4, 30)
        self.escola.data_inicio_t2, self.escola.data_fim_t2 = date(2026, 5, 1), date(2026, 8, 31)
        self.escola.save()
        self.user.escola = self.escola
        assert self._lote(data='2026-03-02', aulas=1).status_code == 200   # 1 falta no 1.º T
        assert self._lote(data='2026-03-03', aulas=2).status_code == 200   # +2 faltas no 1.º T
        assert self._lote(data='2026-06-01', aulas=2).status_code == 200   # 2 faltas no 2.º T
        r = self.client.get(f'/api/v1/alunos/presencas/faltas-geral/?ano_letivo=2026&turma_id={self.turma26.id}')
        assert r.status_code == 200
        assert [d['nome'] for d in r.data['disciplinas']] == ['Matemática']
        x = r.data['alunos'][0]['disc'][str(self.disc.id)]
        assert (x['f1'], x['f2'], x['f3'], x['total'], x['j']) == (3, 2, 0, 5, 0)
        resumo = self.client.get(f'/api/v1/alunos/presencas/resumo/?turma_id={self.turma26.id}').data['resultados'][0]
        assert (resumo['f1'], resumo['f2'], resumo['faltas_total']) == (3, 2, 5)
        assert self.client.get(f'/api/v1/alunos/presencas/trimestre/?data=2026-06-10').data['trimestre'] == 2

    def test_caderneta_carrega_faltas_das_presencas(self):
        from datetime import date
        from apps.professores.views import compilar_dados_caderneta
        self.escola.data_inicio_t1, self.escola.data_fim_t1 = date(2026, 2, 1), date(2026, 4, 30)
        self.escola.data_inicio_t2, self.escola.data_fim_t2 = date(2026, 5, 1), date(2026, 8, 31)
        self.escola.save()
        self.user.escola = self.escola
        self._lote(data='2026-03-02', aulas=2)
        self._lote(data='2026-06-01', aulas=1)
        aloc = AlocacaoDocente.objects.get(turma=self.turma26, disciplina=self.disc)
        from rest_framework.test import APIRequestFactory
        req = APIRequestFactory().get('/')
        req.user = self.user
        req.tenant = self.escola
        al = compilar_dados_caderneta(req, aloc.id)[2][0]
        assert (al['t1']['faltas'], al['t2']['faltas'], al['t3']['faltas'], al['faltas_total']) == (2, 1, 0, 3)

    def test_faltas_geral_exporta_resumo_e_detalhado(self):
        self._lote()
        for modo in ('resumo', 'detalhado'):
            for fmt, tipo in (('pdf', 'application/pdf'), ('xlsx', 'spreadsheetml')):
                r = self.client.get(f'/api/v1/alunos/presencas/faltas-geral/?formato={fmt}&modo={modo}&classe=7ª Classe&carimbo=nao')
                assert r.status_code == 200 and tipo in r['Content-Type'], (modo, fmt)
        assert self.client.get('/api/v1/alunos/presencas/faltas-geral/?formato=doc&carimbo=nao').status_code == 400

    def _direccao(self):
        u = Usuario.objects.create_user(email='dir.pres@sige.mz', password='PassDir123!', role='DIRECTOR_ESCOLA', escola=self.escola)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_justificar_quantidade_reduz_faltas_e_pode_anular(self):
        from datetime import date
        self.escola.data_inicio_t1, self.escola.data_fim_t1 = date(2026, 2, 1), date(2026, 4, 30)
        self.escola.save()
        self.user.escola = self.escola
        self._lote(data='2026-03-02', aulas=2)   # 2 faltas
        self._lote(data='2026-03-09', aulas=1)   # +1 falta = 3 no 1.º T
        direcao = self._direccao()
        corpo = {'aluno': str(self.aluno.id), 'disciplina': str(self.disc.id), 'trimestre': 1, 'quantidade': 2, 'motivo': 'doença'}
        # só direcção/secretaria justifica; o professor não
        assert self.client.post('/api/v1/alunos/presencas/justificar-faltas/', corpo, format='json').status_code == 403
        assert direcao.post('/api/v1/alunos/presencas/justificar-faltas/', {**corpo, 'quantidade': 4}, format='json').status_code == 400
        r = direcao.post('/api/v1/alunos/presencas/justificar-faltas/', corpo, format='json')
        assert r.status_code == 200
        pivot = direcao.get('/api/v1/alunos/presencas/faltas-geral/?ano_letivo=2026').data
        x = pivot['alunos'][0]['disc'][str(self.disc.id)]
        assert (x['f1'], x['j']) == (1, 2)          # 3 marcadas - 2 justificadas = 1 efectiva
        assert pivot['alunos'][0]['justificadas_txt'] == 'Mat: 2'
        # a mais antiga (aula dupla) ficou totalmente justificada; a simples continua injustificada
        estados = dict(PresencaAluno.objects.values_list('data', 'status'))
        assert estados[date(2026, 3, 2)] == 'FALTA_JUSTIFICADA' and estados[date(2026, 3, 9)] == 'FALTA_INJUSTIFICADA'
        # a caderneta passa a mostrar as faltas efectivas
        resumo = direcao.get(f'/api/v1/alunos/presencas/resumo/?turma_id={self.turma26.id}').data['resultados'][0]
        assert resumo['f1'] == 1
        # detalhe por data + histórico
        det = direcao.get(f'/api/v1/alunos/presencas/faltas-detalhe/?aluno_id={self.aluno.id}').data
        assert [(f['data'], f['aulas'], f['justificadas'], f['efectivas']) for f in det['faltas']] == [
            ('2026-03-02', 2, 2, 0), ('2026-03-09', 1, 0, 1)]
        assert det['justificacoes'][0]['quantidade'] == 2
        # anular devolve as faltas
        jid = det['justificacoes'][0]['id']
        assert direcao.post('/api/v1/alunos/presencas/anular-justificacao/', {'id': jid}, format='json').status_code == 200
        assert direcao.post('/api/v1/alunos/presencas/anular-justificacao/', {'id': jid}, format='json').status_code == 400
        x = direcao.get('/api/v1/alunos/presencas/faltas-geral/?ano_letivo=2026').data['alunos'][0]['disc'][str(self.disc.id)]
        assert (x['f1'], x['j']) == (3, 0)
        assert PresencaAluno.objects.get(data='2026-03-02').status == 'FALTA_INJUSTIFICADA'

    def test_periodo_vem_do_calendario_de_prazos(self):
        from datetime import date
        self._lote(data='2026-03-02', aulas=1)
        self._lote(data='2026-06-01', aulas=2)
        base = '/api/v1/alunos/presencas/faltas-geral/?ano_letivo=2026&periodo='
        assert self.client.get(base + 'T1').status_code == 400   # calendário sem datas: pede configuração
        self.escola.data_inicio_t1, self.escola.data_fim_t1 = date(2026, 2, 1), date(2026, 4, 30)
        self.escola.data_inicio_t2, self.escola.data_fim_t2 = date(2026, 5, 1), date(2026, 8, 31)
        self.escola.save()
        self.user.escola = self.escola
        t2 = self.client.get(base + 'T2').data['alunos'][0]['disc'][str(self.disc.id)]
        assert (t2['f1'], t2['f2']) == (0, 2)
        pers = self.client.get('/api/v1/alunos/presencas/faltas-geral/?data_inicio=2026-03-01&data_fim=2026-03-31').data
        assert pers['alunos'][0]['total'] == 1

    def test_faltas_geral_professor_so_ve_as_suas_disciplinas(self):
        outro = Professor.objects.create(escola=self.escola, nome='Outro', email='outro.pres@sige.mz', especialidade='Física')
        AlocacaoDocente.objects.create(escola=self.escola, professor=outro, disciplina=self.outra_disc, turma=self.turma26)
        PresencaAluno.objects.create(escola=self.escola, aluno=self.aluno, turma=self.turma26, disciplina=self.outra_disc,
                                     data='2026-03-02', status='FALTA_INJUSTIFICADA', aulas=2)
        self._lote()
        r = self.client.get('/api/v1/alunos/presencas/faltas-geral/')
        assert [d['nome'] for d in r.data['disciplinas']] == ['Matemática']

    def test_parametros_invalidos_dao_400_e_nao_500(self):
        for url in ('/api/v1/alunos/presencas/?turma_id=abc',
                    '/api/v1/alunos/presencas/?data=ontem',
                    '/api/v1/alunos/presencas/resumo/?data_inicio=xx',
                    '/api/v1/alunos/presencas/exportar/?formato=pdf&turma_id=nao-uuid',
                    '/api/v1/alunos/presencas/faltas-trimestre/?aluno_id=1&disciplina_id=2&trimestre=1_TRIMESTRE'):
            assert self.client.get(url).status_code == 400, url

    def test_perfil_sem_permissao_nao_lanca(self):
        sec = Usuario.objects.create_user(email='sec.pres@sige.mz', password='PassSec123!', role='SECRETARIA', escola=self.escola)
        c = APIClient()
        c.force_authenticate(sec)
        res = c.post('/api/v1/alunos/presencas/lote/', {'turma': str(self.turma26.id), 'disciplina': str(self.disc.id),
                     'data': '2026-03-02', 'registos': []}, format='json')
        assert res.status_code == 403
