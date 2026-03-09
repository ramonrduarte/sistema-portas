# Generated manually 2026-03-09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portas', '0039_puxador_sobreposto'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracaoempresa',
            name='logo_claro',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='empresa/',
                verbose_name='Logo (fundo claro/impressão)',
                help_text='Versão do logo para uso em fundo branco (impressão). Opcional — se não preenchido, usa o logo principal com fundo escuro.',
            ),
        ),
    ]
