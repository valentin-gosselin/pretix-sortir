"""
Formulaires pour la configuration du plugin Sortir! au niveau organisateur
"""

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from pretix.base.forms import SettingsForm
from pretix.base.models import Item, ItemVariation

from .models import SortirItemConfig, SortirOrganizerSettings, SortirEventSettings

# Liste des domaines autorisés pour l'API
# Configuration à adapter selon votre environnement
ALLOWED_APRAS_DOMAINS = []


class SortirOrganizerSettingsForm(forms.ModelForm):
    """
    Formulaire de configuration du plugin Sortir! au niveau organisateur.
    """

    class Meta:
        model = SortirOrganizerSettings
        fields = [
            'api_url',
            'api_token',
            'api_timeout',
            'prefill_attendee',
            'release_on_cancel',
            'data_retention_days',
            'audit_retention_days'
        ]
        widgets = {
            'api_url': forms.URLInput(attrs={
                'placeholder': _("Ex: https://api.sortir.example.com"),
                'class': 'form-control'
            }),
            'api_token': forms.TextInput(attrs={
                'placeholder': _("Token fourni par l'APRAS"),
                'autocomplete': 'off',
                'class': 'form-control'
            }),
            'api_timeout': forms.NumberInput(attrs={
                'min': 1,
                'max': 10,
                'class': 'form-control'
            })
        }
        help_texts = {
            'api_url': _("URL de l'API APRAS (test ou production)"),
            'api_token': _("Token d'authentification fourni par l'APRAS"),
            'api_timeout': _("Temps d'attente maximal pour la vérification API (recommandé: 2 secondes)"),
            'prefill_attendee': _("Remplit automatiquement le nom du participant si disponible"),
            'release_on_cancel': _("Permet de réutiliser un numéro après annulation d'une commande")
        }

    def clean_api_url(self):
        """
        Valide l'URL de l'API (Sécurité PHASE 1 - Points 4 & 5).

        - En production (DEBUG=False), seules les URLs HTTPS sont acceptées
        - Seuls les domaines APRAS whitelistés sont autorisés
        """
        url = self.cleaned_data.get('api_url', '').strip()

        if not url:
            return url

        # Validation HTTPS obligatoire en production
        if not settings.DEBUG and not url.startswith('https://'):
            raise ValidationError(
                _("En production, seules les URLs HTTPS sont autorisées pour des raisons de sécurité. "
                  "L'URL doit commencer par https://")
            )

        # Validation du domaine (whitelist APRAS)
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Retire le port si présent (ex: example.com:443 -> example.com)
        if ':' in domain:
            domain = domain.split(':')[0]

        # Si une whitelist est configurée, vérifier le domaine
        if ALLOWED_APRAS_DOMAINS and domain not in ALLOWED_APRAS_DOMAINS:
            raise ValidationError(
                _("Domaine non autorisé. Veuillez utiliser un domaine autorisé.")
            )

        return url

    def clean(self):
        """Validation du formulaire."""
        cleaned_data = super().clean()

        # Token toujours requis maintenant que le plugin est activé
        if not cleaned_data.get('api_token'):
            raise ValidationError({
                'api_token': _("Le token API est requis pour utiliser le plugin Sortir!")
            })

        return cleaned_data


class SortirEventSettingsForm(forms.ModelForm):
    """
    Formulaire pour activer/désactiver Sortir! sur un événement.
    """

    class Meta:
        model = SortirEventSettings
        fields = ['enabled']
        widgets = {
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'enabled': _("Activer le tarif Sortir! pour cet événement")
        }
        help_texts = {
            'enabled': _("Permet d'utiliser la vérification des droits Sortir! sur cet événement")
        }


class SortirItemConfigForm(forms.ModelForm):
    """
    Formulaire pour associer un tarif à la vérification Sortir!.
    """

    class Meta:
        model = SortirItemConfig
        fields = ['requires_sortir']
        widgets = {
            'requires_sortir': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'requires_sortir': _("Exiger une carte Sortir! valide pour ce tarif")
        }
        help_texts = {
            'requires_sortir': _(
                "Les acheteurs devront présenter un numéro de carte Sortir! valide pour accéder à ce tarif"
            )
        }

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        self.item = kwargs.pop('item', None)
        self.variation = kwargs.pop('variation', None)
        super().__init__(*args, **kwargs)

    def clean_sortir_price(self):
        """Valide que le prix Sortir est inférieur au prix normal."""
        sortir_price = self.cleaned_data.get('sortir_price')

        if sortir_price is not None and self.item:
            # Récupère le prix normal
            if self.variation:
                normal_price = self.variation.price or self.item.default_price
            else:
                normal_price = self.item.default_price

            if normal_price and sortir_price >= normal_price:
                raise ValidationError(
                    _("Le prix Sortir! doit être inférieur au prix normal (%(price)s €)"),
                    params={'price': normal_price}
                )

        return sortir_price


class SortirCheckoutForm(forms.Form):
    """
    Formulaire pour la saisie des numéros Sortir! lors du checkout.
    """

    def __init__(self, *args, **kwargs):
        self.position_count = kwargs.pop('position_count', 1)
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)

        # Créer un champ pour chaque position
        for i in range(1, self.position_count + 1):
            field_name = f'sortir_number_{i}'
            self.fields[field_name] = forms.CharField(
                label=_("Numéro de carte Sortir! #%(num)d") % {'num': i},
                max_length=10,
                min_length=10,
                required=True,
                widget=forms.TextInput(attrs={
                    'placeholder': _("10 chiffres"),
                    'pattern': r'\d{10}',
                    'inputmode': 'numeric',
                    'class': 'sortir-number-input form-control',
                    'data-position': str(i),
                    'autocomplete': 'off'
                }),
                help_text=_("Saisissez le numéro à 10 chiffres de votre carte KorriGo")
            )

    def clean(self):
        """
        Validation globale: vérifie les doublons dans le formulaire.
        """
        cleaned_data = super().clean()
        numbers = []

        for i in range(1, self.position_count + 1):
            field_name = f'sortir_number_{i}'
            number = cleaned_data.get(field_name)

            if number:
                # Vérifie le format
                if not number.isdigit() or len(number) != 10:
                    self.add_error(
                        field_name,
                        _("Le numéro doit contenir exactement 10 chiffres")
                    )
                    continue

                # Vérifie les doublons dans le formulaire
                if number in numbers:
                    self.add_error(
                        field_name,
                        _("Ce numéro a déjà été saisi pour un autre billet")
                    )
                else:
                    numbers.append(number)

        return cleaned_data


class SortirValidationForm(forms.Form):
    """
    Formulaire pour la validation AJAX d'un numéro Sortir!
    """

    sortir_number = forms.CharField(
        max_length=10,
        min_length=10,
        required=True
    )
    position = forms.IntegerField(
        min_value=1,
        required=True
    )

    def clean_sortir_number(self):
        """Valide le format du numéro."""
        number = self.cleaned_data.get('sortir_number')

        if number and (not number.isdigit() or len(number) != 10):
            raise ValidationError(
                _("Le numéro doit contenir exactement 10 chiffres")
            )

        return number