"""
Signaux pour le plugin Sortir! - Version simplifiée et fonctionnelle
"""

import json
import logging
from django.core.exceptions import ValidationError
from django.dispatch import receiver
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from pretix.base.signals import validate_cart_addons, order_placed, order_approved, order_paid, validate_cart
from pretix.presale.signals import html_head, item_description

from .models import SortirItemConfig, SortirEventSettings

logger = logging.getLogger('pretix.plugins.sortir')


@receiver(validate_cart, dispatch_uid='sortir_validate_cart_main')
def check_sortir_required(sender, positions, **kwargs):
    """
    Vérifie que les numéros de carte Sortir sont fournis et validés pour les positions requises
    SÉCURITÉ CRITIQUE : Validation côté serveur obligatoire

    Note: La validation AJAX a déjà vérifié la carte auprès de l'API APRAS.
    Ce signal vérifie juste que la validation est présente en meta_info.
    """
    from django_scopes import scopes_disabled
    from pretix.base.services.cart import CartError

    logger.info("[Sortir] Validation du panier - vérification sécurisée")

    with scopes_disabled():
        for position in positions:
            try:
                # Vérifie si cet item nécessite Sortir
                config = SortirItemConfig.objects.get(
                    event=sender,
                    item=position.item,
                    variation=position.variation,
                    requires_sortir=True
                )

                logger.info(f"[Sortir] Item {position.item.name} nécessite validation Sortir")

                # Parse meta_info si nécessaire (peut être une string JSON)
                meta_info = position.meta_info
                if isinstance(meta_info, str):
                    try:
                        meta_info = json.loads(meta_info)
                    except (json.JSONDecodeError, TypeError):
                        meta_info = {}
                elif not meta_info:
                    meta_info = {}

                # Vérifie que la position a les métadonnées de validation
                # Ces métadonnées sont ajoutées par le JavaScript lors de la validation AJAX
                if not meta_info.get('sortir_validated'):
                    logger.warning(f"[Sortir] Position {position.item.name} sans validation Sortir dans meta_info")
                    # On laisse passer car la validation sera re-vérifiée à order_placed
                    # Ceci permet au checkout de fonctionner même si le meta_info n'est pas encore set
                    continue

                card_number = meta_info.get('sortir_card_number')
                if card_number:
                    logger.info(f"[Sortir] Carte ***{card_number[-4:]} déjà validée pour {position.item.name}")
                else:
                    logger.warning(f"[Sortir] Pas de numéro de carte dans meta_info pour {position.item.name}")

            except SortirItemConfig.DoesNotExist:
                # Pas de configuration Sortir pour cet item
                continue


@receiver(html_head, dispatch_uid='sortir_html_head')
def add_sortir_html_head(sender, request=None, **kwargs):
    """Ajoute le CSS et JavaScript pour Sortir! dans le <head>"""

    # Vérifie si Sortir est activé pour cet événement
    if not hasattr(request, 'event'):
        return ""

    try:
        event_settings = SortirEventSettings.objects.get(
            event=request.event,
            enabled=True
        )
    except SortirEventSettings.DoesNotExist:
        return ""

    # Récupère les items qui nécessitent Sortir
    sortir_items = {}
    configs = SortirItemConfig.objects.filter(
        event=request.event,
        requires_sortir=True
    ).select_related('item', 'variation')

    for config in configs:
        item_key = f"{config.item.id}_{config.variation.id if config.variation else 'none'}"
        sortir_items[item_key] = {
            'item_id': config.item.id,
            'variation_id': config.variation.id if config.variation else None,
            'name': str(config.item.name) + (f" - {config.variation.value}" if config.variation else "")
        }

    from django.templatetags.static import static

    return mark_safe(f"""
<link rel="stylesheet" type="text/css" href="{static('pretix_sortir/sortir.css')}">
<script src="{static('pretix_sortir/sortir.js')}" data-sortir-config='{json.dumps(sortir_items)}'></script>
""")


@receiver(item_description, dispatch_uid='sortir_item_description')
def add_sortir_item_description(sender, item=None, variation=None, **kwargs):
    """Ajoute une indication dans la description de l'item s'il nécessite Sortir"""

    logger.info(f"Signal item_description reçu pour {item.name}")

    # Vérifie si Sortir est activé pour cet événement
    try:
        event_settings = SortirEventSettings.objects.get(
            event=sender,
            enabled=True
        )
    except SortirEventSettings.DoesNotExist:
        return ""

    # Vérifie si cet item nécessite Sortir
    config = SortirItemConfig.objects.filter(
        event=sender,
        item=item,
        variation=variation,
        requires_sortir=True
    ).first()

    if config:
        logger.info(f"Item {item.name} nécessite Sortir")
        return mark_safe("""
<div style="background-color: #e3f2fd; padding: 10px; margin-top: 10px; border-radius: 4px; border-left: 4px solid #2196f3;">
    Une carte Sortir! valide sera requise lors de la commande.
</div>""")

    return ""


