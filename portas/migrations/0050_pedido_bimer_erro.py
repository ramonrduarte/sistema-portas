from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portas', '0049_remove_divisor_alturas_desconto_percentual'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='bimer_erro',
            field=models.TextField(blank=True, default='', verbose_name='Erro ao enviar para o Bimer'),
        ),
    ]
