from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('escudo', '0006_captura_escudo'),
    ]

    operations = [
        migrations.AddField(
            model_name='capturaescudo',
            name='imei_cifrado',
            field=models.BinaryField(blank=True, editable=False, help_text='IMEI do telefone (15 dígitos, validado), cifrado', null=True),
        ),
        migrations.AddField(
            model_name='capturaescudo',
            name='imagem_aparelho',
            field=models.BinaryField(blank=True, editable=False, help_text='Imagem do modelo do telefone, pesquisada na internet', null=True),
        ),
        migrations.AddField(
            model_name='capturaescudo',
            name='imagem_aparelho_fonte',
            field=models.CharField(blank=True, default='', max_length=300),
        ),
        migrations.AlterField(
            model_name='capturaescudo',
            name='aparelho',
            field=models.JSONField(blank=True, default=dict, help_text='Referências do telefone: marca, modelo, sistema, ecrã, memória, idioma e fuso (nunca o IP)'),
        ),
    ]
