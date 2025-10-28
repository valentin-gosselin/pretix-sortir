"""
Client API pour l'intégration avec l'API APRAS Sortir!
"""

import hashlib
import requests
import logging
from typing import Optional

logger = logging.getLogger('pretix.plugins.sortir')

# Applique les filtres de redaction des logs (Sécurité PHASE 2 - Point 7)
from .logging_filters import SensitiveDataFilter, SortirSecurityFilter
if not any(isinstance(f, SensitiveDataFilter) for f in logger.filters):
    logger.addFilter(SensitiveDataFilter())
if not any(isinstance(f, SortirSecurityFilter) for f in logger.filters):
    logger.addFilter(SortirSecurityFilter())


class SortirAPIClient:
    """Client pour communiquer avec l'API APRAS"""

    def __init__(self, api_key: str, api_url: str = None):
        self.api_key = api_key

        # Utilise l'URL fournie dans les paramètres
        if api_url:
            self.base_url = api_url.rstrip('/')  # Enlève le / final si présent
        else:
            # Fallback si pas d'URL configurée
            self.base_url = ''
            logger.warning("Aucune URL d'API configurée")

    def hash_card_number(self, card_number: str) -> str:
        """Hash le numéro de carte avec SHA-256 pour le stockage sécurisé"""
        return hashlib.sha256(card_number.encode()).hexdigest()

    def verify_eligibility(self, card_number: str) -> bool:
        """
        Vérifie l'éligibilité d'une carte Sortir!

        Args:
            card_number: Le numéro de carte à vérifier

        Returns:
            True si la carte est éligible, False sinon
        """
        try:
            # Nettoie le numéro de carte
            clean_card_number = ''.join(filter(str.isdigit, card_number))

            if not clean_card_number:
                logger.warning("Numéro de carte vide ou invalide")
                return False

            # Vérification de la configuration
            if not self.base_url:
                logger.error("❌ Aucune URL API configurée - Validation impossible")
                return False

            # Appel API réel APRAS (test ou production selon URL configurée)
            # GET api/partners/[CARD]
            url = f"{self.base_url}/api/partners/{clean_card_number}"

            # Format d'authentification correct trouvé : Authorization avec token direct
            headers = {
                'Authorization': self.api_key,
                'Content-Type': 'application/json'
            }

            logger.info(f"[API APRAS] Appel à {url} - Token: {self.api_key[:10]}...")

            # Envoie la requête GET selon la doc APRAS
            response = requests.get(
                url,
                headers=headers,
                timeout=10
            )

            if response.status_code == 201:
                # Code 201 = carte valide selon la doc APRAS
                # La réponse contient une clé de service
                try:
                    result = response.json()
                    service_key = result.get('clé de service') or result.get('cle_de_service') or result.get('token')
                    if service_key:
                        logger.info(f"Carte éligible au tarif Sortir! Clé reçue: {service_key[:10]}...")
                        return True
                    else:
                        logger.warning("Code 201 reçu mais aucune clé de service dans la réponse")
                        return False
                except Exception as e:
                    logger.warning(f"Erreur parsing réponse 201: {e}")
                    # Même si on ne peut pas parser, code 201 = carte valide
                    return True

            elif response.status_code == 404:
                logger.warning("Carte non trouvée, expirée ou non éligible")
                return False

            elif response.status_code == 401:
                logger.error("Token absent")
                return False

            elif response.status_code == 403:
                logger.error(f"Token invalide - Réponse: {response.text[:200]}")
                return False

            else:
                logger.error(f"Erreur API APRAS: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error("Timeout lors de la vérification APRAS")
            return False

        except requests.exceptions.ConnectionError:
            logger.error("Erreur de connexion à l'API APRAS")
            return False

        except Exception as e:
            logger.error(f"Erreur inattendue lors de la vérification: {e}")
            return False

    def get_card_info(self, card_number: str) -> Optional[dict]:
        """
        Récupère les informations détaillées d'une carte

        Args:
            card_number: Le numéro de carte

        Returns:
            Dictionnaire avec les infos de la carte ou None
        """
        try:
            clean_card_number = ''.join(filter(str.isdigit, card_number))

            url = f"{self.base_url}/info"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'card_number': clean_card_number
            }

            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Impossible de récupérer les infos carte: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos carte: {e}")
            return None