import os
import sys

# Ajustar PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.documentos.services.pdf_service import (
    gerar_certificado_pdf, gerar_declaracao_pdf, gerar_boletim_pdf, gerar_pauta_pdf
)

class MockObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

def run_tests():
    print("=== GERANDO AMOSTRAS DE DOCUMENTOS PARA VALIDAÇÃO VISUAL ===")
    
    escola = MockObj(
        id="esc-1001",
        nome="Escola Secundária de Cambine",
        provincia="Inhambane",
        distrito="Massinga",
        codigo_escola="ESC-1001",
        director_nome="Prof. Dr. António Costa",
        director_carreira="Especialista de Educação",
        chefe_secretaria_nome="Dra. Maria Eunice",
        chefe_secretaria_carreira="Técnica Profissional",
        dap_nome="Manuel Joaquim"
    )

    turma = MockObj(
        id="t-10a",
        nome="10ª Classe A",
        grau_ano="10ª Classe",
        area="Geral",
        turno="Manhã",
        ano_letivo="2026",
        director_turma=MockObj(nome="Manuel", telefone="841234567")
    )

    aluno = MockObj(
        id="al-001",
        nome="Graça Mondlane",
        apelido="Mondlane",
        matricula="MAT-2026-1006",
        genero="F",
        pai="Eduardo Mondlane Jr.",
        mae="Janet Mondlane",
        tipo_documento="Bilhete de Identidade",
        numero_documento="110293847591F",
        bi_numero="110293847591F",
        data_nascimento="2008-07-09",
        distrito="Cidade de Maputo",
        provincia="Maputo",
        turma=turma,
        classe="10ª Classe",
        area="Geral"
    )

    notas_disciplinas = [
        {'nome': 'Língua Portuguesa', 'disciplina': 'Português', 't1': 13, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
        {'nome': 'Inglês', 'disciplina': 'Inglês', 't1': 15, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
        {'nome': 'Francês', 'disciplina': 'Francês', 't1': 14, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
        {'nome': 'História', 'disciplina': 'História', 't1': 11, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
        {'nome': 'Geografia', 'disciplina': 'Geografia', 't1': 13, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
        {'nome': 'Biologia', 'disciplina': 'Biologia', 't1': 11, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
        {'nome': 'Química', 'disciplina': 'Química', 't1': 11, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
        {'nome': 'Física', 'disciplina': 'Física', 't1': 14, 't2': None, 't3': None, 'media_anual': 5, 'situacao': 'Reprovado'},
        {'nome': 'Matemática', 'disciplina': 'Matemática', 't1': 12, 't2': None, 't3': None, 'media_anual': 4, 'situacao': 'Reprovado'},
        {'nome': 'Educação Visual', 'disciplina': 'Desenho / GD', 't1': 12, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
        {'nome': 'Agropecuária', 'disciplina': 'Agropecuária', 't1': 12, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
        {'nome': 'Noções de Empreendedorismo', 'disciplina': 'Noções Empreend.', 't1': 13, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
        {'nome': 'Educação Física', 'disciplina': 'Educação Física', 't1': 16, 't2': None, 't3': None, 'media_anual': 5, 'situacao': 'Reprovado'},
        {'nome': 'TIC\'s', 'disciplina': 'TIC\'s', 't1': 13, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
        {'nome': 'Intr. Filosofia', 'disciplina': 'Intr. Filosofia', 't1': 14, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
        {'nome': 'Psicopedagogia', 'disciplina': 'Psicopedagogia', 't1': 14, 't2': None, 't3': None, 'media_anual': 14, 'situacao': 'Aprovado'},
    ]

    # 1. Certificado PDF
    pdf_cert = gerar_certificado_pdf(
        aluno=aluno,
        escola=escola,
        ano_letivo=2026,
        notas_disciplinas=notas_disciplinas,
        media_global=5,
        codigo_autenticidade="CERT-MZ-5001234567-MAT-2026-1006-2026"
    )
    with open("test_sample_certificado.pdf", "wb") as f:
        f.write(pdf_cert)
    print("[OK] Certificado gerado: test_sample_certificado.pdf (Bytes:", len(pdf_cert), ")")

    # 2. Declaração PDF
    pdf_decl = gerar_declaracao_pdf(
        aluno=aluno,
        escola=escola,
        ano_letivo=2026,
        notas_disciplinas=notas_disciplinas,
        media_global=5,
        director_nome="Prof. Dr. António Costa",
        director_carreira="Especialista de Educação"
    )
    with open("test_sample_declaracao.pdf", "wb") as f:
        f.write(pdf_decl)
    print("[OK] Declaração gerada: test_sample_declaracao.pdf (Bytes:", len(pdf_decl), ")")

    # 3. Boletim PDF
    pdf_bol = gerar_boletim_pdf(
        aluno=aluno,
        escola=escola,
        ano_letivo=2026,
        notas_disciplinas=notas_disciplinas
    )
    with open("test_sample_boletim.pdf", "wb") as f:
        f.write(pdf_bol)
    print("[OK] Boletim gerado: test_sample_boletim.pdf (Bytes:", len(pdf_bol), ")")

    # 4. Pauta PDF
    discs_pauta = [
        MockObj(id="d1", nome="Física", codigo="FIS"),
        MockObj(id="d2", nome="Matemática", codigo="MAT")
    ]
    dados_alunos = [
        {
            'numero': 1,
            'nome': 'DANIEL COUTO COUTO',
            'apelido': 'COUTO',
            'genero': 'M',
            'notasDisciplinas': {
                'FIS': {'t1': 17, 't2': None, 't3': None, 'mfd': 6},
                'MAT': {'t1': 14, 't2': 7, 't3': None, 'mfd': 7}
            },
            'mediasTrimestrais': {'t1': 16, 't2': 7, 't3': '-'},
            'negativas': {'t1': 0, 't2': 1, 't3': 0, 'fimDoAno': 2},
            'media_geral': 7,
            'resultado': 'Reprovado'
        },
        {
            'numero': 2,
            'nome': 'ESPERANÇA CHISSANO CHISSANO',
            'apelido': 'CHISSANO',
            'genero': 'F',
            'notasDisciplinas': {
                'FIS': {'t1': 15, 't2': None, 't3': None, 'mfd': 5},
                'MAT': {'t1': 13, 't2': None, 't3': None, 'mfd': 4}
            },
            'mediasTrimestrais': {'t1': 14, 't2': '-', 't3': '-'},
            'negativas': {'t1': 0, 't2': 0, 't3': 0, 'fimDoAno': 2},
            'media_geral': 5,
            'resultado': 'Reprovado'
        },
        {
            'numero': 3,
            'nome': 'FERNANDO GUEBUZA GUEBUZA',
            'apelido': 'GUEBUZA',
            'genero': 'M',
            'notasDisciplinas': {
                'FIS': {'t1': 11, 't2': None, 't3': None, 'mfd': 4},
                'MAT': {'t1': 12, 't2': None, 't3': None, 'mfd': 4}
            },
            'mediasTrimestrais': {'t1': 12, 't2': '-', 't3': '-'},
            'negativas': {'t1': 0, 't2': 0, 't3': 0, 'fimDoAno': 2},
            'media_geral': 4,
            'resultado': 'Reprovado'
        },
        {
            'numero': 4,
            'nome': 'GRAÇA MONDLANE MONDLANE',
            'apelido': 'MONDLANE',
            'genero': 'F',
            'notasDisciplinas': {
                'FIS': {'t1': 14, 't2': None, 't3': None, 'mfd': 5},
                'MAT': {'t1': 12, 't2': None, 't3': None, 'mfd': 4}
            },
            'mediasTrimestrais': {'t1': 13, 't2': '-', 't3': '-'},
            'negativas': {'t1': 0, 't2': 0, 't3': 0, 'fimDoAno': 2},
            'media_geral': 5,
            'resultado': 'Reprovado'
        }
    ]
    pdf_pauta = gerar_pauta_pdf(
        turma=turma,
        escola=escola,
        periodo="1_TRIMESTRE",
        ano_letivo="2026",
        dados_alunos=dados_alunos,
        disciplinas=discs_pauta,
        orientacao="landscape"
    )
    with open("test_sample_pauta.pdf", "wb") as f:
        f.write(pdf_pauta)
    print("[OK] Pauta gerada: test_sample_pauta.pdf (Bytes:", len(pdf_pauta), ")")

if __name__ == '__main__':
    run_tests()
