# Generated manually for audit trail

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pretix_sortir', '0008_add_unique_card_constraint'),
    ]

    operations = [
        migrations.CreateModel(
            name='SortirAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date/Heure')),
                ('action', models.CharField(choices=[('card_validation_success', 'Validation carte réussie'), ('card_validation_failed', 'Validation carte échouée'), ('card_revalidation_success', 'Revalidation réussie (order_placed)'), ('card_revalidation_failed', 'Revalidation échouée (order_placed)'), ('rate_limit_triggered', 'Rate limit déclenché'), ('config_changed', 'Configuration modifiée'), ('usage_recorded', 'Utilisation enregistrée'), ('usage_cancelled', 'Utilisation annulée')], db_index=True, max_length=50, verbose_name='Action')),
                ('severity', models.CharField(choices=[('info', 'Information'), ('warning', 'Avertissement'), ('error', 'Erreur'), ('critical', 'Critique')], db_index=True, default='info', max_length=20, verbose_name='Gravité')),
                ('card_hash', models.CharField(blank=True, max_length=64, verbose_name='Hash de carte')),
                ('card_suffix', models.CharField(blank=True, max_length=4, verbose_name='Suffixe carte (4 derniers chiffres)')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='Adresse IP')),
                ('user_agent', models.TextField(blank=True, verbose_name='User Agent')),
                ('details', models.JSONField(blank=True, default=dict, verbose_name='Détails')),
                ('message', models.TextField(blank=True, verbose_name='Message')),
                ('event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pretixbase.event', verbose_name='Événement')),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pretixbase.order', verbose_name='Commande')),
                ('organizer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pretixbase.organizer', verbose_name='Organisateur')),
            ],
            options={
                'verbose_name': 'Audit Sortir!',
                'verbose_name_plural': 'Audits Sortir!',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='sortirauditlog',
            index=models.Index(fields=['timestamp', 'severity'], name='pretix_sort_timesta_idx'),
        ),
        migrations.AddIndex(
            model_name='sortirauditlog',
            index=models.Index(fields=['event', 'timestamp'], name='pretix_sort_event_i_idx'),
        ),
        migrations.AddIndex(
            model_name='sortirauditlog',
            index=models.Index(fields=['action', 'timestamp'], name='pretix_sort_action_idx'),
        ),
        migrations.AddIndex(
            model_name='sortirauditlog',
            index=models.Index(fields=['card_hash'], name='pretix_sort_card_ha_idx'),
        ),
    ]
