# Generated manually for session_id field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pretix_sortir', '0011_add_retention_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='sortirusage',
            name='session_id',
            field=models.CharField(blank=True, default='', help_text='Identifiant anonyme de session pour gérer les corrections', max_length=100, verbose_name='ID de session'),
        ),
    ]
