import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('escudo', '0005_regra_cor_excluidos'),
    ]

    operations = [
        migrations.CreateModel(
            name='CapturaEscudo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('foto_leitor_cifrada', models.BinaryField(blank=True, editable=False, null=True)),
                ('foto_prova_cifrada', models.BinaryField(blank=True, editable=False, null=True)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('precisao_m', models.PositiveIntegerField(blank=True, null=True)),
                ('aparelho', models.JSONField(blank=True, default=dict, help_text='Modelo, sistema, ecrã, idioma e fuso (nunca o IP)')),
                ('criada_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('leitura', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='capturas', to='escudo.leituraescudo')),
                ('prova', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='capturas', to='escudo.provaescudo')),
            ],
            options={'db_table': 'sige_escudo_capturas', 'ordering': ['-id']},
        ),
    ]
