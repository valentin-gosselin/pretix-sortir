# Migration to simplify API URL configuration
# Replaces api_url_test + api_url_production + api_mode with a single api_url field

from django.db import migrations, models


def migrate_api_url_forward(apps, schema_editor):
    """
    Copie l'URL active (selon le mode) vers le nouveau champ api_url
    """
    SortirOrganizerSettings = apps.get_model('pretix_sortir', 'SortirOrganizerSettings')

    for settings in SortirOrganizerSettings.objects.all():
        # Copie l'URL selon le mode actif
        if settings.api_mode == 'production' and settings.api_url_production:
            settings.api_url = settings.api_url_production
        elif settings.api_url_test:
            settings.api_url = settings.api_url_test
        # Si aucune URL n'est configurée, api_url reste vide

        settings.save()


def migrate_api_url_backward(apps, schema_editor):
    """
    Restaure api_url vers api_url_test (mode test par défaut)
    """
    SortirOrganizerSettings = apps.get_model('pretix_sortir', 'SortirOrganizerSettings')

    for settings in SortirOrganizerSettings.objects.all():
        if settings.api_url:
            settings.api_url_test = settings.api_url
            settings.api_mode = 'test'
        settings.save()


class Migration(migrations.Migration):

    dependencies = [
        ('pretix_sortir', '0012_add_session_id'),
    ]

    operations = [
        # Étape 1 : Ajouter le nouveau champ api_url
        migrations.AddField(
            model_name='sortirorganizersettings',
            name='api_url',
            field=models.URLField(blank=True, default='', help_text="URL de l'API APRAS (fournie par l'APRAS)", verbose_name='URL API Sortir'),
        ),

        # Étape 2 : Migrer les données
        migrations.RunPython(migrate_api_url_forward, migrate_api_url_backward),

        # Étape 3 : Supprimer les anciens champs
        migrations.RemoveField(
            model_name='sortirorganizersettings',
            name='api_mode',
        ),
        migrations.RemoveField(
            model_name='sortirorganizersettings',
            name='api_url_production',
        ),
        migrations.RemoveField(
            model_name='sortirorganizersettings',
            name='api_url_test',
        ),
    ]