@receiver(order_placed, dispatch_uid='sortir_order_placed_final_check')
@receiver(order_approved, dispatch_uid='sortir_order_approved_final_check')
def final_sortir_verification(sender, order, **kwargs):
    """
    VÉRIFICATION FINALE : Contrôle ultime avant finalisation de commande (Sécurité PHASE 2 - Point 8)

    Déclenché sur order_placed (commande créée) ET order_approved (commande approuvée/en attente paiement)

    1. S'assure qu'aucun item Sortir n'a été ajouté sans validation
    2. Re-valide la carte auprès de l'API APRAS pour détecter expiration/révocation
    3. Enregistre l'utilisation en base pour tracking
    """
    from django.core.exceptions import ValidationError
    from django_scopes import scopes_disabled
    from .api import APRASClient
    from .models import SortirOrganizerSettings, SortirUsage

    logger.info(f"[Sortir] Vérification finale commande {order.code}")

    # Évite les doubles exécutions : vérifie si des SortirUsage sont déjà liés à cette commande
    existing_usages = SortirUsage.objects.filter(order=order).count()
    if existing_usages > 0:
        logger.info(f"[Sortir] Commande {order.code} déjà traitée ({existing_usages} usages), skip")
        return

    with scopes_disabled():
        # Récupère les settings de l'organisateur
        try:
            org_settings = SortirOrganizerSettings.objects.get(
                organizer=order.event.organizer,
                api_enabled=True
            )
        except SortirOrganizerSettings.DoesNotExist:
            logger.error(f"[Sortir] Pas de configuration API pour l'organisateur {order.event.organizer}")
            # Continue sans bloquer si pas de config (ne devrait pas arriver)
            return

        # Client API pour revalidation
        api_client = APRASClient(
            base_url=org_settings.api_url,
            token=org_settings.api_token,
            timeout=org_settings.api_timeout
        )

        # Compte combien de positions nécessitent Sortir
        sortir_positions_count = 0
        for position in order.positions.all():
            try:
                SortirItemConfig.objects.get(
                    event=order.event,
                    item=position.item,
                    variation=position.variation,
                    requires_sortir=True
                )
                sortir_positions_count += 1
            except SortirItemConfig.DoesNotExist:
                pass

        # Récupère les N plus récents SortirUsage pending (créés dans les 5 dernières minutes)
        from datetime import timedelta
        recent_threshold = timezone.now() - timedelta(minutes=5)

        recent_pending_usages = SortirUsage.objects.filter(
            event=order.event,
            status='pending',
            order__isnull=True,
            created_at__gte=recent_threshold  # Seulement les récents
        ).order_by('-created_at')[:sortir_positions_count]  # Les N plus récents

        if len(recent_pending_usages) < sortir_positions_count:
            logger.error(f"[Sortir] Pas assez de SortirUsage récents : besoin de {sortir_positions_count}, trouvé {len(recent_pending_usages)}")
            raise ValidationError(_(f"Erreur : Validations Sortir manquantes. Veuillez rafraîchir et réessayer."))

        # Convertit en liste pour itération facile
        pending_usages_list = list(recent_pending_usages)
        usage_index = 0

        # Liste des IDs de SortirUsage déjà traités dans cette commande
        processed_usage_ids = []

        for position in order.positions.all():
            try:
                # Vérifie si cet item nécessite Sortir
                config = SortirItemConfig.objects.get(
                    event=order.event,
                    item=position.item,
                    variation=position.variation,
                    requires_sortir=True
                )

                # Parse meta_info si nécessaire (peut être une string JSON)
                meta_info = position.meta_info
                if isinstance(meta_info, str):
                    try:
                        meta_info = json.loads(meta_info)
                    except (json.JSONDecodeError, TypeError):
                        meta_info = {}
                elif not meta_info:
                    meta_info = {}

                # Prend le prochain SortirUsage dans la liste des récents
                if usage_index >= len(pending_usages_list):
                    logger.error(f"[Sortir] Index hors limites : {usage_index} >= {len(pending_usages_list)}")
                    raise ValidationError(_(f"Erreur : Pas assez de validations Sortir"))

                pending_usage = pending_usages_list[usage_index]
                usage_index += 1

                if not pending_usage:
                    logger.error(f"[Sortir] SÉCURITÉ : Aucun SortirUsage pending trouvé pour position {position.pk} commande {order.code}")
                    raise ValidationError(_(f"Erreur critique : Aucune validation Sortir trouvée pour {position.item.name}"))

                # Met à jour le SortirUsage avec la commande
                pending_usage.order = order
                pending_usage.item = position.item
                pending_usage.variation = position.variation
                pending_usage.status = 'validated'
                pending_usage.validated_at = timezone.now()
                pending_usage.save()

                # Marque cet usage comme traité
                processed_usage_ids.append(pending_usage.id)

                logger.info(f"[Sortir] SortirUsage {pending_usage.id} lié à la commande {order.code}")

                # Ajoute un commentaire interne à la commande pour le support (RGPD)
                # Ne pas écraser les commentaires existants, ajouter une ligne
                sortir_comment = f"[Sortir!] Carte validée : ***{pending_usage.sortir_number_suffix}"
                if order.comment:
                    # Il y a déjà des commentaires, ajoute une nouvelle ligne
                    if sortir_comment not in order.comment:
                        order.comment = f"{order.comment}\n{sortir_comment}"
                        order.save(update_fields=['comment'])
                else:
                    # Pas de commentaire existant
                    order.comment = sortir_comment
                    order.save(update_fields=['comment'])

                logger.info(f"[Sortir] Commentaire ajouté à la commande {order.code} : ***{pending_usage.sortir_number_suffix}")

                # Audit trail enregistrement utilisation (PHASE 2 - Point 9)
                from .models import SortirAuditLog
                SortirAuditLog.log(
                    action='usage_recorded',
                    severity='info',
                    event=order.event,
                    organizer=order.event.organizer,
                    order=order,
                    message=f'Utilisation finalisée (ID: {pending_usage.id}) pour commande {order.code}'
                )

                logger.info(f"[Sortir] Position {position.pk} validée pour commande {order.code}")

            except SortirItemConfig.DoesNotExist:
                # Pas de config Sortir pour cet item
                continue


