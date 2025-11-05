# Generated manually 2025-09-23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pretix_sortir', '0005_set_event_enabled_default_true'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sortirorganizersettings',
            name='api_url_test',
            field=models.URLField(
                blank=True,
                default='',
                verbose_name='URL API Test',
                help_text='URL de l\'API APRAS de test (fournie par l\'APRAS pour les tests)'
            ),
        ),
        migrations.AlterField(
            model_name='sortirorganizersettings',
            name='api_url_production',
            field=models.URLField(
                blank=True,
                default='',
                verbose_name='URL API Production',
                help_text='URL de l\'API APRAS en production (fournie par l\'APRAS après validation)'
            ),
        ),
    ]