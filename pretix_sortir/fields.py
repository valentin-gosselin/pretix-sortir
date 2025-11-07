"""
Champs de base de données chiffrés pour le plugin Sortir!
"""

import os
import logging
from pathlib import Path
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger('pretix.plugins.sortir')


def get_encryption_key():
    """
    Récupère ou génère automatiquement une clé de chiffrement.
    La clé est stockée dans un fichier dans le datadir de Pretix pour persistance.
    """
    # Essaie d'abord les variables d'environnement (pour compatibilité)
    key = os.environ.get('SORTIR_ENCRYPTION_KEY')

    if key:
        logger.debug("[Sortir] Utilisation de la clé depuis variable d'environnement")
        return key.encode() if isinstance(key, str) else key

    # Essaie les settings Django
    key = getattr(settings, 'SORTIR_ENCRYPTION_KEY', None)

    if key:
        logger.debug("[Sortir] Utilisation de la clé depuis settings Django")
        return key.encode() if isinstance(key, str) else key

    # Sinon, utilise un fichier de clé persistant dans le datadir
    data_dir = getattr(settings, 'DATA_DIR', '/data')
    key_file = Path(data_dir) / '.sortir_encryption_key'

    try:
        if key_file.exists():
            with open(key_file, 'r') as f:
                key = f.read().strip()
                logger.debug(f"[Sortir] Clé de chiffrement chargée depuis {key_file}")
                return key.encode() if isinstance(key, str) else key
        else:
            # Génère une nouvelle clé
            new_key = Fernet.generate_key()

            # Crée le répertoire si nécessaire
            key_file.parent.mkdir(parents=True, exist_ok=True)

            # Sauvegarde la clé
            with open(key_file, 'wb') as f:
                f.write(new_key)

            # Change les permissions pour sécuriser le fichier
            try:
                os.chmod(key_file, 0o600)
            except:
                pass  # Peut échouer sur certains systèmes

            logger.info(f"[Sortir] Nouvelle clé de chiffrement générée et sauvegardée dans {key_file}")
            logger.warning("[Sortir] IMPORTANT: Sauvegardez cette clé pour les migrations/restaurations!")

            return new_key

    except (IOError, OSError) as e:
        logger.error(f"[Sortir] Erreur lors de la gestion du fichier de clé: {e}")
        # En dernier recours, génère une clé temporaire (non persistante)
        logger.warning("[Sortir] Utilisation d'une clé temporaire - Les données chiffrées ne seront pas persistantes!")
        return Fernet.generate_key()


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
                logger.warning(
                    "[Sortir] Token impossible à déchiffrer (clé incorrecte). "
                    "Retour d'une valeur vide - veuillez re-saisir le token dans l'interface."
                )
                return ""  # Retourne une chaîne vide au lieu de lever une exception
            except Exception as e:
                logger.error(f"[Sortir] Erreur lors du déchiffrement: {e}")
                return ""  # Retourne une chaîne vide en cas d'erreur
        else:
            # Token en clair (anciennes données) - retourner tel quel
            # À la prochaine sauvegarde, il sera automatiquement chiffré
            logger.debug(
                "[Sortir] Token en clair détecté - Il sera chiffré lors de la prochaine sauvegarde"
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
