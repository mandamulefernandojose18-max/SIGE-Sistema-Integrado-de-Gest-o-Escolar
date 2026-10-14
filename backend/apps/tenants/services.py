from datetime import datetime
from django.utils import timezone
from .models import Escola, AnoLectivo

def garantir_anos_lectivos_escola(escola):
    """
    Garante que a escola possui todos os anos lectivos registados automaticamente:
    - Ano civil actual (ex: 2026, 2027 conforme o tempo avança)
    - Anos lectivos findos mínimos históricos (ex: 2023, 2024, 2025, 2026)
    - Ano lectivo activo configurado na Escola (escola.ano_letivo_ativo)
    - Quaisquer anos presentes em Turmas, Alunos ou Pautas da instituição
    - Em cada novo ano lectivo que se inicia, cria automaticamente o novo ano.
    """
    if not escola:
        return []

    ano_atual = timezone.now().year
    ano_ativo = str(escola.ano_letivo_ativo or ano_atual).strip()

    # Base mínima histórica: do ano 2023 até ao ano actual
    ano_inicio = min(2023, ano_atual - 3)
    anos_set = {str(y) for y in range(ano_inicio, ano_atual + 1)}
    if ano_ativo and ano_ativo.isdigit():
        anos_set.add(ano_ativo)

    # Adicionar anos detectados dinamicamente no banco para esta escola
    try:
        from apps.turmas.models import Turma
        turmas_anos = Turma.objects.filter(escola=escola).values_list('ano_letivo', flat=True).distinct()
        for y in turmas_anos:
            if y and str(y).strip().isdigit():
                anos_set.add(str(y).strip())
    except Exception:
        pass

    try:
        from apps.alunos.models import Aluno
        alunos_anos = Aluno.objects.filter(escola=escola).values_list('ano_ingresso', flat=True).distinct()
        for y in alunos_anos:
            if y and str(y).strip().isdigit():
                anos_set.add(str(y).strip())
    except Exception:
        pass

    try:
        from apps.pautas.models import Pauta
        pautas_anos = Pauta.objects.filter(escola=escola).values_list('ano_letivo', flat=True).distinct()
        for y in pautas_anos:
            if y and str(y).strip().isdigit():
                anos_set.add(str(y).strip())
    except Exception:
        pass

    # Criar ou actualizar cada ano lectivo
    for ano_str in sorted(anos_set):
        is_ativo = (ano_str == ano_ativo)
        desc = f"Ano Lectivo de {ano_str}"
        ano_obj, created = AnoLectivo.objects.get_or_create(
            escola=escola,
            ano=ano_str,
            defaults={
                'descricao': desc,
                'ativo': is_ativo,
            }
        )
        if not created and ano_obj.ativo != is_ativo:
            ano_obj.ativo = is_ativo
            if not ano_obj.descricao:
                ano_obj.descricao = desc
            ano_obj.save(update_fields=['ativo', 'descricao'])

    return list(AnoLectivo.objects.filter(escola=escola).order_by('-ano'))
