import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notas', '0012_folhas_pendentes'),
        ('tenants', '0025_escola_lixeira'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CorrecaoRegisto',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('duracao_seg', models.PositiveIntegerField(default=0)),
                ('n_folhas', models.PositiveIntegerField(default=0)),
                ('caminho_pdf', models.CharField(blank=True, default='', max_length=255)),
                ('caminho_xlsx', models.CharField(blank=True, default='', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('criado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='correcoes_registos', to=settings.AUTH_USER_MODEL)),
                ('escola', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='correcoes_registos', to='tenants.escola')),
                ('prova', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registos', to='notas.provafisica')),
            ],
            options={
                'db_table': 'sige_correcoes_registos',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['escola', 'prova'], name='sige_correc_escola__6fea90_idx')],
            },
        ),
    ]
