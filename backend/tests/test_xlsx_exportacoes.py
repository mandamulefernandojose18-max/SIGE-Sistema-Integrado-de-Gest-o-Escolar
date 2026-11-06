"""Cabeçalho da pauta de exames e varredura de todas as exportações Excel (têm de abrir no Excel)."""
import io
import re
import zipfile
import xml.dom.minidom as minidom

import openpyxl
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos.models import Aluno
from apps.disciplinas.models import Disciplina
from apps.notas.models import Nota
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.documentos.services.excel_service import gerar_pauta_exames_xlsx
from apps.documentos.services.xlsx_seguro import validar_xlsx_bytes


def verificar_como_o_excel(dados):
    """Verificações estritas do que faz o Excel recusar/“reparar” um ficheiro."""
    validar_xlsx_bytes(dados)
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        for nome in z.namelist():
            if nome.endswith(('.xml', '.rels')):
                minidom.parseString(z.read(nome))  # XML bem formado
        assert not [n for n in z.namelist() if 'sheetProtection' in z.read(n).decode('utf-8', 'ignore')
                    and n.startswith('xl/worksheets/')], 'folha protegida'
        assert b'workbookProtection' not in z.read('xl/workbook.xml')
        for n in z.namelist():
            if n.startswith('xl/worksheets/sheet'):
                xml = z.read(n).decode('utf-8')
                cols = [(int(a), int(b)) for a, b in re.findall(r'<col [^>]*?min="(\d+)" max="(\d+)"', xml)]
                cols.sort()
                for (a1, b1), (a2, b2) in zip(cols, cols[1:]):
                    assert a2 > b1, f'colunas sobrepostas em {n}'
                for h in re.findall(r'<row [^>]*?ht="([\d.]+)"', xml):
                    assert float(h) <= 409, 'altura de linha acima do limite do Excel'
                for w in re.findall(r'<col [^>]*?width="([\d.]+)"', xml):
                    assert float(w) <= 255, 'largura de coluna acima do limite do Excel'
    wb = openpyxl.load_workbook(io.BytesIO(dados))
    nomes = [ws.title.lower() for ws in wb.worksheets]
    assert len(nomes) == len(set(nomes))
    return wb


def _dados_exames(n_com=2, n_sem=1, nomes_longos=False):
    com = [{'id': f'c{i}', 'nome': 'TIC' if i == 0 else 'Matemática'} for i in range(n_com)]
    sem = [{'id': f's{i}', 'nome': 'Educação Física'} for i in range(n_sem)]
    alunos = [{
        'numero': 1, 'nome': 'Aluno Exemplo da Silva', 'genero': 'M', 'turma': '10ª A',
        'disciplinas': {d['id']: {'frequencia': 12, 'exame_1epoca': 11, 'exame_2epoca': '', 'media': 11.5}
                        for d in com + sem},
        'resultado_final': {'aprovado': 'Aprovado', 'mf': 12, 'disciplinas_reprovou': '---'},
    }]
    return {
        'turma': {'nome': '10ª A', 'grau_ano': '10ª Classe', 'area': ''},
        'disciplinas': com + sem, 'disciplinas_com_exame': com, 'disciplinas_sem_exame': sem,
        'alunos': alunos, 'estatisticas': {'total': 1},
    }


def test_pauta_exames_exame_unido_freq_abreviada_e_colunas_compactas():
    dados = gerar_pauta_exames_xlsx(_dados_exames(), {'nome': 'Escola Teste'})
    wb = verificar_como_o_excel(dados)
    ws = wb.active
    valores = [c.value for row in ws.iter_rows(min_row=4, max_row=6) for c in row if c.value]
    assert valores.count('Exame') == 2          # uma vez por disciplina com exame (não por época)
    assert 'Frequência' not in valores and valores.count('Freq.') == 3
    assert valores.count('1ª') == 2 and valores.count('2ª') == 2
    fundidas = {str(r) for r in ws.merged_cells.ranges}
    assert 'G5:H5' in fundidas                   # Exame sobre as colunas 1ª e 2ª
    larg = lambda col: ws.column_dimensions[col].width
    assert larg('F') <= 9 and larg('G') <= 9      # notas: colunas estreitas
    # «TIC» (cabeçalho fundido) cabe sem alargar desnecessariamente o bloco
    assert sum(larg(c) for c in 'FGHI') < 40


def test_tabela_opaca_com_moldura_e_linhas_avancadas():
    ws = verificar_como_o_excel(gerar_pauta_exames_xlsx(_dados_exames(), {'nome': 'Escola Teste'})).active
    # moldura grossa à volta e canto superior esquerdo opaco
    a4 = ws['A4']
    assert a4.border.left.style == 'thick' and a4.border.top.style == 'thick'
    # linha dupla por baixo do cabeçalho (última linha de cabeçalho -> primeira de dados)
    assert ws['A7'].border.top.style == 'double' or ws['F6'].border.bottom.style == 'double'
    # separação média entre blocos de disciplina e pontilhado entre linhas de dados
    assert ws['F7'].border.left.style == 'medium'
    # nenhuma célula da tabela fica transparente
    for linha in ws.iter_rows(min_row=4, max_row=7, max_col=12):
        for c in linha:
            if isinstance(c, openpyxl.cell.cell.MergedCell):
                continue  # o openpyxl não relê o estilo das células fundidas secundárias
            assert c.fill.fill_type == 'solid', c.coordinate


