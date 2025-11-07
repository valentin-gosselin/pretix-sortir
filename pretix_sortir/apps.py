"""
Configuration de l'application Django pour le plugin Sortir!
"""

from django.utils.translation import gettext_lazy as _
from pretix.base.plugins import PluginConfig, PluginType


class SortirPluginConfig(PluginConfig):
    """Configuration principale du plugin Sortir!"""

    name = 'pretix_sortir'
    verbose_name = _('Sortir! - Tarif réduit')

    class PretixPluginMeta:
        """Métadonnées requises par Pretix pour le plugin."""

        name = _('Sortir! - Tarif réduit')
        author = 'Gosselico'
        version = '1.0.3'
        category = 'INTEGRATION'
        description = _(
            'Intégration du dispositif Sortir! pour appliquer automatiquement '
            'le tarif réduit après vérification des droits via l\'API APRAS. '
            'Compatible avec les cartes KorriGo Services.'
        )
        visible = True
        restricted = False
        compatibility = "pretix>=2024.7.0"

        # Plugin activable au niveau organisateur et événement
        type = PluginType.RESTRICTION

    @property
    def settings_form_fields(self):
        """Pas de champs de formulaire au niveau global."""
        return {}

    def installed(self, event):
        """Appelé quand le plugin est installé sur un événement."""
        from .models import SortirEventSettings
        SortirEventSettings.objects.get_or_create(event=event, defaults={'enabled': False})

    def ready(self):
        """Appelé quand Django est prêt et le plugin chargé."""
        from . import signals  # noqa: F401
        from . import navigation  # noqa: F401

        super().ready()

        # Auto-activation de l'API si le plugin est installé
        self._auto_enable_api()

        # Auto-collectstatic au démarrage pour s'assurer que les assets sont à jour
        # Ceci est exécuté une seule fois au démarrage de Pretix
        import os
        import logging
        from django.core.management import call_command
        from django.core.cache import cache

        logger = logging.getLogger(__name__)

        # Variable d'environnement pour désactiver si besoin (ex: en dev)
        if os.environ.get('SORTIR_SKIP_AUTOCOLLECT') != '1':
            try:
                # Vérifier si on doit faire un collectstatic
                # On utilise un flag en cache pour éviter de le faire plusieurs fois
                cache_key = f'sortir_collectstatic_v{self.PretixPluginMeta.version}'

                if not cache.get(cache_key):
                    logger.info('[Sortir] Running collectstatic for updated assets...')
                    call_command('collectstatic', '--noinput', verbosity=0)

                    # Vider le cache pour forcer le rechargement des assets
                    # Seulement les clés liées à sortir pour ne pas impacter tout Pretix
                    for key in cache.keys('*sortir*'):
                        cache.delete(key)

                    # Marquer comme fait pour cette version (expire après 24h)
                    cache.set(cache_key, True, 86400)
                    logger.info('[Sortir] Collectstatic completed successfully')
                else:
                    logger.debug('[Sortir] Collectstatic already done for this version')

            except Exception as e:
                # Ne pas faire planter Pretix si le collectstatic échoue
                logger.warning(f'[Sortir] Could not run collectstatic: {e}')

    def _auto_enable_api(self):
        """Active automatiquement l'API pour les organisateurs qui ont le plugin."""
        try:
            from django.db import connection
            from .models import SortirOrganizerSettings

            # Vérifier que les tables existent
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'pretix_sortir_sortirorganizersettings'
                    );
                """)
                if not cursor.fetchone()[0]:
                    return  # Table n'existe pas encore

            # Activer l'API pour tous les organisateurs qui ont le plugin mais API désactivée
            updated = SortirOrganizerSettings.objects.filter(api_enabled=False).update(api_enabled=True)

            if updated > 0:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f'[Sortir] API automatiquement activée pour {updated} organisateur(s)')

        except Exception:
            # Silencieusement ignorer les erreurs (peut arriver pendant les migrations)
            pass


default_app_config = 'pretix_sortir.SortirPluginConfig'