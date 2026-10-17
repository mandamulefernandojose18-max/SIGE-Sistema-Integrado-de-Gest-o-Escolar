from django.db import migrations

def renomear_planos(apps, schema_editor):
    SaasPlano = apps.get_model('tenants', 'SaasPlano')
    SaasPlano.objects.filter(nome__icontains='Moçambique').update(nome='Plano Básico')
    SaasPlano.objects.filter(nome__icontains='Mocambique').update(nome='Plano Básico')
    Plano = apps.get_model('tenants', 'Plano')
    Plano.objects.filter(nome__icontains='Moçambique').update(nome='Plano Básico')
    Plano.objects.filter(nome__icontains='Mocambique').update(nome='Plano Básico')

def reverter(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0010_escola_galeria_fundos_escola_imagem_fundo_base64_and_more'),
    ]

    operations = [
        migrations.RunPython(renomear_planos, reverter),
    ]
