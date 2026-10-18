# Generated manually for SIGE: Adicionar campo regime_curricular ao modelo Escola

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0013_escola_config_classes_exames'),
    ]

    operations = [
        migrations.AddField(
            model_name='escola',
            name='regime_curricular',
            field=models.CharField(
                choices=[
                    ('CLASSES', 'Regime por Classes (1ª à 12ª Classe)'),
                    ('NIVEIS', 'Regime por Níveis (Nível 1, Nível 2...)'),
                ],
                default='CLASSES',
                max_length=20,
            ),
        ),
    ]
