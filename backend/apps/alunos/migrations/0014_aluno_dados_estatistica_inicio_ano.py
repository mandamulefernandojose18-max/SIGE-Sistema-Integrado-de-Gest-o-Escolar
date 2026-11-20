from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alunos', '0013_justificacao_faltas'),
    ]

    operations = [
        migrations.AddField(
            model_name='aluno',
            name='orfandade',
            field=models.CharField(blank=True, choices=[('NENHUMA', 'Não é órfão'), ('PAI', 'Órfão de pai'), ('MAE', 'Órfão de mãe'), ('AMBOS', 'Órfão de pai e mãe')], default='NENHUMA', max_length=10),
        ),
        migrations.AddField(
            model_name='aluno',
            name='necessidade_especial',
            field=models.CharField(blank=True, choices=[('DV', 'Deficiência visual'), ('DAU', 'Deficiência auditiva'), ('DFM', 'Deficiência física/motora'), ('DAP', 'Dificuldades de aprendizagem'), ('ALB', 'Albinismo'), ('PC', 'Problemas comportamentais'), ('OUTRA', 'Outra necessidade educativa especial')], default='', max_length=10),
        ),
        migrations.AddField(
            model_name='aluno',
            name='meio_transporte',
            field=models.CharField(blank=True, choices=[('A_PE', 'A pé'), ('BICICLETA', 'Bicicleta'), ('MOTORIZADA', 'Motorizada'), ('TRANSPORTE_PUBLICO', 'Transporte público (chapa/machimbombo)'), ('CARRO', 'Carro particular'), ('OUTRO', 'Outro')], default='', max_length=20),
        ),
        migrations.AddField(
            model_name='aluno',
            name='tempo_casa_escola',
            field=models.CharField(blank=True, choices=[('ATE_30', 'Até 30 minutos'), ('DE_30_A_60', 'De 30 a 60 minutos'), ('DE_60_A_90', 'De 60 a 90 minutos'), ('MAIS_90', 'Mais de 90 minutos')], default='', max_length=12),
        ),
        migrations.AddField(
            model_name='aluno',
            name='local_residencia',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
    ]
