"""
Modèles de données pour le plugin Sortir! - Version organisateur

Configuration au niveau organisateur pour l'API APRAS
et tracking au niveau événement pour les utilisations.
"""

import hashlib
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from pretix.base.models import Event, Item, ItemVariation, Order, Organizer
from pretix.base.models.base import LoggedModel
from .fields import EncryptedTextField


class SortirOrganizerSettings(LoggedModel):
    """
    Configuration du plugin Sortir! au niveau organisateur.

    Stocke les paramètres de connexion à l'API APRAS communs
    à tous les événements de l'organisateur.
    """

    organizer = models.OneToOneField(
        Organizer,
        on_delete=models.CASCADE,
        related_name='sortir_settings',
        verbose_name=_('Organisateur')
    )

    # Configuration API
    api_enabled = models.BooleanField(
        default=True,  # Toujours activé si le plugin est installé
        verbose_name=_('Activer Sortir!'),
        help_text=_('Automatiquement activé quand le plugin est installé')
    )

    api_mode = models.CharField(
        max_length=20,
        choices=[
            ('production', _('Production')),
            ('test', _('Test'))
        ],
        default='test',
        verbose_name=_('Mode API'),
        help_text=_('Choisir entre l\'environnement de production ou de test')
    )

    api_url_production = models.URLField(
        blank=True,
        default='',
        verbose_name=_('URL API Production'),
        help_text=_('URL de l\'API APRAS en production (fournie par l\'APRAS après validation)')
    )

    api_url_test = models.URLField(
        blank=True,
        default='',
        verbose_name=_('URL API Test'),
        help_text=_('URL de l\'API APRAS de test (fournie par l\'APRAS pour les tests)')
    )

    api_token = EncryptedTextField(
        blank=True,
        verbose_name=_('Token API'),
        help_text=_('Token d\'authentification fourni par l\'APRAS (chiffré au repos)')
    )

    api_timeout = models.IntegerField(
        default=2,
        verbose_name=_('Timeout API (secondes)'),
        help_text=_('Délai maximum d\'attente pour les appels API')
    )

    # Options de comportement globales
    prefill_attendee = models.BooleanField(
        default=True,
        verbose_name=_('Pré-remplir nom/prénom'),
        help_text=_('Pré-remplir les champs attendee si l\'API retourne ces infos')
    )

    release_on_cancel = models.BooleanField(
        default=True,
        verbose_name=_('Libérer à l\'annulation'),
        help_text=_('Libérer les numéros Sortir! lors de l\'annulation d\'une commande')
    )

    # RGPD - Rétention des données (PHASE 3)
    data_retention_days = models.IntegerField(
        default=90,
        verbose_name=_('Durée de conservation (jours)'),
        help_text=_('Durée de conservation des données SortirUsage après la fin de l\'événement (RGPD). Recommandé : 90 jours')
    )

    audit_retention_days = models.IntegerField(
        default=365,
        verbose_name=_('Durée de conservation des logs (jours)'),
        help_text=_('Durée de conservation des logs d\'audit (RGPD). Recommandé : 365 jours pour sécurité')
    )

    # Salt pour le hashage des numéros (partagé entre événements)
    salt = models.CharField(
        max_length=50,
        editable=False
    )

    class Meta:
        verbose_name = _('Configuration Sortir! organisateur')
        verbose_name_plural = _('Configurations Sortir! organisateur')

    def __str__(self):
        return f"Sortir! - {self.organizer.name}"

    def save(self, *args, **kwargs):
        """Génère un salt unique si nécessaire."""
        if not self.salt:
            self.salt = get_random_string(50)
        super().save(*args, **kwargs)

    @property
    def api_base_url(self):
        """Retourne l'URL API active selon le mode."""
        if self.api_mode == 'production':
            return self.api_url_production
        return self.api_url_test


