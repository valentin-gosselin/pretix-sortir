# Generated manually 2025-09-22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pretix_sortir', '0004_set_api_enabled_default_true'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sortireventsettings',
            name='enabled',
            field=models.BooleanField(
                default=True,
                verbose_name='Utiliser Sortir! pour cet événement',
                help_text='Automatiquement activé quand le plugin est activé pour cet événement'
            ),
        ),
    ]