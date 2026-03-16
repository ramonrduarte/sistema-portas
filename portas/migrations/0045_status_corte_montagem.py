from django.db import migrations


class Migration(migrations.Migration):
    """
    Converte o status legado 'producao' para 'corte' em Pedido e PedidoStatusLog.
    Também atualiza o campo choices no CharField (sem alteração de schema no banco).
    """

    dependencies = [
        ("portas", "0044_pedidostatuslog"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "UPDATE portas_pedido SET status = 'corte' WHERE status = 'producao';",
                "UPDATE portas_pedidostatuslog SET status = 'corte' WHERE status = 'producao';",
            ],
            reverse_sql=[
                "UPDATE portas_pedido SET status = 'producao' WHERE status = 'corte';",
                "UPDATE portas_pedidostatuslog SET status = 'producao' WHERE status = 'corte';",
            ],
        ),
    ]
