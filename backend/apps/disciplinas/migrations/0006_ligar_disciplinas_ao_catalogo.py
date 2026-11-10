from django.db import migrations


def ligar_disciplinas_existentes(apps, schema_editor):
    """Cria o catálogo a partir dos nomes REAIS já cadastrados em cada escola e liga as disciplinas a ele."""
    Disciplina = apps.get_model('disciplinas', 'Disciplina')
    Catalogo = apps.get_model('disciplinas', 'DisciplinaCatalogo')
    por_escola = {}
    for d in Disciplina.objects.all().only('id', 'escola_id', 'nome'):
        nome = ' '.join((d.nome or '').split())
        if not nome:
            continue
        cache = por_escola.setdefault(d.escola_id, {})
        chave = nome.lower()
        if chave not in cache:
            cache[chave] = Catalogo.objects.create(escola_id=d.escola_id, nome=nome)
        Disciplina.objects.filter(pk=d.pk).update(catalogo=cache[chave])


class Migration(migrations.Migration):

    dependencies = [('disciplinas', '0005_catalogo_disciplinas')]

    operations = [migrations.RunPython(ligar_disciplinas_existentes, migrations.RunPython.noop)]
