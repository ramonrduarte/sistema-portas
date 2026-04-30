from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portas", "0055_remove_custo_mao_obra_vidro"),
    ]

    operations = [
        migrations.AddField(
            model_name="bimerconfig",
            name="bimer_id_produto_porta",
            field=models.CharField(
                blank=True,
                default="00A0000AU5",
                help_text="Identificador do produto 'Porta' usado ao enviar pedidos.",
                max_length=50,
                verbose_name="ID produto Porta no Bimer",
            ),
        ),
    ]
