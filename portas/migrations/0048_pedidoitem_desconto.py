from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portas", "0047_pedido_data_previsao"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedidoitem",
            name="desconto",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=None,
                max_digits=10,
                null=True,
                verbose_name="Desconto (R$)",
            ),
        ),
    ]
