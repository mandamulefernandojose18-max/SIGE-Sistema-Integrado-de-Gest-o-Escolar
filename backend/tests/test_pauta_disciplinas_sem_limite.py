import pytest

from apps.disciplinas.models import Disciplina
from apps.pautas.services import obter_disciplinas_pauta_exames_1_ciclo as obter_disciplinas_pauta_turma
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma

NOMES_9 = [
    'Língua Portuguesa', 'Língua Francesa', 'Língua Inglesa', 'História', 'Geografia',
    'Matemática', 'Biologia', 'Física', 'Química', 'Educação Visual', 'TIC',
    'Agropecuária', 'Noções de Empreendedorismo', 'Educação Física', 'Filosofia',
    'Disciplina Extra Do Plano',
]


@pytest.mark.django_db
def test_nenhuma_disciplina_do_plano_e_ocultada_na_9_classe():
    plano = Plano.objects.create(nome='P_SEM_LIMITE', preco=1500, duracao_dias=30)
    escola = Escola.objects.create(nome='Escola Teste Plano', nif_cnpj='99887766', email='plano@escola.mz',
                                   status='ATIVA', plano=plano)
    turma = Turma.objects.create(escola=escola, nome='9ª A', grau_ano='9ª Classe', ano_letivo='2026')
    for i, nome in enumerate(NOMES_9):
        Disciplina.objects.create(escola=escola, nome=nome, codigo=f'D{i}-9', classe='9ª Classe', ano_letivo='2026')

    nomes = {d.nome for d in obter_disciplinas_pauta_turma(turma)}
    assert len(nomes) == len(NOMES_9)
    assert {'Língua Francesa', 'Noções de Empreendedorismo', 'Filosofia', 'Disciplina Extra Do Plano'} <= nomes
