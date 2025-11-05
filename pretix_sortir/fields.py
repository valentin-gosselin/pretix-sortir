"""
Champs de base de données chiffrés pour le plugin Sortir!
"""

import os
import logging
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger('pretix.plugins.sortir')


def get_encryption_key():
    """
    Récupère la clé de chiffrement depuis les settings ou les variables d'environnement.
    La clé doit être définie dans SORTIR_ENCRYPTION_KEY.
    """
    # Essaie d'abord les settings Django
    key = getattr(settings, 'SORTIR_ENCRYPTION_KEY', None)

    # Sinon, essaie les variables d'environnement
    if not key:
        key = os.environ.get('SORTIR_ENCRYPTION_KEY')

    if not key:
        raise ValueError(
            "SORTIR_ENCRYPTION_KEY n'est pas définie. "
            "Ajoutez-la dans vos variables d'environnement ou dans pretix.cfg. "
            "Générez une clé avec: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    return key.encode() if isinstance(key, str) else key


class EncryptedTextField(models.TextField):
    """
    Champ TextField qui chiffre automatiquement les données au repos.
    Utilise Fernet (AES-128 CBC avec HMAC SHA-256) de la librairie cryptography.

    La clé de chiffrement doit être stockée dans SORTIR_ENCRYPTION_KEY (settings).

    Utilisation:
        api_token = EncryptedTextField(blank=True, help_text="Token chiffré")
    """

    description = "TextField chiffré avec Fernet (AES-128)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fernet = None

    @property
    def fernet(self):
        """Lazy loading de l'instance Fernet"""
        if self._fernet is None:
            key = get_encryption_key()
            self._fernet = Fernet(key)
        return self._fernet

    def from_db_value(self, value, expression, connection):
        """Déchiffre la valeur lue depuis la base"""
        if value is None or value == '':
            return value

        # Si la valeur commence par 'gAAAAA', c'est un token chiffré avec Fernet
        if value.startswith('gAAAAA'):
            try:
                # Déchiffre et retourne la valeur en clair
                decrypted = self.fernet.decrypt(value.encode()).decode('utf-8')
                return decrypted
            except InvalidToken:
                logger.error(
                    "Impossible de déchiffrer le token - La clé de chiffrement a peut-être changé"
                )
                raise ValueError("Token invalide - Impossible de déchiffrer")
            except Exception as e:
                logger.error(f"Erreur lors du déchiffrement: {e}")
                raise
        else:
            # Token en clair (anciennes données) - retourner tel quel
            # À la prochaine sauvegarde, il sera automatiquement chiffré
            logger.warning(
                "Token en clair détecté - Il sera chiffré lors de la prochaine sauvegarde"
            )
            return value

    def get_prep_value(self, value):
        """Chiffre la valeur avant de l'enregistrer en base"""
        if value is None or value == '':
            return value

        # Si la valeur est déjà chiffrée (commence par gAAAAA...), ne pas rechiffrer
        if isinstance(value, str) and value.startswith('gAAAAA'):
            return value

        try:
            # Chiffre la valeur
            encrypted = self.fernet.encrypt(value.encode()).decode('utf-8')
            return encrypted
        except Exception as e:
            logger.error(f"Erreur lors du chiffrement: {e}")
            raise

    def deconstruct(self):
        """
        Retourne une définition qui peut être utilisée pour les migrations.
        Le champ est stocké comme TextField en base.
        """
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs
