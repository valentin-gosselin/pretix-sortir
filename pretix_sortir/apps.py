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
        version = '1.0.0'
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


default_app_config = 'pretix_sortir.SortirPluginConfig'