@receiver(order_paid, dispatch_uid='sortir_order_paid_grant')
def order_paid_handler(sender, **kwargs):
    """
    Handler appelé lorsqu'une commande est payée (order_paid signal).

    Envoie les appels POST /api/partners/grant à l'API APRAS pour chaque carte validée.
    C'est à ce moment que l'APRAS enregistre la vente pour sa traçabilité.

    IMPORTANT : Ce n'est PAS dans order_placed qu'on fait le grant, mais dans order_paid,
    car l'APRAS doit être notifié uniquement pour les paiements confirmés.
    """
    from django_scopes import scopes_disabled
    from .api import APRASClient
    from .models import SortirOrganizerSettings, SortirUsage

    order = kwargs['order']
    logger.info(f"[Sortir] order_paid_handler appelé pour commande {order.code}")

    with scopes_disabled():
        # Récupère tous les SortirUsage de cette commande avec status='validated'
        usages = SortirUsage.objects.filter(
            order=order,
            status='validated'
        ).select_related('event', 'order')

        if not usages.exists():
            logger.info(f"[Sortir] Aucun SortirUsage à notifier pour commande {order.code}")
            return

        # Récupère les settings de l'organisateur
        try:
            org_settings = SortirOrganizerSettings.objects.get(
                organizer=order.event.organizer,
                api_enabled=True
            )
        except SortirOrganizerSettings.DoesNotExist:
            logger.error(f"[Sortir] Pas de configuration API pour l'organisateur {order.event.organizer}")
            return

        # Crée le client API
        api_client = APRASClient(
            base_url=org_settings.api_url,
            token=org_settings.api_token,
            timeout=org_settings.api_timeout
        )

        # Pour chaque usage, envoie le grant à l'APRAS
        for usage in usages:
            if not usage.service_key:
                logger.error(f"[Sortir] SortirUsage {usage.id} sans service_key - impossible d'envoyer le grant")

                # Audit trail erreur
                from .models import SortirAuditLog
                SortirAuditLog.log(
                    action='grant_failed',
                    severity='error',
                    event=order.event,
                    organizer=order.event.organizer,
                    order=order,
                    message=f'service_key manquant pour SortirUsage {usage.id}'
                )
                continue

            # Appel POST /api/partners/grant
            success, result = api_client.post_grant(service_key=usage.service_key)

            if success:
                # Grant réussi - stocke l'ID de la demande APRAS
                usage.apras_request_id = str(result.id)
                usage.status = 'used'  # Marque comme utilisé
                usage.save(update_fields=['apras_request_id', 'status'])

                logger.info(f"[Sortir] Grant envoyé avec succès pour SortirUsage {usage.id} - APRAS request_id: {result.id}")

                # Audit trail succès
                from .models import SortirAuditLog
                SortirAuditLog.log(
                    action='grant_success',
                    severity='info',
                    event=order.event,
                    organizer=order.event.organizer,
                    order=order,
                    message=f'Grant envoyé avec succès (APRAS request_id: {result.id}, SortirUsage: {usage.id})'
                )
            else:
                # Grant échoué - garde en status='validated' pour retry ultérieur
                error_message = str(result) if result else "Erreur inconnue"
                logger.error(f"[Sortir] Échec grant pour SortirUsage {usage.id} : {error_message}")

                # Audit trail échec
                from .models import SortirAuditLog
                SortirAuditLog.log(
                    action='grant_failed',
                    severity='error',
                    event=order.event,
                    organizer=order.event.organizer,
                    order=order,
                    message=f'Échec grant pour SortirUsage {usage.id} : {error_message}'
                )

                # TODO: Implémenter un système de retry automatique pour les grants échoués
                # Pour l'instant, l'usage reste en status='validated' pour retry manuel

    logger.info(f"[Sortir] Validation finale OK pour commande {order.code}")