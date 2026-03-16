from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portas", "0046_cliente_cidade"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedido",
            name="data_previsao",
            field=models.DateField(blank=True, null=True, verbose_name="Previsão de entrega"),
        ),
    ]
