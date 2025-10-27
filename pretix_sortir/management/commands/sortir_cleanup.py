"""
Commande de maintenance pour purger les anciennes données Sortir! (RGPD - PHASE 3)

Usage:
    python -m pretix sortir_cleanup [--dry-run] [--days-usage=90] [--days-audit=365]
"""

import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_scopes import scopes_disabled

logger = logging.getLogger('pretix.plugins.sortir')


class Command(BaseCommand):
    help = 'Purge les anciennes données Sortir! selon la politique de rétention RGPD'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait supprimé sans supprimer réellement',
        )
        parser.add_argument(
            '--days-usage',
            type=int,
            default=None,
            help='Nombre de jours de rétention pour SortirUsage (défaut: depuis config organisateur)',
        )
        parser.add_argument(
            '--days-audit',
            type=int,
            default=None,
            help='Nombre de jours de rétention pour AuditLog (défaut: depuis config organisateur)',
        )

    def handle(self, *args, **options):
        from pretix_sortir.models import SortirUsage, SortirAuditLog, SortirOrganizerSettings

        dry_run = options['dry_run']
        custom_days_usage = options['days_usage']
        custom_days_audit = options['days_audit']

        self.stdout.write(self.style.SUCCESS('=== Sortir! Data Cleanup - RGPD ==='))
        if dry_run:
            self.stdout.write(self.style.WARNING('MODE DRY-RUN : Aucune suppression réelle'))

        with scopes_disabled():
            # 1. NETTOYAGE DES PENDING ORPHELINS (paniers abandonnés > 10 min)
            self.stdout.write('\n--- Nettoyage SortirUsage pending orphelins ---')
            expiry_threshold = timezone.now() - timedelta(minutes=10)

            old_pending = SortirUsage.objects.filter(
                status='pending',
                order__isnull=True,
                created_at__lt=expiry_threshold
            )

            count_pending = old_pending.count()
            if count_pending > 0:
                if not dry_run:
                    old_pending.delete()
                self.stdout.write(self.style.SUCCESS(f'✓ {count_pending} SortirUsage pending orphelins supprimés (paniers abandonnés)'))
            else:
                self.stdout.write('  Aucun pending orphelin à nettoyer')

            # 2. Purge SortirUsage anciens (RGPD)
            self.stdout.write('\n--- Purge SortirUsage (RGPD) ---')
            total_deleted_usage = 0

            for org_settings in SortirOrganizerSettings.objects.all():
                retention_days = custom_days_usage if custom_days_usage else org_settings.data_retention_days
                cutoff_date = timezone.now() - timedelta(days=retention_days)

                # Trouve les événements terminés
                old_usages = SortirUsage.objects.filter(
                    event__organizer=org_settings.organizer,
                    created_at__lt=cutoff_date
                ).select_related('event')

                count = old_usages.count()
                if count > 0:
                    self.stdout.write(
                        f'  Organisateur: {org_settings.organizer.name} '
                        f'({count} SortirUsage de plus de {retention_days} jours)'
                    )

                    if not dry_run:
                        deleted = old_usages.delete()
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Supprimé: {deleted[0]} enregistrements'))
                        total_deleted_usage += deleted[0]
                    else:
                        for usage in old_usages[:5]:  # Affiche les 5 premiers
                            self.stdout.write(
                                f'    - Usage ID {usage.id}: Carte ***{usage.sortir_number_suffix} '
                                f'(Event: {usage.event.slug}, Date: {usage.created_at.date()})'
                            )
                        if count > 5:
                            self.stdout.write(f'    ... et {count - 5} autres')

            # Purge AuditLog
            self.stdout.write('\n--- Purge AuditLog ---')
            total_deleted_audit = 0

            for org_settings in SortirOrganizerSettings.objects.all():
                retention_days = custom_days_audit if custom_days_audit else org_settings.audit_retention_days
                cutoff_date = timezone.now() - timedelta(days=retention_days)

                old_audits = SortirAuditLog.objects.filter(
                    organizer=org_settings.organizer,
                    timestamp__lt=cutoff_date
                )

                count = old_audits.count()
                if count > 0:
                    self.stdout.write(
                        f'  Organisateur: {org_settings.organizer.name} '
                        f'({count} AuditLog de plus de {retention_days} jours)'
                    )

                    if not dry_run:
                        deleted = old_audits.delete()
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Supprimé: {deleted[0]} enregistrements'))
                        total_deleted_audit += deleted[0]
                    else:
                        for audit in old_audits[:5]:
                            self.stdout.write(
                                f'    - Audit ID {audit.id}: {audit.action} '
                                f'({audit.severity}, Date: {audit.timestamp.date()})'
                            )
                        if count > 5:
                            self.stdout.write(f'    ... et {count - 5} autres')

            # Résumé
            self.stdout.write('\n=== Résumé ===')
            if not dry_run:
                self.stdout.write(self.style.SUCCESS(f'✓ SortirUsage supprimés : {total_deleted_usage}'))
                self.stdout.write(self.style.SUCCESS(f'✓ AuditLog supprimés : {total_deleted_audit}'))
                self.stdout.write(self.style.SUCCESS(f'✓ Total : {total_deleted_usage + total_deleted_audit}'))
            else:
                self.stdout.write(self.style.WARNING('Mode DRY-RUN : Aucune suppression effectuée'))
                self.stdout.write(f'  Seraient supprimés : {total_deleted_usage} SortirUsage + {total_deleted_audit} AuditLog')

            self.stdout.write(self.style.SUCCESS('\n✓ Nettoyage terminé'))