def test_nome_do_aluno_cabe_numa_linha_sem_corte():
    d = _dados_exames()
    d['alunos'][0]['nome'] = 'Viviana Yolanda Mandamule'
    ws = verificar_como_o_excel(gerar_pauta_exames_xlsx(d, {'nome': 'E'})).active
    assert ws.column_dimensions['C'].width >= len('Viviana Yolanda Mandamule') * 1.2
    assert (ws.row_dimensions[7].height or 0) >= 20


def test_palavras_nunca_partidas_e_freq_unida_sem_exame():
    d = _dados_exames(n_com=1, n_sem=1)
    d['disciplinas_sem_exame'][0]['nome'] = 'Agropecuária'
    d['alunos'][0]['resultado_final']['aprovado'] = 'Reprovado'
    ws = verificar_como_o_excel(gerar_pauta_exames_xlsx(d, {'nome': 'E'})).active
    fundidas = {str(r) for r in ws.merged_cells.ranges}
    assert 'J5:J6' in fundidas                    # Freq. unida nas 2 linhas (sem exame)
    assert ws.column_dimensions['J'].width >= len('Agropecuária') * 1.3
    assert ws.column_dimensions['K'].width >= len('Reprovado(a)') * 1.3 - 1


def test_cabecalho_fundido_longo_cabe_sem_cortar_palavra():
    d = _dados_exames()
    d['disciplinas_com_exame'][0]['nome'] = 'Empreendedorismo'
    ws = verificar_como_o_excel(gerar_pauta_exames_xlsx(d, {'nome': 'E'})).active
    assert sum(ws.column_dimensions[c].width for c in 'FGHI') >= len('Empreendedorismo')


@pytest.mark.django_db
class TestVarreduraExcel:
    def setup_method(self):
        self.client = APIClient()
        plano = Plano.objects.create(nome='PLANO_XLSX', preco=1500, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Primaria e Secundaria', nif_cnpj='55667788',
                                            email='xlsx@escola.mz', status='ATIVA', plano=plano)
        Usuario.objects.create_user(email='admin.xlsx@escola.mz', password='DocPassword123!',
                                    role='ADMIN_ESCOLA', escola=self.escola)
        self.turma = Turma.objects.create(escola=self.escola, nome='10ª A/B: "1"', grau_ano='10ª Classe', ano_letivo='2026')
        d1 = Disciplina.objects.create(escola=self.escola, nome='=Matemática', codigo='MAT-10', ano_letivo='2026')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='2026111',
                                          nome='+Estudante Teste', data_nascimento='2009-03-15', genero='M')
        for per in ('1_TRIMESTRE', '2_TRIMESTRE'):
            Nota.objects.create(escola=self.escola, aluno=self.aluno, turma=self.turma, disciplina=d1,
                                periodo=per, media_final=14, resultado='Aprovado')
        res = self.client.post('/api/v1/auth/login/', {'email': 'admin.xlsx@escola.mz', 'password': 'DocPassword123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")

    def _urls(self):
        t, a = self.turma.id, self.aluno.id
        return [
            f'/api/v1/pautas/turma/{t}/export-xlsx/?periodo=1_TRIMESTRE',
            f'/api/v1/pautas/turma/{t}/export-xlsx/?periodo=1_TRIMESTRE&orientacao=portrait',
            f'/api/v1/pautas/exames/turma/{t}/xlsx?anoLetivo=2026',
            '/api/v1/pautas/estatisticas-gerais/xlsx?anoLetivo=2026',
            f'/api/v1/pautas/turma/{t}/acta-xlsx?anoLetivo=2026',
            f'/api/v1/pautas/turma/{t}/acta-xlsx?anoLetivo=2026&orientacao=portrait',
            f'/api/v1/impressao/boletim/{a}/xlsx?anoLetivo=2026',
            f'/api/v1/impressao/declaracao/{a}/xlsx?anoLetivo=2026',
            f'/api/v1/impressao/certificado/{a}/xlsx?anoLetivo=2026',
            f'/api/v1/impressao/lote/turma/{t}/xlsx?tipo=BOLETIM&anoLetivo=2026',
        ]

    def test_todas_as_exportacoes_xlsx_abrem(self):
        vistos = 0
        for url in self._urls():
            res = self.client.get(url)
            assert res.status_code == 200, (url, res.status_code)
            assert 'spreadsheetml' in res['Content-Type'], url
            assert 'attachment' in res['Content-Disposition'] and '.xlsx' in res['Content-Disposition'], url
            assert res.content[:2] == b'PK', url
            verificar_como_o_excel(res.content)
            vistos += 1
        assert vistos == len(self._urls())
