"""Regras do Plano Curricular: Classe/Nível -> Disciplinas -> Área/Secção -> disciplinas da área (com exame).

Este módulo é a fonte única da estrutura curricular da escola. Turmas e matrículas validam contra ele.
"""
import re

SEM_AREA = {'', 'geral', 'ensino geral', 'tronco comum', 'none', 'ensino geral (tronco comum)'}


def chave_classe(nome):
    """Chave estável para comparar '10ª Classe', '10a classe', '10' ou 'Nível 3' sem depender da grafia."""
    texto = str(nome or '').strip().lower()
    if not texto:
        return ('', '')
    m = re.search(r'(?<!\d)(\d+)(?!\d)', texto)
    if m:
        tipo = 'N' if re.search(r'n[ií]vel', texto) else 'C'
        return (tipo, str(int(m.group(1))))
    return ('T', ' '.join(texto.split()))


def mesma_classe(a, b):
    ca, cb = chave_classe(a), chave_classe(b)
    return bool(ca[0]) and ca == cb


def classes_configuradas(escola):
    """Dicionário {nome: tem_exame} das classes/níveis cadastrados no Plano Curricular da escola."""
    cfg = getattr(escola, 'config_classes_exames', None) or {}
    return dict(cfg) if isinstance(cfg, dict) else {}


def nome_classe_oficial(escola, classe):
    for nome in classes_configuradas(escola):
        if mesma_classe(nome, classe):
            return nome
    return None


def classe_tem_exame(escola, classe):
    for nome, tem in classes_configuradas(escola).items():
        if mesma_classe(nome, classe):
            return bool(tem)
    return False


def achar_no_catalogo(escola, nome, excluir_pk=None):
    """Procura no catálogo ignorando maiúsculas/minúsculas e acentos de caixa (igual em SQLite e PostgreSQL)."""
    from .models import DisciplinaCatalogo
    alvo = ' '.join(str(nome or '').split()).casefold()
    for c in DisciplinaCatalogo.objects.filter(escola=escola):
        if c.pk != excluir_pk and c.nome.casefold() == alvo:
            return c
    return None


def disciplinas_da_classe(escola, classe):
    from .models import Disciplina
    return [d for d in Disciplina.objects.filter(escola=escola).order_by('nome') if mesma_classe(d.classe, classe)]


def areas_da_classe(escola, classe):
    from .models import AreaSeccao
    return [a for a in AreaSeccao.objects.filter(escola=escola) if mesma_classe(a.classe, classe)]


def area_valida_para_classe(escola, classe, area):
    """Devolve (ok, mensagem). Se a classe tem áreas, a área escolhida tem de ser uma delas."""
    areas = areas_da_classe(escola, classe)
    if not areas:
        return True, ''
    nome = ' '.join(str(area or '').split()).lower()
    if nome in SEM_AREA:
        return False, f"A {classe} tem Áreas/Secções no Plano Curricular: escolha uma delas."
    if any(a.nome.strip().lower() == nome for a in areas):
        return True, ''
    return False, f"A área '{area}' não existe no Plano Curricular da {classe}."


def sincronizar_disciplina(disciplina):
    """Mantém Disciplina.area / tem_exame coerentes com os vínculos (usados por pautas, notas e exames)."""
    from .models import Disciplina
    vinculos = list(disciplina.vinculos_area.select_related('area').order_by('area__ordem', 'area__nome'))
    if vinculos:
        area = vinculos[0].area.nome[:50]
        tem_exame = any(v.tem_exame for v in vinculos)
    else:
        area = 'Geral'
        tem_exame = False
    Disciplina.objects.filter(pk=disciplina.pk).update(area=area, tem_exame=tem_exame)


def uso_da_classe(escola, classe):
    """Quantas disciplinas, áreas e turmas dependem da classe/nível (para impedir remoções que deixariam órfãos)."""
    from apps.turmas.models import Turma
    return {
        'disciplinas': len(disciplinas_da_classe(escola, classe)),
        'areas': len(areas_da_classe(escola, classe)),
        'turmas': sum(1 for t in Turma.objects.filter(escola=escola) if mesma_classe(t.grau_ano, classe)),
    }


def normalizar_exames(escola):
    """Classe sem exame => nenhuma disciplina dela pode ficar marcada com exame."""
    from .models import AreaSeccaoDisciplina
    for nome, tem in classes_configuradas(escola).items():
        if tem:
            continue
        vinculos = [v for v in AreaSeccaoDisciplina.objects.filter(escola=escola, tem_exame=True).select_related('area', 'disciplina')
                    if mesma_classe(v.area.classe, nome)]
        for v in vinculos:
            v.tem_exame = False
            v.save(update_fields=['tem_exame'])
            sincronizar_disciplina(v.disciplina)


def estrutura(escola):
    """Árvore para os filtros em cascata: classes -> áreas. Nunca devolve dados de outra escola."""
    from .models import AreaSeccao, Disciplina
    regime = getattr(escola, 'regime_curricular', 'CLASSES') or 'CLASSES'
    areas = list(AreaSeccao.objects.filter(escola=escola))
    discs = list(Disciplina.objects.filter(escola=escola).values_list('classe', flat=True))

    def ordem(nome):
        m = re.search(r'\d+', nome)
        return (0, int(m.group(0))) if m else (1, nome.lower())

    classes = []
    for nome in sorted(classes_configuradas(escola), key=ordem):
        classes.append({
            'nome': nome,
            'tem_exame': classe_tem_exame(escola, nome),
            'areas': [{'id': str(a.id), 'nome': a.nome} for a in sorted(areas, key=lambda x: (x.ordem, x.nome.lower())) if mesma_classe(a.classe, nome)],
            'total_disciplinas': sum(1 for c in discs if mesma_classe(c, nome)),
        })
    return {'regime': regime, 'classes': classes}