class SortirEventSettings(models.Model):
    """
    Activation et configuration du plugin Sortir! pour un événement spécifique.
    """

    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name='sortir_event_settings',
        verbose_name=_('Événement')
    )

    enabled = models.BooleanField(
        default=True,  # Toujours activé si le plugin est actif pour l'événement
        verbose_name=_('Utiliser Sortir! pour cet événement'),
        help_text=_('Automatiquement activé quand le plugin est activé pour cet événement')
    )

    class Meta:
        verbose_name = _('Activation Sortir! événement')
        verbose_name_plural = _('Activations Sortir! événements')

    def __str__(self):
        return f"Sortir! - {self.event.name}"


class SortirItemConfig(models.Model):
    """
    Configuration Sortir! pour un item ou une variation spécifique.

    Définit simplement si un tarif nécessite la validation Sortir!.
    Le prix est celui défini dans l'item lui-même.
    """

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='sortir_item_configs'
    )

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        verbose_name=_('Produit')
    )

    variation = models.ForeignKey(
        ItemVariation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Variation')
    )

    # Configuration simple : ce tarif nécessite-t-il la vérification Sortir ?
    requires_sortir = models.BooleanField(
        default=True,
        verbose_name=_('Validation Sortir! requise'),
        help_text=_('Cocher pour que ce tarif nécessite une carte Sortir! valide')
    )

    class Meta:
        verbose_name = _('Tarif avec vérification Sortir!')
        verbose_name_plural = _('Tarifs avec vérification Sortir!')
        unique_together = [['event', 'item', 'variation']]

    def __str__(self):
        if self.variation:
            return f"{self.item.name} - {self.variation.value}"
        return f"{self.item.name}"


class SortirUsage(models.Model):
    """
    Enregistrement de l'utilisation d'un numéro de carte Sortir!

    Stocke de manière sécurisée (hash) les numéros utilisés pour éviter
    les doublons et permettre le suivi.
    """

    STATUS_CHOICES = [
        ('pending', _('En attente')),
        ('validated', _('Validé')),
        ('used', _('Utilisé')),
        ('cancelled', _('Annulé')),
        ('expired', _('Expiré')),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        verbose_name=_('Événement')
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Commande')
    )

    # Numéro hashé et suffixe pour support
    sortir_number_hash = models.CharField(
        max_length=64,
        db_index=True,
        verbose_name=_('Hash du numéro')
    )

    sortir_number_suffix = models.CharField(
        max_length=4,
        blank=True,
        verbose_name=_('4 derniers chiffres'),
        help_text=_('Pour faciliter le support client')
    )

    # Clé de service chiffrée retournée par l'API
    service_key = models.TextField(
        blank=True,
        verbose_name=_('Clé de service')
    )

    # Tracking
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        null=True,
        verbose_name=_('Produit')
    )

    variation = models.ForeignKey(
        ItemVariation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Variation')
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name=_('Statut')
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date de création')
    )

    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Date de validation')
    )

    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Date d\'utilisation')
    )

    # ID de demande APRAS après POST
    apras_request_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('ID demande APRAS')
    )

    class Meta:
        verbose_name = _('Utilisation Sortir!')
        verbose_name_plural = _('Utilisations Sortir!')
        indexes = [
            models.Index(fields=['event', 'sortir_number_hash']),
            models.Index(fields=['event', 'status']),
            models.Index(fields=['order', 'status']),
        ]
        # Contrainte d'unicité anti-fraude (Sécurité PHASE 1 - Point 3)
        # Empêche qu'une même carte hashée soit utilisée plusieurs fois pour le même événement
        # sauf si elle a été annulée (permettant la réutilisation)
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'sortir_number_hash'],
                condition=models.Q(status__in=['validated', 'used', 'pending']),
                name='unique_card_per_event_active',
                violation_error_message=_('Cette carte a déjà été utilisée pour cet événement')
            )
        ]

    def __str__(self):
        return f"Sortir! ***{self.sortir_number_suffix} - {self.get_status_display()}"

    @staticmethod
    def hash_number(number: str, salt: str) -> str:
        """
        Génère un hash SHA-256 salé du numéro de carte.

        Args:
            number: Le numéro de carte à hasher
            salt: Le salt unique de l'organisateur

        Returns:
            Le hash hexadécimal du numéro
        """
        salted = f"{salt}{number}".encode('utf-8')
        return hashlib.sha256(salted).hexdigest()

    @classmethod
    def is_number_used(cls, event: Event, number: str, salt: str,
                      exclude_order: Order = None) -> bool:
        """
        Vérifie si un numéro est déjà utilisé pour cet événement.

        Args:
            event: L'événement concerné
            number: Le numéro de carte à vérifier
            salt: Le salt de l'organisateur
            exclude_order: Commande à exclure de la vérification

        Returns:
            True si le numéro est déjà utilisé
        """
        hashed = cls.hash_number(number, salt)

        queryset = cls.objects.filter(
            event=event,
            sortir_number_hash=hashed,
            status__in=['validated', 'used', 'pending']
        )

        if exclude_order:
            queryset = queryset.exclude(order=exclude_order)

        return queryset.exists()


