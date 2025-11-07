# Generated manually 2025-11-07
"""
Migration pour activer automatiquement l'API Sortir si le plugin est installé.
Cela évite aux utilisateurs d'avoir à l'activer manuellement.
"""

from django.db import migrations

def enable_api_for_existing(apps, schema_editor):
    """Active l'API pour toutes les configurations existantes"""
    SortirOrganizerSettings = apps.get_model('pretix_sortir', 'SortirOrganizerSettings')

    # Active l'API pour toutes les configurations d'organisateur existantes
    updated = SortirOrganizerSettings.objects.filter(api_enabled=False).update(api_enabled=True)

    if updated > 0:
        print(f"[Sortir] API activée automatiquement pour {updated} organisateur(s)")

def disable_api_rollback(apps, schema_editor):
    """Rollback: ne fait rien car on ne veut pas désactiver l'API si elle était déjà activée"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pretix_sortir', '0013_simplify_api_url'),
    ]

    operations = [
        migrations.RunPython(enable_api_for_existing, disable_api_rollback),
    ]