"""
Gestion de la navigation pour le plugin Sortir!
"""

from django.dispatch import receiver
from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _

from pretix.control.signals import nav_organizer, nav_event


@receiver(nav_organizer, dispatch_uid="sortir_nav_organizer")
def control_nav_organizer(sender, request=None, **kwargs):
    """
    Ajoute le lien Sortir! dans le menu de l'organisateur.
    """
    if not request.user.has_organizer_permission(request.organizer, 'can_change_organizer_settings', request=request):
        return []

    return [
        {
            'label': _('Sortir!'),
            'icon': 'credit-card',
            'url': reverse('plugins:pretix_sortir:organizer-settings', kwargs={
                'organizer': request.organizer.slug,
            }),
            'active': 'sortir' in request.resolver_match.url_name if request.resolver_match else False,
        }
    ]


@receiver(nav_event, dispatch_uid="sortir_nav_event")
def control_nav_event(sender, request=None, **kwargs):
    """
    Ajoute le lien Sortir! dans le menu de l'événement.
    """
    if not request.user.has_event_permission(request.organizer, request.event, 'can_change_event_settings', request=request):
        return []

    # Vérifie si le plugin est activé pour cet événement
    from .models import SortirEventSettings
    try:
        event_settings = SortirEventSettings.objects.get(event=request.event)
        if not event_settings.enabled:
            # Si désactivé, ne montre le lien que dans les paramètres
            return [{
                'label': _('Sortir!'),
                'icon': 'credit-card',
                'url': reverse('plugins:pretix_sortir:event-settings', kwargs={
                    'organizer': request.organizer.slug,
                    'event': request.event.slug,
                }),
                'active': 'sortir' in request.resolver_match.url_name if request.resolver_match else False,
                'parent': 'settings',  # Dans le sous-menu paramètres
            }]
    except SortirEventSettings.DoesNotExist:
        pass

    # Si activé, affiche le menu complet
    return [
        {
            'label': _('Sortir!'),
            'icon': 'credit-card',
            'url': reverse('plugins:pretix_sortir:event-settings', kwargs={
                'organizer': request.organizer.slug,
                'event': request.event.slug,
            }),
            'active': 'sortir' in request.resolver_match.url_name if request.resolver_match else False,
            'parent': None,  # Menu principal si activé
            'children': [
                {
                    'label': _('Configuration'),
                    'url': reverse('plugins:pretix_sortir:event-settings', kwargs={
                        'organizer': request.organizer.slug,
                        'event': request.event.slug,
                    }),
                    'active': 'event-settings' in request.resolver_match.url_name if request.resolver_match else False,
                },
                {
                    'label': _('Utilisations'),
                    'url': reverse('plugins:pretix_sortir:usage-list', kwargs={
                        'organizer': request.organizer.slug,
                        'event': request.event.slug,
                    }),
                    'active': 'usage-list' in request.resolver_match.url_name if request.resolver_match else False,
                }
            ]
        }
    ]