from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('escudo', '0003_leitura_vista'),
        ('tenants', '0018_escola_limite_faltas_percent'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegraExclusaoEscudo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('verificar_sempre', models.BooleanField(default=False)),
                ('motivos', models.JSONField(blank=True, default=list)),
                ('faltas_minimo', models.PositiveIntegerField(default=0, help_text='Total de faltas acumuladas a partir do qual o aluno é excluído (0 = não definido)')),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('escola', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='regra_exclusao_escudo', to='tenants.escola')),
            ],
            options={
                'verbose_name': 'Regra de exclusão do Escudo Anti-IA',
                'db_table': 'sige_escudo_regra_exclusao',
            },
        ),
    ]

