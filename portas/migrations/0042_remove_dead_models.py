from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("portas", "0041_pedido_observacoes"),
    ]

    operations = [
        migrations.DeleteModel(name="ItemOrcamento"),
        migrations.DeleteModel(name="Orcamento"),
        migrations.DeleteModel(name="ExtraServico"),
    ]
