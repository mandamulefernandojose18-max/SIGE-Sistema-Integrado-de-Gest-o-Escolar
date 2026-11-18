from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alunos', '0011_presencaaluno_pedido_justificacao'),
    ]

    operations = [
        migrations.AddField(
            model_name='presencaaluno',
            name='aulas',
            field=models.PositiveSmallIntegerField(
                choices=[(1, 'Aula simples (1)'), (2, 'Aula dupla (2)')], default=1),
        ),
    ]
