"""
Plugin Pretix Sortir!
Intégration du tarif réduit Sortir! via l'API APRAS pour Pretix.

Ce plugin permet de vendre des billets au tarif Sortir! après vérification
en temps réel des droits via l'API APRAS (KorriGo Services).
"""

from .apps import SortirPluginConfig

__version__ = '1.0.0'
__all__ = ['SortirPluginConfig']