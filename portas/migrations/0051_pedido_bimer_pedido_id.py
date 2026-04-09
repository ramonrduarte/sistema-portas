from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portas', '0050_pedido_bimer_erro'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='bimer_pedido_id',
            field=models.CharField(blank=True, default='', max_length=30, verbose_name='ID do pedido no Bimer'),
        ),
    ]
