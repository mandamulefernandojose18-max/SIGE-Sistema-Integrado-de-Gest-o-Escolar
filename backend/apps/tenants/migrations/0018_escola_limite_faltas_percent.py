from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0017_escola_marca_dagua_base64_escola_marca_dagua_modo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='escola',
            name='limite_faltas_percent',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
