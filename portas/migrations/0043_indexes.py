from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portas", "0042_remove_dead_models"),
    ]

    operations = [
        # Pedido.status — filtrado em todas as views de controle/relatório
        migrations.AddIndex(
            model_name="pedido",
            index=models.Index(fields=["status"], name="pedido_status_idx"),
        ),
        # Pedido.data — filtrado em lista e relatório
        migrations.AddIndex(
            model_name="pedido",
            index=models.Index(fields=["data"], name="pedido_data_idx"),
        ),
        # Pedido.status + data juntos — consulta mais comum no controle de produção
        migrations.AddIndex(
            model_name="pedido",
            index=models.Index(fields=["status", "data"], name="pedido_status_data_idx"),
        ),
        # Cliente.bimer_id — usado na integração Bimer para verificar duplicatas
        migrations.AddIndex(
            model_name="cliente",
            index=models.Index(fields=["bimer_id"], name="cliente_bimer_id_idx"),
        ),
    ]
