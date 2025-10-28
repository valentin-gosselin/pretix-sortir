"""
Vues pour le plugin Sortir! - Version simplifiée
"""

import json
import logging
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView, ListView, TemplateView
from pretix.control.permissions import OrganizerPermissionRequiredMixin
from pretix.control.views.event import EventSettingsViewMixin

from .forms import SortirOrganizerSettingsForm
from .models import SortirOrganizerSettings, SortirEventSettings, SortirItemConfig, SortirUsage

logger = logging.getLogger('pretix.plugins.sortir')

# Applique les filtres de redaction des logs (Sécurité PHASE 2 - Point 7)
from .logging_filters import SensitiveDataFilter, SortirSecurityFilter
if not any(isinstance(f, SensitiveDataFilter) for f in logger.filters):
    logger.addFilter(SensitiveDataFilter())
if not any(isinstance(f, SortirSecurityFilter) for f in logger.filters):
    logger.addFilter(SortirSecurityFilter())


class SortirOrganizerSettingsView(OrganizerPermissionRequiredMixin, UpdateView):
    """Vue de configuration au niveau organisateur."""
    model = SortirOrganizerSettings
    form_class = SortirOrganizerSettingsForm
    template_name = 'pretix_sortir/organizer_settings.html'
    permission = 'can_change_organizer_settings'

    def get_object(self, queryset=None):
        obj, created = SortirOrganizerSettings.objects.get_or_create(
            organizer=self.request.organizer,
            defaults={'api_enabled': False, 'api_mode': 'test'}
        )
        return obj

    def get_success_url(self):
        return reverse('plugins:pretix_sortir:organizer-settings',
                      kwargs={'organizer': self.request.organizer.slug})

    def form_valid(self, form):
        messages.success(self.request, _('Paramètres Sortir! enregistrés.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organizer'] = self.request.organizer
        return context


class SortirEventSettingsView(EventSettingsViewMixin, TemplateView):
    """Vue pour configurer les tarifs Sortir! sur un événement."""
    template_name = 'pretix_sortir/event_settings.html'
    permission = 'can_change_event_settings'

    def get_object(self, queryset=None):
        obj, created = SortirEventSettings.objects.get_or_create(
            event=self.request.event,
            defaults={'enabled': True}  # Toujours activé si le plugin est actif
        )
        return obj

    def get_success_url(self):
        return reverse('plugins:pretix_sortir:event-settings',
                      kwargs={'organizer': self.request.event.organizer.slug,
                             'event': self.request.event.slug})

    def post(self, request, *args, **kwargs):
        """Gère directement les checkboxes des tarifs sans formulaire Django."""
        self.object = self.get_object()

        # Gère les checkboxes des tarifs
        requires_sortir_ids = request.POST.getlist('requires_sortir')

        # Supprime toutes les configs existantes
        SortirItemConfig.objects.filter(event=self.request.event).delete()
        
        # Crée les nouvelles configs pour les tarifs cochés
        for item_id_str in requires_sortir_ids:
            if '_' in item_id_str:
                item_id, variation_id = item_id_str.split('_')
                item_id = int(item_id)
                variation_id = int(variation_id)
            else:
                item_id = int(item_id_str)
                variation_id = None

            from pretix.base.models import Item, ItemVariation
            item = Item.objects.get(pk=item_id, event=self.request.event)
            variation = ItemVariation.objects.get(pk=variation_id, item=item) if variation_id else None

            SortirItemConfig.objects.create(
                event=self.request.event,
                item=item,
                variation=variation,
                requires_sortir=True
            )
        
        messages.success(request, _('Paramètres Sortir! mis à jour.'))
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Vérifie si l'organisateur a configuré l'API
        try:
            org_settings = SortirOrganizerSettings.objects.get(
                organizer=self.request.event.organizer
            )
            context['organizer_configured'] = org_settings.api_enabled
        except SortirOrganizerSettings.DoesNotExist:
            context['organizer_configured'] = False

        # Récupère tous les items de l'événement
        items_data = []
        for item in self.request.event.items.all():
            if not item.has_variations:
                config = SortirItemConfig.objects.filter(
                    event=self.request.event,
                    item=item,
                    variation__isnull=True
                ).first()

                items_data.append({
                    'item': item,
                    'variation': None,
                    'requires_sortir': config.requires_sortir if config else False,
                    'name': item.name,
                    'price': item.default_price,
                    'id_str': str(item.id)
                })

            for variation in item.variations.all():
                var_config = SortirItemConfig.objects.filter(
                    event=self.request.event,
                    item=item,
                    variation=variation
                ).first()

                items_data.append({
                    'item': item,
                    'variation': variation,
                    'requires_sortir': var_config.requires_sortir if var_config else False,
                    'name': f"{item.name} - {variation.value}",
                    'price': variation.default_price or item.default_price,
                    'id_str': f"{item.id}_{variation.id}"
                })

        context['items_data'] = items_data
        return context


class SortirUsageListView(EventSettingsViewMixin, ListView):
    """Vue pour l'historique des utilisations."""
    model = SortirUsage
    template_name = 'pretix_sortir/usage_list.html'
    context_object_name = 'usages'
    paginate_by = 50
    permission = 'can_view_orders'

    def get_queryset(self):
        return SortirUsage.objects.filter(
            event=self.request.event
        ).select_related('order', 'item', 'variation').order_by('-created_at')


from django.views import View

@method_decorator(csrf_exempt, name='dispatch')
class SortirCardValidationView(View):
    """Vue AJAX pour valider un numéro de carte Sortir en temps réel"""

    def _get_client_ip(self, request):
        """
        Récupère l'adresse IP réelle du client (Sécurité PHASE 2).
        Tient compte des proxies (X-Forwarded-For, X-Real-IP).
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Prend la première IP (client réel)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')
        return ip

    def dispatch(self, request, *args, **kwargs):
        """Setup l'event et l'organizer dans le contexte"""
        from pretix.base.models import Event, Organizer
        from django_scopes import scopes_disabled

        # Récupère l'organisateur et l'événement
        organizer_slug = kwargs.get('organizer')
        event_slug = kwargs.get('event')

        try:
            # Désactive temporairement les scopes pour les requêtes
            with scopes_disabled():
                organizer = Organizer.objects.get(slug=organizer_slug)
                event = Event.objects.get(slug=event_slug, organizer=organizer)

            # Ajoute au request pour simuler le middleware Pretix
            request.event = event
            request.organizer = organizer

        except (Organizer.DoesNotExist, Event.DoesNotExist):
            from django.http import JsonResponse
            return JsonResponse({
                'valid': False,
                'error': 'Événement non trouvé'
            }, status=404)

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Valide un numéro de carte via AJAX"""
        import json
        from django.http import JsonResponse
        from .api_client import SortirAPIClient
        from django_scopes import scopes_disabled
        from django.core.cache import cache

        # Rate limiting (Sécurité PHASE 2 - Point 6)
        # Limite : 10 tentatives par IP toutes les 5 minutes
        ip_address = self._get_client_ip(request)
        rate_limit_key = f'sortir_rate_limit_{ip_address}'
        attempts = cache.get(rate_limit_key, 0)

        if attempts >= 10:
            logger.warning(f"[Sortir] Rate limit dépassé pour IP {ip_address}")

            # Audit trail (PHASE 2 - Point 9)
            from .models import SortirAuditLog
            SortirAuditLog.log(
                action='rate_limit_triggered',
                severity='warning',
                event=request.event,
                organizer=request.organizer,
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                message=f'Rate limit dépassé : {attempts} tentatives en 5 minutes'
            )

            return JsonResponse({
                'valid': False,
                'error': 'Trop de tentatives. Veuillez réessayer dans 5 minutes.'
            }, status=429)

        # Incrémente le compteur (expire après 5 minutes)
        cache.set(rate_limit_key, attempts + 1, 300)

        try:
            # Récupère le numéro de carte et le session_id
            data = json.loads(request.body)
            card_number = data.get('card_number', '').strip()
            session_id = data.get('session_id', '').strip()  # ID anonyme de session (RGPD-compliant)

            if not card_number:
                return JsonResponse({
                    'valid': False,
                    'error': 'Numéro de carte requis'
                })

            # Nettoie le numéro (seulement chiffres)
            clean_card_number = ''.join(filter(str.isdigit, card_number))

            if len(clean_card_number) < 6:
                return JsonResponse({
                    'valid': False,
                    'error': 'Numéro de carte trop court'
                })

            # Utilise request.event et request.organizer ajoutés dans dispatch()
            event = request.event
            organizer = request.organizer

            # Désactive les scopes pour toutes les requêtes de la base de données
            with scopes_disabled():
                # Vérifie si Sortir est activé pour cet événement
                try:
                    event_settings = SortirEventSettings.objects.get(
                        event=event,
                        enabled=True
                    )
                except SortirEventSettings.DoesNotExist:
                    return JsonResponse({
                        'valid': False,
                        'error': 'Sortir non activé pour cet événement'
                    })

                # Récupère les settings de l'organisateur
                try:
                    org_settings = SortirOrganizerSettings.objects.get(
                        organizer=organizer,
                        api_enabled=True
                    )
                except SortirOrganizerSettings.DoesNotExist:
                    return JsonResponse({
                        'valid': False,
                        'error': 'API Sortir non configurée'
                    })

            # Détermine l'URL selon le mode
            if org_settings.api_mode == 'production':
                api_url = org_settings.api_url_production
            else:
                api_url = org_settings.api_url_test

            # Crée le client API et vérifie l'éligibilité
            api_client = SortirAPIClient(
                api_key=org_settings.api_token,
                api_mode=org_settings.api_mode,
                api_url=api_url
            )

            is_eligible = api_client.verify_eligibility(clean_card_number)

            if is_eligible:
                # VÉRIFICATION ANTI-FRAUDE (PHASE 1 - Point 3)
                # Vérifie que la carte n'est pas déjà utilisée pour cet événement
                from .models import SortirUsage
                from pretix.base.models import Order
                card_hash = SortirUsage.hash_number(clean_card_number, org_settings.salt)

                # NETTOYAGE PRÉALABLE : Supprime les SortirUsage 'pending' trop vieux (>10 min = panier abandonné)
                from datetime import timedelta
                expiry_threshold = timezone.now() - timedelta(minutes=10)

                old_pending_usages = SortirUsage.objects.filter(
                    event=event,
                    sortir_number_hash=card_hash,
                    status='pending',
                    order__isnull=True,  # Pas encore de commande
                    created_at__lt=expiry_threshold
                )

                deleted_count = old_pending_usages.count()
                if deleted_count > 0:
                    old_pending_usages.delete()
                    logger.info(f"[Sortir] Nettoyage : {deleted_count} SortirUsage pending expirés supprimés pour carte ***{clean_card_number[-4:]}")

                # Récupère les usages existants (après nettoyage)
                existing_usages = SortirUsage.objects.filter(
                    event=event,
                    sortir_number_hash=card_hash,
                    status__in=['validated', 'used', 'pending']
                ).select_related('order')

                # Filtre pour ne garder que les usages avec commandes valides
                # IMPORTANT : On ignore les 'pending' de la MÊME SESSION (< 5 min)
                # car c'est la même personne qui corrige son numéro (RGPD-compliant : pas d'IP stockée)
                from datetime import timedelta
                recent_threshold = timezone.now() - timedelta(minutes=5)

                valid_existing_usage = None
                for usage in existing_usages:
                    # Si pas de commande associée, c'est un usage 'pending' récent (< 10 min)
                    if not usage.order:
                        # NOUVEAU : Ignore les pending de la MÊME SESSION récents (< 5 min)
                        # Si session_id match ET récent : c'est la même personne qui corrige
                        if session_id and usage.session_id == session_id and usage.created_at >= recent_threshold:
                            age_seconds = (timezone.now() - usage.created_at).total_seconds()
                            logger.info(f"[Sortir] Carte ***{clean_card_number[-4:]} : pending ignoré (même session, créé il y a {age_seconds:.0f}s)")
                            continue
                        # Sinon : pending d'une autre session ou trop vieux → on bloque
                        else:
                            valid_existing_usage = usage
                            break
                    # Si commande associée, vérifie son statut
                    elif usage.order.status not in [Order.STATUS_CANCELED, Order.STATUS_EXPIRED]:
                        # Commande valide (pending ou paid)
                        valid_existing_usage = usage
                        break

                if valid_existing_usage:
                    logger.warning(f"[Sortir] ANTI-FRAUDE : Carte ***{clean_card_number[-4:]} déjà utilisée pour l'événement {event.slug}")

                    # Audit trail tentative fraude
                    from .models import SortirAuditLog
                    SortirAuditLog.log(
                        action='card_validation_failed',
                        severity='critical',
                        event=event,
                        organizer=organizer,
                        card_number=clean_card_number,
                        salt=org_settings.salt,
                        ip_address=ip_address,
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        message=f'Tentative de réutilisation de carte déjà utilisée (Usage ID: {valid_existing_usage.id})'
                    )

                    return JsonResponse({
                        'valid': False,
                        'error': 'Cette carte a déjà été utilisée pour cet événement'
                    })

                # AVANT de créer un nouveau pending, supprime les anciens pending de cette session pour cette carte
                # Cela évite les violations de contrainte unique
                if session_id:
                    old_pending_same_session = SortirUsage.objects.filter(
                        event=event,
                        sortir_number_hash=card_hash,
                        status='pending',
                        order__isnull=True,
                        session_id=session_id
                    )
                    deleted = old_pending_same_session.count()
                    if deleted > 0:
                        old_pending_same_session.delete()
                        logger.info(f"[Sortir] Supprimé {deleted} ancien(s) pending de cette session pour carte ***{clean_card_number[-4:]}")

                # Crée un SortirUsage en statut 'pending' (sera validé à order_placed)
                usage = SortirUsage.objects.create(
                    event=event,
                    sortir_number_hash=card_hash,
                    sortir_number_suffix=clean_card_number[-4:],
                    status='pending',
                    validated_at=timezone.now(),
                    session_id=session_id  # Stocke le session_id pour ignorer les corrections (RGPD-compliant)
                )

                logger.info(f"[Sortir] SortirUsage créé (ID: {usage.id}) pour carte ***{clean_card_number[-4:]}")

                # Sauvegarde sécurisée en session pour le checkout
                session_key = f'sortir_card_validated_{clean_card_number}'
                request.session[session_key] = {
                    'card_number': clean_card_number,
                    'validated_at': str(timezone.now()),
                    'organizer': organizer.slug,
                    'event': event.slug,
                    'usage_id': usage.id  # Lien vers le SortirUsage
                }
                request.session.save()

                logger.info(f"[Sortir] Carte {clean_card_number} validée et sauvée en session")

                # Audit trail succès (PHASE 2 - Point 9)
                from .models import SortirAuditLog
                SortirAuditLog.log(
                    action='card_validation_success',
                    severity='info',
                    event=event,
                    organizer=organizer,
                    card_number=clean_card_number,
                    salt=org_settings.salt,
                    ip_address=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    message=f'Validation carte réussie via AJAX (Usage ID: {usage.id})'
                )

                return JsonResponse({
                    'valid': True,
                    'message': 'Carte valide et éligible'
                })
            else:
                # Audit trail échec (PHASE 2 - Point 9)
                from .models import SortirAuditLog
                SortirAuditLog.log(
                    action='card_validation_failed',
                    severity='warning',
                    event=event,
                    organizer=organizer,
                    card_number=clean_card_number,
                    salt=org_settings.salt,
                    ip_address=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    message='Carte non éligible, expirée ou inconnue'
                )

                return JsonResponse({
                    'valid': False,
                    'error': 'Carte non éligible, expirée ou inconnue'
                })

        except json.JSONDecodeError:
            return JsonResponse({
                'valid': False,
                'error': 'Format de données invalide'
            })

        except Exception as e:
            logger.error(f"Erreur lors de la validation AJAX: {e}")
            return JsonResponse({
                'valid': False,
                'error': 'Erreur de validation'
            })


class SortirCleanupSessionView(View):
    """
    Vue pour nettoyer les SortirUsage pending d'une session
    Appelée quand on change le panier pour éviter les conflits
    """
    def post(self, request, *args, **kwargs):
        try:
            # Récupère les paramètres
            organizer = get_object_or_404(Organizer, slug=kwargs['organizer'])
            event = get_object_or_404(Event, organizer=organizer, slug=kwargs['event'])

            # Parse le JSON du body
            body_data = json.loads(request.body.decode('utf-8'))
            session_id = body_data.get('session_id')
            card_number = body_data.get('card_number')  # Optionnel : nettoyer une carte spécifique

            if not session_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Session ID requis'
                })

            # IP du client
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or \
                        request.META.get('REMOTE_ADDR', '')

            # Nettoie les SortirUsage pending pour cette session
            # On identifie par IP + timeframe (5 dernières minutes)
            from datetime import timedelta
            recent_threshold = timezone.now() - timedelta(minutes=5)

            # Si un card_number spécifique est fourni, on ne nettoie que celui-là
            # Sinon on nettoie TOUS les pending de cette IP
            filter_kwargs = {
                'event': event,
                'status': 'pending',
                'order__isnull': True,
                'ip_address': ip_address,
                'created_at__gte': recent_threshold
            }

            if card_number:
                filter_kwargs['card_number'] = card_number

            deleted_count = SortirUsage.objects.filter(**filter_kwargs).delete()[0]  # delete() renvoie (count, dict)

            if card_number:
                logger.info(f"[Sortir] Nettoyage session {session_id}: carte {card_number} supprimée pour IP {ip_address}")
            else:
                logger.info(f"[Sortir] Nettoyage session {session_id}: {deleted_count} SortirUsage pending supprimés pour IP {ip_address}")

            # Nettoie aussi les vieux pending (>10 minutes) toutes IPs confondues
            old_threshold = timezone.now() - timedelta(minutes=10)
            old_deleted = SortirUsage.objects.filter(
                event=event,
                status='pending',
                order__isnull=True,
                created_at__lt=old_threshold
            ).delete()[0]

            if old_deleted > 0:
                logger.info(f"[Sortir] Nettoyage global: {old_deleted} vieux SortirUsage pending supprimés")

            return JsonResponse({
                'success': True,
                'deleted': deleted_count,
                'old_deleted': old_deleted
            })

        except Exception as e:
            logger.error(f"Erreur nettoyage session: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
