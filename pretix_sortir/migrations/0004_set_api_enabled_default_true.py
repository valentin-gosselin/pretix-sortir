# Generated manually 2025-09-22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pretix_sortir', '0003_rename_pretix_sort_event_i_5b5c5f_idx_pretix_sort_event_i_9db569_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sortirorganizersettings',
            name='api_enabled',
            field=models.BooleanField(
                default=True,
                verbose_name='Activer Sortir!',
                help_text='Automatiquement activé quand le plugin est installé'
            ),
        ),
    ]