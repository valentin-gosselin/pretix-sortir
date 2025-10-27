"""
Client API APRAS pour la vérification des droits Sortir!

Ce module gère la communication avec l'API APRAS pour:
- Vérifier les droits d'une carte KorriGo
- Enregistrer une demande après validation d'une commande
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Tuple, Union
from urllib.parse import urljoin

import requests
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger('pretix.plugins.sortir')


class APRASErrorCode(Enum):
    """Codes d'erreur de l'API APRAS."""
    SUCCESS = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    TIMEOUT = 408
    SERVER_ERROR = 500


@dataclass
class ServiceKey:
    """Clé de service retournée par l'API après validation."""
    key: str
    created_at: datetime
    card_number_suffix: str  # 4 derniers chiffres pour référence


@dataclass
class GrantResponse:
    """Réponse de l'API après enregistrement d'une demande."""
    id: int
    date_demande: datetime
    montant_activite: int
    montant_aide: int
    aide_coupon_sport: int
    aide_autres: int
    aide_additionnelle: int


@dataclass
class InscritInfo:
    """Informations sur le bénéficiaire (si disponibles)."""
    id: int
    nom: str
    prenom: str
    date_naissance: Optional[datetime] = None


class APRASClient:
    """
    Client pour l'API APRAS de vérification des droits Sortir!

    Gère les appels API avec:
    - Retry automatique avec backoff exponentiel
    - Cache des réponses négatives (anti brute-force)
    - Timeout configurable
    - Circuit breaker en cas de panne API
    """

    def __init__(self, base_url: str, token: str, timeout: int = 2):
        """
        Initialise le client API.

        Args:
            base_url: URL de base de l'API (prod ou test)
            token: Token d'authentification fourni par l'APRAS
            timeout: Timeout en secondes pour les appels API
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout

        # Configuration de la session avec retry
        self.session = requests.Session()
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Headers par défaut
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def _get_cache_key(self, card_number: str) -> str:
        """Génère une clé de cache pour un numéro de carte."""
        # Utilise seulement les 4 derniers chiffres pour la clé
        suffix = card_number[-4:] if len(card_number) >= 4 else card_number
        return f"sortir_api_404_{suffix}"

    def _is_circuit_breaker_open(self) -> bool:
        """Vérifie si le circuit breaker est ouvert (API down)."""
        return cache.get('sortir_api_circuit_breaker', False)

    def _open_circuit_breaker(self):
        """Ouvre le circuit breaker pour 5 minutes."""
        cache.set('sortir_api_circuit_breaker', True, 300)
        logger.error("Circuit breaker ouvert - API APRAS indisponible")

    def _close_circuit_breaker(self):
        """Ferme le circuit breaker."""
        cache.delete('sortir_api_circuit_breaker')

    def verify_rights(self, card_number: str) -> Tuple[bool, Union[ServiceKey, str]]:
        """
        Vérifie les droits Sortir! d'une carte KorriGo.

        Args:
            card_number: Numéro de carte à 10 chiffres

        Returns:
            Tuple (succès, ServiceKey ou message d'erreur)
        """
        # Validation format
        if not card_number or not card_number.isdigit() or len(card_number) != 10:
            return False, _("Numéro de carte invalide (10 chiffres requis)")

        # Vérification circuit breaker
        if self._is_circuit_breaker_open():
            return False, _("Service temporairement indisponible. Veuillez réessayer dans quelques minutes.")

        # Vérification cache anti brute-force
        cache_key = self._get_cache_key(card_number)
        cached_error = cache.get(cache_key)
        if cached_error:
            return False, cached_error

        # Appel API
        url = urljoin(self.base_url, f'/api/partners/{card_number}')

        try:
            logger.info(f"Vérification droits Sortir! pour carte ***{card_number[-4:]}")
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == APRASErrorCode.SUCCESS.value:
                # Succès - droits valides
                self._close_circuit_breaker()

                data = response.json()
                service_key = ServiceKey(
                    key=data.get('cle_service', ''),
                    created_at=datetime.now(),
                    card_number_suffix=card_number[-4:]
                )

                # Extraction des infos inscrit si disponibles
                if 'inscrit' in data:
                    inscrit = InscritInfo(
                        id=data['inscrit'].get('id'),
                        nom=data['inscrit'].get('nom', ''),
                        prenom=data['inscrit'].get('prenom', ''),
                        date_naissance=data['inscrit'].get('date_naissance')
                    )
                    # Stocker temporairement en cache pour pré-remplissage
                    cache.set(f"sortir_inscrit_{card_number[-4:]}", inscrit, 600)

                logger.info(f"Droits valides pour carte ***{card_number[-4:]}")
                return True, service_key

            elif response.status_code == APRASErrorCode.UNAUTHORIZED.value:
                error_msg = _("Token API invalide ou manquant")
                logger.error(f"Erreur auth API: {error_msg}")
                self._open_circuit_breaker()
                return False, error_msg

            elif response.status_code == APRASErrorCode.FORBIDDEN.value:
                error_msg = _("Accès refusé par l'API")
                cache.set(cache_key, error_msg, 300)  # Cache 5 min
                return False, error_msg

            elif response.status_code == APRASErrorCode.NOT_FOUND.value:
                error_msg = _("Numéro de carte inconnu ou droits expirés")
                cache.set(cache_key, error_msg, 300)  # Cache 5 min
                logger.info(f"Carte invalide: ***{card_number[-4:]}")
                return False, error_msg

            else:
                error_msg = _("Erreur lors de la vérification")
                logger.error(f"Code retour inattendu: {response.status_code}")
                return False, error_msg

        except requests.Timeout:
            logger.error("Timeout lors de l'appel API APRAS")
            return False, _("Délai d'attente dépassé. Veuillez réessayer.")

        except requests.ConnectionError:
            logger.error("Erreur de connexion à l'API APRAS")
            self._open_circuit_breaker()
            return False, _("Impossible de contacter le service. Veuillez réessayer plus tard.")

        except Exception as e:
            logger.exception(f"Erreur inattendue: {e}")
            return False, _("Une erreur inattendue s'est produite")

    def post_grant(self, service_key: str, activite_id: Optional[int] = None) -> Tuple[bool, Union[GrantResponse, str]]:
        """
        Enregistre une demande après validation d'une commande.

        Args:
            service_key: Clé de service obtenue lors de la vérification
            activite_id: ID de l'activité (optionnel pour Gosselico)

        Returns:
            Tuple (succès, GrantResponse ou message d'erreur)
        """
        if not service_key:
            return False, _("Clé de service manquante")

        # Vérification circuit breaker
        if self._is_circuit_breaker_open():
            # En cas de circuit breaker ouvert, on met en queue pour retry
            logger.warning("Circuit breaker ouvert - mise en queue de la demande")
            return False, _("Demande mise en attente - sera traitée ultérieurement")

        url = urljoin(self.base_url, '/api/partners/grant')
        payload = {
            'token': service_key
        }

        if activite_id:
            payload['activite'] = activite_id

        try:
            logger.info("Envoi demande grant à l'API APRAS")
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code in [200, 201]:
                self._close_circuit_breaker()
                data = response.json()

                grant = GrantResponse(
                    id=data.get('id'),
                    date_demande=datetime.fromisoformat(data.get('date_demande')),
                    montant_activite=data.get('montant_activite', 0),
                    montant_aide=data.get('montant_aide', 0),
                    aide_coupon_sport=data.get('aide_coupon_sport', 0),
                    aide_autres=data.get('aide_autres', 0),
                    aide_additionnelle=data.get('aide_additionnelle', 0)
                )

                logger.info(f"Demande grant enregistrée avec succès: ID={grant.id}")
                return True, grant

            elif response.status_code == APRASErrorCode.BAD_REQUEST.value:
                return False, _("Paramètres invalides")

            elif response.status_code in [401, 403]:
                self._open_circuit_breaker()
                return False, _("Erreur d'authentification")

            else:
                logger.error(f"Erreur grant: code {response.status_code}")
                return False, _("Erreur lors de l'enregistrement de la demande")

        except requests.Timeout:
            logger.error("Timeout lors du POST grant")
            return False, _("Délai dépassé - demande mise en attente")

        except requests.ConnectionError:
            logger.error("Erreur connexion lors du POST grant")
            self._open_circuit_breaker()
            return False, _("Erreur de connexion - demande mise en attente")

        except Exception as e:
            logger.exception(f"Erreur inattendue grant: {e}")
            return False, _("Erreur inattendue")


def get_inscrit_info(card_suffix: str) -> Optional[InscritInfo]:
    """
    Récupère les infos inscrit depuis le cache si disponibles.

    Args:
        card_suffix: Les 4 derniers chiffres de la carte

    Returns:
        InscritInfo ou None
    """
    return cache.get(f"sortir_inscrit_{card_suffix}")