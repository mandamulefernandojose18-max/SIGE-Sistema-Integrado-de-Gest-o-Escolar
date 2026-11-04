from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alunos', '0010_presencaaluno_justificacao'),
    ]

    operations = [
        migrations.AddField(
            model_name='presencaaluno',
            name='pedido_justificacao',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='presencaaluno',
            name='pedido_justificacao_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