class SortirAuditLog(models.Model):
    """
    Audit trail sécurisé pour toutes les actions critiques (Sécurité PHASE 2 - Point 9).

    Enregistre :
    - Validations de cartes
    - Tentatives échouées
    - Modifications de configuration
    - Rate limiting triggers
    - Revalidations à order_placed
    """

    ACTION_CHOICES = [
        ('card_validation_success', _('Validation carte réussie')),
        ('card_validation_failed', _('Validation carte échouée')),
        ('card_revalidation_success', _('Revalidation réussie (order_placed)')),
        ('card_revalidation_failed', _('Revalidation échouée (order_placed)')),
        ('rate_limit_triggered', _('Rate limit déclenché')),
        ('config_changed', _('Configuration modifiée')),
        ('usage_recorded', _('Utilisation enregistrée')),
        ('usage_cancelled', _('Utilisation annulée')),
    ]

    SEVERITY_CHOICES = [
        ('info', _('Information')),
        ('warning', _('Avertissement')),
        ('error', _('Erreur')),
        ('critical', _('Critique')),
    ]

    # Quand et qui
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_('Date/Heure')
    )

    # Contexte
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Événement')
    )

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Organisateur')
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Commande')
    )

    # Action
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True,
        verbose_name=_('Action')
    )

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='info',
        db_index=True,
        verbose_name=_('Gravité')
    )

    # Données (ne stocke JAMAIS de numéros en clair)
    card_hash = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_('Hash de carte')
    )

    card_suffix = models.CharField(
        max_length=4,
        blank=True,
        verbose_name=_('Suffixe carte (4 derniers chiffres)')
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('Adresse IP')
    )

    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('User Agent')
    )

    # Détails additionnels (JSON)
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Détails')
    )

    # Message
    message = models.TextField(
        blank=True,
        verbose_name=_('Message')
    )

    class Meta:
        verbose_name = _('Audit Sortir!')
        verbose_name_plural = _('Audits Sortir!')
        indexes = [
            models.Index(fields=['timestamp', 'severity']),
            models.Index(fields=['event', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['card_hash']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.get_action_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

    @classmethod
    def log(cls, action, severity='info', event=None, organizer=None, order=None,
            card_number=None, salt=None, ip_address=None, user_agent=None,
            message='', **extra_details):
        """
        Helper pour créer un log d'audit facilement.

        Args:
            action: Type d'action (voir ACTION_CHOICES)
            severity: Gravité (info, warning, error, critical)
            event: Événement concerné (optionnel)
            organizer: Organisateur concerné (optionnel)
            order: Commande concernée (optionnel)
            card_number: Numéro de carte (sera hashé, jamais stocké en clair)
            salt: Salt pour hasher la carte
            ip_address: IP du client
            user_agent: User agent du client
            message: Message descriptif
            **extra_details: Détails additionnels (seront en JSON)
        """
        card_hash = ''
        card_suffix = ''

        if card_number and salt:
            card_hash = SortirUsage.hash_number(card_number, salt)
            card_suffix = card_number[-4:] if len(card_number) >= 4 else ''

        return cls.objects.create(
            action=action,
            severity=severity,
            event=event,
            organizer=organizer,
            order=order,
            card_hash=card_hash,
            card_suffix=card_suffix,
            ip_address=ip_address,
            user_agent=user_agent,
            message=message,
            details=extra_details
        )