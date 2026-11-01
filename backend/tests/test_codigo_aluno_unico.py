import pytest

from apps.alunos.models import Aluno
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma


@pytest.mark.django_db
def test_sufixo_do_codigo_nunca_se_repete_entre_turmas_da_mesma_classe_area():
    plano = Plano.objects.create(nome='PLANO_COD', preco=1500, duracao_dias=30)
    escola = Escola.objects.create(
        nome='Escola Codigo', nif_cnpj='NIF_COD', email='cod@sige.mz', status='ATIVA', plano=plano,
    )
    t2 = Turma.objects.create(escola=escola, nome='Turma 2', grau_ano='11ª Classe', ano_letivo='2026', area='Ciências com Geografia')
    t4 = Turma.objects.create(escola=escola, nome='Turma 4', grau_ano='11ª Classe', ano_letivo='2026', area='Ciências com Geografia')

    codigos = []
    for i, turma in enumerate([t2, t4, t2, t4, t2]):
        a = Aluno.objects.create(
            escola=escola, turma=turma, matricula='x', nome=f'Aluno {i}',
            data_nascimento='2009-01-01', genero='M', ano_ingresso='2026',
            area='Ciências com Geografia',
        )
        codigos.append(a.matricula)

    assert len(set(codigos)) == len(codigos)
    sufixos = [c.split('.')[-1] for c in codigos]
    assert len(set(sufixos)) == len(sufixos)
