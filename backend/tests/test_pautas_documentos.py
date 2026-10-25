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

    def test_conexao_automatica_caderneta_boletim_declaracao_certificado(self):
        # 1. Testar Boletim Escolar com notas vindas da Caderneta
        res_bol = self.client.get(f'/api/v1/impressao/boletim/{self.aluno.id}/')
        assert res_bol.status_code == 200
        data_bol = res_bol.data
        assert data_bol['success'] is True
        assert len(data_bol['disciplinas']) >= 2
        # Verificar se as notas 16 e 15 estão presentes
        disc_mat = next((d for d in data_bol['disciplinas'] if d['nome'] == 'Matemática'), None)
        assert disc_mat is not None
        assert disc_mat['t1'] == 16.0
        assert disc_mat['situacao'] == 'Aprovado'

        # 2. Testar Declaração Escolar com notas automáticas
        res_dec = self.client.get(f'/api/v1/impressao/declaracao/{self.aluno.id}/')
        assert res_dec.status_code == 200
        data_dec = res_dec.data
        assert data_dec['success'] is True
        assert len(data_dec['disciplinas']) >= 2
        assert data_dec['resultadoOficial'] == 'Aprovado'

        # 3. Testar Certificado de Habilitações com código de autenticidade e notas
        res_cert = self.client.get(f'/api/v1/impressao/certificado/{self.aluno.id}/')
        assert res_cert.status_code == 200
        data_cert = res_cert.data
        assert data_cert['success'] is True
        assert len(data_cert['disciplinas']) >= 2
        assert data_cert['codigo_autenticidade'].startswith('CERT-')

        # 4. Testar Lote de Impressão da Turma
        res_lote = self.client.get(f'/api/v1/impressao/lote/turma/{self.turma.id}/?tipo=BOLETIM')
        assert res_lote.status_code == 200
        assert res_lote.data['success'] is True
        assert len(res_lote.data['documentos']) == 1
        assert res_lote.data['documentos'][0]['aluno']['matricula'] in ['2026999', self.aluno.matricula]

        # 5. Testar PDFs de Boletim, Declaração e Certificado
        res_b_pdf = self.client.get(f'/api/v1/impressao/boletim/{self.aluno.id}/pdf/')
        assert res_b_pdf.status_code == 200
        assert res_b_pdf['Content-Type'] == 'application/pdf'
        assert len(res_b_pdf.content) > 500

        res_d_pdf = self.client.get(f'/api/v1/impressao/declaracao/{self.aluno.id}/pdf/')
        assert res_d_pdf.status_code == 200
        assert res_d_pdf['Content-Type'] == 'application/pdf'
        assert len(res_d_pdf.content) > 500

        res_c_pdf = self.client.get(f'/api/v1/impressao/certificado/{self.aluno.id}/pdf/')
        assert res_c_pdf.status_code == 200
        assert res_c_pdf['Content-Type'] == 'application/pdf'
        assert len(res_c_pdf.content) > 500

    def test_calculo_automatico_rigoroso_nota_caderneta(self):
        # Criar nota com testes e trabalho:
        # teste1=14, teste2=16 -> MAC = 15.0
        # avaliacao_trimestral=15 -> MT = (2*15 + 15)/3 = 15
        nota_teste = Nota(
            escola=self.escola,
            aluno=self.aluno,
            turma=self.turma,
            disciplina=self.disc1,
            periodo='2_TRIMESTRE',
            teste1=14,
            teste2=16,
            avaliacao_trimestral=15
        )
        nota_teste.save()
        assert nota_teste.media_final == 15.0
        assert nota_teste.resultado == 'Aprovado'

    def test_aluno_sem_notas_na_caderneta_nao_tem_dados_ficticios(self):
        # Criar aluno sem notas em nenhuma disciplina
        aluno_sem_notas = Aluno.objects.create(
            escola=self.escola,
            turma=self.turma,
            matricula='2026888',
            nome='Aluno Sem Avaliacao',
            data_nascimento='2009-05-20',
            genero='F'
        )

        # 1. Pauta da Turma: o aluno sem notas deve ter '-' nas notas e não reprovar por zero fictício
        res_pauta = self.client.get(f'/api/v1/pautas/turma/{self.turma.id}/completa/?periodo=1_TRIMESTRE')
        assert res_pauta.status_code == 200
        pauta_aluno = next(a for a in res_pauta.data['alunos'] if a['id'] == str(aluno_sem_notas.id))
        assert pauta_aluno['notas'][str(self.disc1.id)]['media_final'] == '-'
        assert pauta_aluno['notas'][str(self.disc2.id)]['media_final'] == '-'
        assert pauta_aluno['media_geral'] == '-'
        assert pauta_aluno['resultado'] == 'Pendente'

        # 2. Boletim Escolar: disciplinas não avaliadas devem ter '-' e média global '-' (sem 13 ou 14 fictício)
        res_bol = self.client.get(f'/api/v1/impressao/boletim/{aluno_sem_notas.id}/')
        assert res_bol.status_code == 200
        bol_data = res_bol.data
        for d in bol_data['disciplinas']:
            assert d['t1'] == '-'
            assert d['t2'] == '-'
            assert d['t3'] == '-'
            assert d['media_anual'] == '-'
            assert d['situacao'] == 'Pendente'
        assert bol_data['mediaGlobal'] == '-'
        assert bol_data['situacaoGlobal'] == 'Pendente'

        # 3. Certificado: disciplinas não avaliadas devem ter '-' (sem 14 fictício)
        res_cert = self.client.get(f'/api/v1/impressao/certificado/{aluno_sem_notas.id}/')
        assert res_cert.status_code == 200
        cert_data = res_cert.data
        for d in cert_data['disciplinas']:
            assert d['notaFinal'] == '-'
            assert d['mediaFinal'] == '-'
        assert cert_data['mediaGlobal'] == '-'

    def test_pauta_so_e_so_tem_disciplinas_daquela_area_ou_seccao(self):
        # 1. Criar turma de Ciências com Biologia (11ª Classe)
        turma_ciencias_bio = Turma.objects.create(
            escola=self.escola,
            nome='11ª A',
            grau_ano='11ª Classe',
            area='Ciências com Biologia',
            ano_letivo='2026'
        )

        # 2. Criar turma de Letras com Geografia (11ª Classe)
        turma_letras_geo = Turma.objects.create(
            escola=self.escola,
            nome='11ª B',
            grau_ano='11ª Classe',
            area='Letras com Geografia',
            ano_letivo='2026'
        )

        # 3. Criar disciplinas de Ciências com Biologia
        d_lp_cb = Disciplina.objects.create(escola=self.escola, nome='Língua Portuguesa', codigo='LP-11CB', classe='11ª Classe', area='Ciências com Biologia', ano_letivo='2026')
        d_mat_cb = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT-11CB', classe='11ª Classe', area='Ciências com Biologia', ano_letivo='2026')
        d_bio_cb = Disciplina.objects.create(escola=self.escola, nome='Biologia', codigo='BIO-11CB', classe='11ª Classe', area='Ciências com Biologia', ano_letivo='2026')
        d_qui_cb = Disciplina.objects.create(escola=self.escola, nome='Química', codigo='QUI-11CB', classe='11ª Classe', area='Ciências com Biologia', ano_letivo='2026')
        d_fis_cb = Disciplina.objects.create(escola=self.escola, nome='Física', codigo='FIS-11CB', classe='11ª Classe', area='Ciências com Biologia', ano_letivo='2026')

        # 4. Criar disciplinas de Ciências com Desenho
        d_dgd = Disciplina.objects.create(escola=self.escola, nome='Desenho e Geometria Descritiva', codigo='DGD-11CD', classe='11ª Classe', area='Ciências com Desenho', ano_letivo='2026')

        # 5. Criar disciplinas de Letras com Geografia
        d_fran = Disciplina.objects.create(escola=self.escola, nome='Língua Francesa', codigo='FRAN-11LG', classe='11ª Classe', area='Letras com Geografia', ano_letivo='2026')
        d_his_lg = Disciplina.objects.create(escola=self.escola, nome='História', codigo='HIS-11LG', classe='11ª Classe', area='Letras com Geografia', ano_letivo='2026')
        d_geo_lg = Disciplina.objects.create(escola=self.escola, nome='Geografia', codigo='GEO-11LG', classe='11ª Classe', area='Letras com Geografia', ano_letivo='2026')

        # 6. Criar disciplina de Letras com História
        d_lit = Disciplina.objects.create(escola=self.escola, nome='Introdução à Literatura', codigo='LIT-11LH', classe='11ª Classe', area='Letras com História', ano_letivo='2026')

        # Matricular alunos em cada turma
        aluno_cb = Aluno.objects.create(escola=self.escola, turma=turma_ciencias_bio, matricula='2026111', nome='Estudante de Ciencias', data_nascimento='2008-01-01', genero='M')
        aluno_lg = Aluno.objects.create(escola=self.escola, turma=turma_letras_geo, matricula='2026222', nome='Estudante de Letras', data_nascimento='2008-02-02', genero='F')

        Nota.objects.create(escola=self.escola, aluno=aluno_cb, turma=turma_ciencias_bio, disciplina=d_bio_cb, periodo='1_TRIMESTRE', media_final=15, resultado='Aprovado')
        Nota.objects.create(escola=self.escola, aluno=aluno_lg, turma=turma_letras_geo, disciplina=d_fran, periodo='1_TRIMESTRE', media_final=16, resultado='Aprovado')

        # TESTE 1: Pauta da Turma de Ciências com Biologia
        res_cb = self.client.get(f'/api/v1/pautas/turma/{turma_ciencias_bio.id}/completa/?periodo=1_TRIMESTRE')
        assert res_cb.status_code == 200
        discs_cb = res_cb.data['disciplinas']
        codigos_cb = [d['codigo'] for d in discs_cb]
        nomes_cb = [d['nome'] for d in discs_cb]

        # DEVE conter as disciplinas da área de Ciências com Biologia
        assert 'BIO-11CB' in codigos_cb
        assert 'MAT-11CB' in codigos_cb
        assert 'QUI-11CB' in codigos_cb
        assert 'FIS-11CB' in codigos_cb
        assert 'LP-11CB' in codigos_cb

        # NÃO PODE DE JEITO NENHUM conter disciplinas de outras áreas/secções
        assert 'DGD-11CD' not in codigos_cb, "Pauta de Ciências com Biologia não deve ter Desenho/DGD"
        assert 'FRAN-11LG' not in codigos_cb, "Pauta de Ciências com Biologia não deve ter Língua Francesa"
        assert 'HIS-11LG' not in codigos_cb, "Pauta de Ciências com Biologia não deve ter História"
        assert 'GEO-11LG' not in codigos_cb, "Pauta de Ciências com Biologia não deve ter Geografia"
        assert 'LIT-11LH' not in codigos_cb, "Pauta de Ciências com Biologia não deve ter Literatura"
        assert 'Desenho e Geometria Descritiva' not in nomes_cb
        assert 'Língua Francesa' not in nomes_cb

        # TESTE 2: Pauta da Turma de Letras com Geografia
        res_lg = self.client.get(f'/api/v1/pautas/turma/{turma_letras_geo.id}/completa/?periodo=1_TRIMESTRE')
        assert res_lg.status_code == 200
        discs_lg = res_lg.data['disciplinas']
        codigos_lg = [d['codigo'] for d in discs_lg]
        nomes_lg = [d['nome'] for d in discs_lg]

        # DEVE conter as disciplinas de Letras com Geografia
        assert 'FRAN-11LG' in codigos_lg
        assert 'HIS-11LG' in codigos_lg
        assert 'GEO-11LG' in codigos_lg

        # NÃO PODE conter disciplinas de Ciências nem Literatura
        assert 'BIO-11CB' not in codigos_lg, "Pauta de Letras não deve ter Biologia"
        assert 'FIS-11CB' not in codigos_lg, "Pauta de Letras não deve ter Física"
        assert 'QUI-11CB' not in codigos_lg, "Pauta de Letras não deve ter Química"
        assert 'DGD-11CD' not in codigos_lg, "Pauta de Letras não deve ter Desenho/DGD"
        assert 'LIT-11LH' not in codigos_lg, "Pauta de Letras com Geografia não deve ter Literatura (que é de Letras com História)"
        assert 'Biologia' not in nomes_lg
        assert 'Física' not in nomes_lg
        assert 'Química' not in nomes_lg

        # TESTE 3: Exportação de PDF, XLSX e DOCX para Ciências com Biologia
        res_pdf = self.client.get(f'/api/v1/pautas/turma/{turma_ciencias_bio.id}/pdf/?periodo=1_TRIMESTRE')
        assert res_pdf.status_code == 200
        assert res_pdf['Content-Type'] == 'application/pdf'

        res_xlsx = self.client.get(f'/api/v1/pautas/turma/{turma_ciencias_bio.id}/export-xlsx/?periodo=1_TRIMESTRE')
        assert res_xlsx.status_code == 200

        res_docx = self.client.get(f'/api/v1/pautas/turma/{turma_ciencias_bio.id}/docx/?periodo=1_TRIMESTRE')
        assert res_docx.status_code == 200

        # TESTE 4: Pauta da Turma de Ciências com Geografia (Regra expressa do usuário)
        # "Por exemplo Ciencias com Geografia, nao tem Historia, Frances, Biologia, Desenho e Geometria Descritiva"
        turma_cg = Turma.objects.create(
            escola=self.escola,
            nome='11ª Classe CG',
            grau_ano='11ª Classe',
            area='Ciências com Geografia',
            turno='MANHA',
            ano_letivo='2026'
        )
        d_geo_cg = Disciplina.objects.create(escola=self.escola, nome='Geografia', codigo='GEO-11CG', classe='11ª Classe', area='Ciências com Geografia', ano_letivo='2026')
        d_mat_cg = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT-11CG', classe='11ª Classe', area='Ciências com Geografia', ano_letivo='2026')
        d_qui_cg = Disciplina.objects.create(escola=self.escola, nome='Química', codigo='QUI-11CG', classe='11ª Classe', area='Ciências com Geografia', ano_letivo='2026')

        res_cg = self.client.get(f'/api/v1/pautas/turma/{turma_cg.id}/completa/?periodo=1_TRIMESTRE')
        assert res_cg.status_code == 200
        discs_cg = res_cg.data['disciplinas']
        codigos_cg = [d['codigo'] for d in discs_cg]
        nomes_cg = [d['nome'] for d in discs_cg]

        # DEVE conter Geografia e disciplinas da área de Ciências com Geografia
        assert 'GEO-11CG' in codigos_cg
        assert 'Geografia' in nomes_cg

        # NÃO PODE conter: História, Francês, Biologia, Desenho/DGD, Literatura
        assert 'História' not in nomes_cg, "Ciências com Geografia não pode ter História"
        assert 'Língua Francesa' not in nomes_cg, "Ciências com Geografia não pode ter Língua Francesa"
        assert 'Biologia' not in nomes_cg, "Ciências com Geografia não pode ter Biologia"
        assert 'Desenho e Geometria Descritiva' not in nomes_cg, "Ciências com Geografia não pode ter Desenho e Geometria Descritiva"
        assert 'Introdução à Literatura' not in nomes_cg, "Ciências com Geografia não pode ter Literatura"

        # Nomes das disciplinas não devem estar abreviados
        for n in nomes_cg:
            assert '-' not in n, f"Nome da disciplina não deve ser código abreviado: {n}"

    def test_mfd_somente_quando_3_trimestres_disponiveis(self):
        from apps.professores.models import Professor, AlocacaoDocente
        prof = Professor.objects.create(escola=self.escola, nome='Prof', apelido='Docente', email='prof.docente@sige.mz', especialidade='Matemática')
        aloc = AlocacaoDocente.objects.create(escola=self.escola, professor=prof, turma=self.turma, disciplina=self.disc1)

        # 1. Aluno apenas com 1º trimestre lançado: MFD deve ser None na caderneta e '-' na pauta
        res_cad = self.client.get(f'/api/v1/professores/caderneta/{aloc.id}/completa')
        assert res_cad.status_code == 200
        aluno_cad = next(a for a in res_cad.data['data']['alunos'] if a['alunoId'] == str(self.aluno.id))
        assert aluno_cad['numero'] == 1
        assert aluno_cad['t1']['mt'] == 16.0
        assert aluno_cad['t2']['mt'] is None
        assert aluno_cad['t3']['mt'] is None
        assert aluno_cad['mfd'] is None, "MFD não pode ser calculado se falta o 2º e 3º trimestre"

        res_pauta = self.client.get(f'/api/v1/pautas/turma/{self.turma.id}/completa/?periodo=ANUAL')
        assert res_pauta.status_code == 200
        aluno_pauta = next(a for a in res_pauta.data['alunos'] if a['id'] == str(self.aluno.id))
        assert aluno_pauta['numero'] == 1
        assert aluno_pauta['notas'][str(self.disc1.id)]['mfd'] == '-', "Na pauta anual, MFD deve ser '-' se faltam trimestres"

        # Validar Acta: apenas trimestres com notas lançadas devem ser marcados como disponíveis e avaliados
        tc1 = res_pauta.data['trimestresComNotas']
        assert tc1['t1'] is True
        assert tc1['t2'] is False, "T2 sem notas não pode estar disponível na acta"
        assert tc1['t3'] is False, "T3 sem notas não pode estar disponível na acta"
        assert tc1['fimAno'] is False, "Fim do ano não pode estar disponível se faltam trimestres"
        ta1 = res_pauta.data['tabelaAproveitamento']
        assert ta1['t1']['avaliados']['hm'] == 1
        assert ta1['t2']['avaliados']['hm'] == 0, "T2 sem notas deve ter 0 avaliados na acta"
        assert ta1['t3']['avaliados']['hm'] == 0, "T3 sem notas deve ter 0 avaliados na acta"
        assert ta1['fimAno']['avaliados']['hm'] == 0, "Fim do ano sem 3 trimestres deve ter 0 avaliados na acta"

        # 2. Lançar 2º trimestre: ainda assim MFD deve ser None / '-'
        Nota.objects.create(escola=self.escola, aluno=self.aluno, turma=self.turma, disciplina=self.disc1, periodo='2_TRIMESTRE', media_final=14, resultado='Aprovado')
        res_cad2 = self.client.get(f'/api/v1/professores/caderneta/{aloc.id}/completa')
        aluno_cad2 = next(a for a in res_cad2.data['data']['alunos'] if a['alunoId'] == str(self.aluno.id))
        assert aluno_cad2['mfd'] is None, "MFD não pode ser calculado se falta o 3º trimestre"

        # 3. Lançar 3º trimestre: agora sim MFD deve ser calculado como a média dos 3 trimestres
        # (16 + 14 + 18) / 3 = 48 / 3 = 16.0
        Nota.objects.create(escola=self.escola, aluno=self.aluno, turma=self.turma, disciplina=self.disc1, periodo='3_TRIMESTRE', media_final=18, resultado='Aprovado')
        res_cad3 = self.client.get(f'/api/v1/professores/caderneta/{aloc.id}/completa')
        aluno_cad3 = next(a for a in res_cad3.data['data']['alunos'] if a['alunoId'] == str(self.aluno.id))
        assert aluno_cad3['mfd'] == 16.0, "MFD deve ser 16.0 quando os 3 trimestres estiverem disponíveis"

        res_pauta3 = self.client.get(f'/api/v1/pautas/turma/{self.turma.id}/completa/?periodo=ANUAL')
        aluno_pauta3 = next(a for a in res_pauta3.data['alunos'] if a['id'] == str(self.aluno.id))
        assert aluno_pauta3['notas'][str(self.disc1.id)]['mfd'] == 16

        tc3 = res_pauta3.data['trimestresComNotas']
        assert tc3['t1'] is True
        assert tc3['t2'] is True
        assert tc3['t3'] is True
        assert tc3['fimAno'] is True
        ta3 = res_pauta3.data['tabelaAproveitamento']
        assert ta3['t1']['avaliados']['hm'] == 1
        assert ta3['t2']['avaliados']['hm'] == 1
        assert ta3['t3']['avaliados']['hm'] == 1
        assert ta3['fimAno']['avaliados']['hm'] == 1

    def test_pauta_exames_download_xlsx_e_pdf(self):
        res_xlsx = self.client.get(f'/api/v1/pautas/exames/turma/{self.turma.id}/xlsx?anoLetivo=2026')
        assert res_xlsx.status_code == 200
        assert res_xlsx['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert len(res_xlsx.content) > 0

        res_pdf = self.client.get(f'/api/v1/pautas/exames/turma/{self.turma.id}/pdf?anoLetivo=2026')
        assert res_pdf.status_code == 200
        assert res_pdf['Content-Type'] == 'application/pdf'
        assert len(res_pdf.content) > 0




    def test_permissoes_parciais_exames_por_grupo_disciplina(self):
        from apps.professores.models import Professor, AlocacaoDocente

        # 1. Criar dois professores da disciplina de Matemática e um de Física
        prof_mat1 = Professor.objects.create(escola=self.escola, nome='Prof João Matemática', especialidade='Matemática', email='prof.mat1@escola.mz', ativo=True)
        prof_mat2 = Professor.objects.create(escola=self.escola, nome='Prof Pedro Matemática', especialidade='Matemática', email='prof.mat2@escola.mz', ativo=True)
        prof_fis = Professor.objects.create(escola=self.escola, nome='Prof Ana Física', especialidade='Física', email='prof.fis@escola.mz', ativo=True)

        AlocacaoDocente.objects.create(escola=self.escola, professor=prof_mat1, disciplina=self.disc1, turma=self.turma)
        AlocacaoDocente.objects.create(escola=self.escola, professor=prof_mat2, disciplina=self.disc1, turma=self.turma)
        AlocacaoDocente.objects.create(escola=self.escola, professor=prof_fis, disciplina=self.disc2, turma=self.turma)

        # Os usuários dos professores são criados automaticamente no save de Professor com senha = codigo
        u_mat1 = Usuario.objects.filter(professor_id=prof_mat1.id).first()
        u_mat1.set_password('PassProf123!')
        u_mat1.save()

        u_mat2 = Usuario.objects.filter(professor_id=prof_mat2.id).first()
        u_mat2.set_password('PassProf123!')
        u_mat2.save()

        # 2. Consultar endpoint de professores autorizados (como admin)
        res_profs = self.client.get('/api/v1/pautas/exames/professores-autorizados/')
        assert res_profs.status_code == 200
        data_profs = res_profs.data
        assert data_profs['success'] is True
        assert 'disciplinas_com_exame' in data_profs
        assert len(data_profs['disciplinas_com_exame']) >= 2

        # 3. DAP configura permissão parcial: Do grupo de Matemática, APENAS prof_mat1 pode lançar Matemática na 10ª Classe
        res_save_perm = self.client.post('/api/v1/pautas/exames/professores-autorizados/', {
            'modo_permissao': 'ALGUNS_PROFESSORES',
            'autorizacoes': [
                {
                    'professor_id': str(prof_mat1.id),
                    'professor_nome': prof_mat1.nome,
                    'classes': ['10ª Classe'],
                    'disciplinas': ['Matemática'],
                    'ativo': True
                }
            ]
        }, format='json')
        assert res_save_perm.status_code == 200
        assert res_save_perm.data['success'] is True
        assert len(res_save_perm.data['autorizacoes']) == 1
        assert res_save_perm.data['autorizacoes'][0]['disciplinas'] == ['Matemática']

        # 4. Prof Mat 1 (autorizado parcialmente para Matemática) consulta a pauta da turma
        login_mat1 = self.client.post('/api/v1/auth/login/', {'email': u_mat1.email, 'password': 'PassProf123!'}, format='json')
        client_mat1 = APIClient()
        client_mat1.credentials(HTTP_AUTHORIZATION=f"Bearer {login_mat1.data['token']}")

        res_pauta_mat1 = client_mat1.get(f'/api/v1/pautas/exames/turma/{self.turma.id}/')
        assert res_pauta_mat1.status_code == 200
        d_pauta1 = res_pauta_mat1.data['data']
        assert d_pauta1['pode_editar'] is True
        assert d_pauta1['is_permissao_parcial'] is True
        assert str(self.disc1.id) in d_pauta1['disciplinas_autorizadas_ids']
        assert str(self.disc2.id) not in d_pauta1['disciplinas_autorizadas_ids']
        assert 'Matemática' in d_pauta1['disciplinas_autorizadas_nomes']

        # 5. Prof Mat 1 lança notas: Matemática tem sucesso, Física é ignorada ou barrada
        res_post_notas = client_mat1.post(f'/api/v1/pautas/exames/turma/{self.turma.id}/', {
            'ano_letivo': '2026',
            'notas': [
                {'aluno_id': str(self.aluno.id), 'disciplina_id': str(self.disc1.id), 'exame_1epoca': 14.5, 'frequencia': 15.0},
                {'aluno_id': str(self.aluno.id), 'disciplina_id': str(self.disc2.id), 'exame_1epoca': 12.0, 'frequencia': 14.0}
            ]
        }, format='json')
        assert res_post_notas.status_code == 200
        # Apenas 1 nota (Matemática) foi salva
        assert res_post_notas.data['salvos'] == 1

        # 6. Prof Mat 2 (mesmo grupo de disciplina, mas NÃO autorizado pelo DAP) é bloqueado
        login_mat2 = self.client.post('/api/v1/auth/login/', {'email': u_mat2.email, 'password': 'PassProf123!'}, format='json')
        client_mat2 = APIClient()
        client_mat2.credentials(HTTP_AUTHORIZATION=f"Bearer {login_mat2.data['token']}")

        res_pauta_mat2 = client_mat2.get(f'/api/v1/pautas/exames/turma/{self.turma.id}/')
        assert res_pauta_mat2.status_code == 200
        assert res_pauta_mat2.data['data']['pode_editar'] is False

        res_post_mat2 = client_mat2.post(f'/api/v1/pautas/exames/turma/{self.turma.id}/', {
            'ano_letivo': '2026',
            'notas': [{'aluno_id': str(self.aluno.id), 'disciplina_id': str(self.disc1.id), 'exame_1epoca': 15.0}]
        }, format='json')
        assert res_post_mat2.status_code == 403

    def test_emissao_lote_completa_com_mapa_e_todos_documentos_alunos(self):
        # 1. Lote PDF: deve conter Mapa Oficial + Documentos de Cada Aluno
        res_pdf = self.client.get(f'/api/v1/impressao/lote/turma/{self.turma.id}/pdf?tipo=BOLETIM')
        assert res_pdf.status_code == 200
        assert res_pdf['Content-Type'] == 'application/pdf'
        assert len(res_pdf.content) > 1000

        # 2. Lote DOCX: deve conter Mapa Oficial + Documentos de Cada Aluno
        res_docx = self.client.get(f'/api/v1/impressao/lote/turma/{self.turma.id}/docx?tipo=BOLETIM')
        assert res_docx.status_code == 200
        assert 'wordprocessingml' in res_docx['Content-Type']
        assert len(res_docx.content) > 1000

        # 3. Lote XLSX: deve conter folha Mapa de Emissao + aba individual para cada aluno
        res_xlsx = self.client.get(f'/api/v1/impressao/lote/turma/{self.turma.id}/xlsx?tipo=BOLETIM')
        assert res_xlsx.status_code == 200
        assert 'spreadsheetml' in res_xlsx['Content-Type']
        assert len(res_xlsx.content) > 1000

        # 4. Lote ZIP: deve conter Mapa Oficial + Documento Completo Unificado + Documentos Individuais
        res_zip = self.client.get(f'/api/v1/impressao/lote/turma/{self.turma.id}/zip?tipo=BOLETIM')
        assert res_zip.status_code == 200
        assert res_zip['Content-Type'] == 'application/zip'
        assert len(res_zip.content) > 1000

        import zipfile, io
        with zipfile.ZipFile(io.BytesIO(res_zip.content)) as zf:
            zip_names = zf.namelist()
            assert any('00_MAPA_OFICIAL_EMISSAO' in n for n in zip_names)
            assert any('TODOS_DOCUMENTOS_COMPLETO' in n for n in zip_names)
            assert any('documentos_individuais' in n for n in zip_names)
