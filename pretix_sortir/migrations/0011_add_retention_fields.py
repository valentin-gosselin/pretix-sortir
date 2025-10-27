# Generated manually for RGPD retention fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pretix_sortir', '0010_nullable_user_agent'),
    ]

    operations = [
        migrations.AddField(
            model_name='sortirorganizersettings',
            name='data_retention_days',
            field=models.IntegerField(default=90, help_text='Durée de conservation des données SortirUsage après la fin de l\'événement (RGPD). Recommandé : 90 jours', verbose_name='Durée de conservation (jours)'),
        ),
        migrations.AddField(
            model_name='sortirorganizersettings',
            name='audit_retention_days',
            field=models.IntegerField(default=365, help_text='Durée de conservation des logs d\'audit (RGPD). Recommandé : 365 jours pour sécurité', verbose_name='Durée de conservation des logs (jours)'),
        ),
    ]
