from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('escudo', '0004_regra_exclusao'),
    ]

    operations = [
        migrations.AddField(
            model_name='regraexclusaoescudo',
            name='cor_excluidos',
            field=models.CharField(default='#FDE2E2', help_text='Cor das linhas dos alunos excluídos nas listas (PDF/Excel)', max_length=7),
        ),
    ]
