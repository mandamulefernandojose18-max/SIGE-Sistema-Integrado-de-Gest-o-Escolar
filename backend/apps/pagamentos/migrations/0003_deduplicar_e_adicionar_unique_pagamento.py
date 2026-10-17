# Generated manually for SIGE - Anti-duplicação de facturas do mesmo mês

from django.db import migrations, models


def deduplicar_pagamentos(apps, schema_editor):
    Pagamento = apps.get_model('pagamentos', 'Pagamento')
    from django.db.models import Count

    duplicados = (
        Pagamento.objects.exclude(status='CANCELADO')
        .values('escola_id', 'aluno_id', 'mes_referencia')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )

    for dup in duplicados:
        pags = list(
            Pagamento.objects.filter(
                escola_id=dup['escola_id'],
                aluno_id=dup['aluno_id'],
                mes_referencia=dup['mes_referencia']
            ).exclude(status='CANCELADO').order_by('created_at')
        )
        if len(pags) <= 1:
            continue

        # Se houver algum PAGO, mantém o PAGO. Caso contrário, mantém o primeiro.
        pagos = [p for p in pags if p.status == 'PAGO']
        manter = pagos[0] if pagos else pags[0]

        for p in pags:
            if p.id != manter.id:
                p.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pagamentos', '0002_alter_pagamento_valor_alter_pagamento_valor_pago_and_more'),
    ]

    operations = [
        migrations.RunPython(deduplicar_pagamentos, reverse_code=migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='pagamento',
            constraint=models.UniqueConstraint(
                condition=models.Q(models.Q(('status', 'CANCELADO'), _negated=True)),
                fields=('escola', 'aluno', 'mes_referencia'),
                name='unique_pagamento_aluno_mes'
            ),
        ),
    ]
