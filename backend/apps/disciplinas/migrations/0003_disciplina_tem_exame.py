from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disciplinas', '0002_alter_disciplina_carga_horaria_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='disciplina',
            name='tem_exame',
            field=models.BooleanField(default=False, verbose_name='Tem Exame'),
        ),
    ]
