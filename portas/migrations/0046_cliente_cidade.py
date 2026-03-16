from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portas", "0045_status_corte_montagem"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="cidade",
            field=models.CharField(blank=True, max_length=100, verbose_name="Cidade"),
        ),
    ]
