# Generated manually for SIGE: Adicionar campo config_classes_exames ao modelo Escola

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0012_saascoordenadaspagamento'),
    ]

    operations = [
        migrations.AddField(
            model_name='escola',
            name='config_classes_exames',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
