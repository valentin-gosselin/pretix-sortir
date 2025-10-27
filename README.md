# Plugin Pretix Sortir!

[![PyPI version](https://badge.fury.io/py/pretix-sortir.svg)](https://pypi.org/project/pretix-sortir/)
[![Python versions](https://img.shields.io/pypi/pyversions/pretix-sortir.svg)](https://pypi.org/project/pretix-sortir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/gosselico/pretix-sortir/workflows/CI/badge.svg)](https://github.com/gosselico/pretix-sortir/actions)

Plugin d'intégration du dispositif Sortir! pour Pretix, permettant l'application automatique du tarif réduit après vérification des droits via l'API APRAS.

## 🎯 Fonctionnalités

- ✅ Vérification en temps réel des droits Sortir! (cartes KorriGo)
- 💰 Application automatique du tarif réduit
- 🔒 Sécurisation des données (hash SHA-256)
- 🚫 Prévention des doublons (par événement)
- 📊 Dashboard de suivi des utilisations
- 🌍 Interface bilingue FR/EN
- ♿ Accessibilité WCAG 2.1

## 📋 Prérequis

- Pretix >= 2024.7.0
- Python >= 3.8
- Token API APRAS valide

## 🚀 Installation

### 1. Installation du plugin

```bash
# Via PyPI
pip install pretix-sortir

# Ou depuis GitHub
pip install git+https://github.com/gosselico/pretix-sortir.git
```

### 2. Activation dans Pretix

1. Connectez-vous à l'administration Pretix
2. Allez dans **Événement** → **Paramètres** → **Plugins**
3. Activez **"Sortir! - Tarif réduit"**
4. Configurez les paramètres du plugin

## ⚙️ Configuration

### Paramètres globaux (par événement)

| Paramètre | Description | Valeur par défaut |
|-----------|-------------|-------------------|
| **Activer Sortir!** | Active le plugin pour l'événement | Non |
| **URL API** | URL de l'API APRAS (configurée dans Pretix) | - |
| **Token API** | Token d'authentification APRAS | - |
| **Timeout** | Délai max pour les appels API | 2 secondes |
| **Pré-remplir participant** | Auto-complétion nom/prénom | Oui |
| **Libérer à l'annulation** | Réutilisation des numéros annulés | Oui |

### Configuration par tarif

1. Allez dans **Produits** → Sélectionnez un produit
2. Dans l'onglet **Sortir!**, configurez :
   - ✅ **Validation requise** : Active la vérification pour ce tarif
   - 💶 **Prix Sortir!** : Prix à appliquer si validation OK (ex: 4,50€)

## 🎫 Utilisation côté client

### 1. Sélection du tarif

Le client voit les tarifs disponibles avec indication "Sortir!" :
```
🎫 Plein tarif : 16,00€
🎫 Tarif Sortir! : 4,50€ (sur présentation de la carte)
```

### 2. Saisie du numéro

Pour chaque billet au tarif Sortir!, le client doit saisir un numéro de carte valide :


- Format : 10 chiffres exactement
- Validation en temps réel
- Feedback visuel immédiat (✅/❌)

### 3. Validation et paiement

Une fois tous les numéros validés :
- Le tarif réduit est automatiquement appliqué
- Le client procède au paiement normal
- Les numéros sont enregistrés de manière sécurisée

## 🔧 Administration

### Dashboard des utilisations

Accédez au suivi via **Événement** → **Sortir!** → **Utilisations**

Informations disponibles :
- Nombre total d'utilisations
- Statut par numéro (validé/utilisé/annulé)
- Commandes associées
- Dates et heures

### Export des données

```bash
# Export CSV des utilisations
python manage.py export_sortir_usage --event=mon-event --format=csv
```

## 🧪 Tests

Pour obtenir les informations de test (token, numéros de cartes), contactez l'APRAS.

### Commandes de test

```bash
# Tests unitaires
pytest tests/

# Tests d'intégration
pytest tests/integration/

# Coverage
pytest --cov=pretix_sortir tests/
```

## 🔒 Sécurité

- **Stockage** : Numéros hashés (SHA-256 + salt)
- **API** : HTTPS obligatoire + token sécurisé
- **Logs** : Anonymisation automatique
- **RGPD** : Conforme, aucune donnée personnelle en clair

## 📊 Monitoring

### Métriques disponibles

- Temps de réponse API (P50, P95, P99)
- Taux de validation réussie
- Nombre de doublons bloqués
- Disponibilité du service

### Logs

```bash
# Consulter les logs
docker logs pretix-dev | grep sortir

# Niveau de log
export SORTIR_LOG_LEVEL=DEBUG
```

## 🐛 Dépannage

### L'API ne répond pas

1. Vérifiez le token API
2. Testez l'URL configurée dans Pretix
3. Vérifiez les logs : Circuit breaker activé ?

### Numéro refusé alors qu'il devrait être valide

1. Vérifiez qu'il n'est pas déjà utilisé
2. Cache de 5 min sur les erreurs 404/403
3. Videz le cache si nécessaire : `cache.delete('sortir_api_404_XXXX')`

### Prix non appliqué

1. Vérifiez la configuration du produit
2. Le numéro doit être validé AVANT le checkout
3. Vérifiez les logs pour les erreurs

## 📝 Changelog

### v1.0.0 (2025-10-27)
- 🎉 Version initiale
- ✅ Validation en temps réel
- 💰 Application du tarif réduit
- 🔒 Sécurisation des données
- 📊 Dashboard admin

## 📄 Licence

MIT - Voir [LICENSE](LICENSE)

## 🤝 Support

- **Issues GitHub** : [github.com/gosselico/pretix-sortir/issues](https://github.com/gosselico/pretix-sortir/issues)
- **Contact APRAS** : Pour obtenir un token API et les informations de test

## 👥 Crédits

Plugin développé pour l'intégration du dispositif Sortir! de l'APRAS.

---

*Ce plugin est en développement actif. Les contributions sont les bienvenues !*