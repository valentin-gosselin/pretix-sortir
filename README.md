# Pretix Sortir!

Plugin d'intégration du dispositif **Sortir!** pour Pretix, permettant la validation automatique des cartes KorriGo et l'application du tarif réduit via l'API APRAS.

[![PyPI version](https://badge.fury.io/py/pretix-sortir.svg)](https://pypi.org/project/pretix-sortir/)
[![Python versions](https://img.shields.io/pypi/pyversions/pretix-sortir.svg)](https://pypi.org/project/pretix-sortir/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Niveau 1 : Organisateur](#niveau-1--organisateur)
  - [Niveau 2 : Événement](#niveau-2--événement)
  - [Niveau 3 : Produits/Tarifs](#niveau-3--produitstarifs)
- [Utilisation](#utilisation)
- [Administration](#administration)
- [Sécurité et RGPD](#sécurité-et-rgpd)
- [Dépannage](#dépannage)

---

## Fonctionnalités

- **Validation en temps réel** des cartes KorriGo via l'API APRAS
- **Application automatique** du tarif réduit Sortir!
- **Prévention des doublons** : une carte ne peut être utilisée qu'une fois par événement
- **Traçabilité complète** : notification automatique à l'APRAS après paiement confirmé
- **Sécurité** : stockage chiffré des tokens API, hashage des numéros de carte
- **RGPD compliant** : gestion des données avec rétention configurable
- **Circuit breaker** : protection automatique contre les pannes API
- **Cache intelligent** : optimisation des appels API avec retry automatique

---

## Prérequis

- **Pretix** >= 2024.7.0
- **Python** >= 3.8
- **Token API APRAS** : Contactez l'APRAS pour obtenir vos identifiants

---

## Installation

### Via PyPI (recommandé)

```bash
pip install pretix-sortir
```

### Depuis les sources

```bash
pip install git+https://github.com/valentin-gosselin/pretix-sortir.git
```

### Activation dans Pretix

1. Redémarrez votre instance Pretix
2. Le plugin apparaît automatiquement dans la liste des plugins disponibles

---

## Configuration

La configuration se fait en **trois niveaux hiérarchiques** :

### Niveau 1 : Organisateur

**Où :** `Organisateur` → `Paramètres` → `Sortir!`

Cette configuration est **partagée par tous les événements** de l'organisateur.

#### Paramètres API

| Paramètre | Description | Obligatoire |
|-----------|-------------|-------------|
| **URL API Sortir** | URL de l'API APRAS (fournie par l'APRAS)<br>Exemple : `https://test.sortir-v2.extrazimut.net` | Oui |
| **Token API** | Token d'authentification (fourni par l'APRAS)<br>Stocké de manière chiffrée | Oui |
| **Timeout API** | Délai maximum d'attente pour les appels API<br>Valeur recommandée : 2 secondes | Non (défaut: 2s) |

#### Options de comportement

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| **Pré-remplir nom/prénom** | Pré-remplir automatiquement les champs participant avec les infos de l'API | Activé |
| **Libérer à l'annulation** | Autoriser la réutilisation d'un numéro de carte si la commande est annulée | Activé |

#### Rétention des données (RGPD)

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| **Durée de conservation (jours)** | Durée de conservation des données SortirUsage après la fin de l'événement | 90 jours |
| **Durée de conservation des logs (jours)** | Durée de conservation des logs d'audit pour la sécurité | 365 jours |

---

### Niveau 2 : Événement

**Où :** `Événement` → `Paramètres` → `Plugins`

#### Activation du plugin

1. Allez dans `Événement` → `Paramètres` → `Plugins`
2. Cochez **"Sortir! - Tarif réduit"**
3. Cliquez sur `Enregistrer`

Une fois activé, **une entrée "Sortir!" apparaît dans la barre latérale de l'événement** (comme au niveau Organisateur).

---

### Niveau 3 : Produits/Tarifs

**Où :** `Événement` → `Sortir!` (dans la barre latérale) → **Liste des produits**

Une fois le plugin activé, configurez les produits qui nécessitent une validation Sortir! :

#### Configuration par produit

1. Dans la section `Sortir!` de la barre latérale, vous voyez la liste de tous vos produits
2. Cochez les produits qui doivent nécessiter une carte Sortir! valide
3. Cliquez sur `Enregistrer`

**Important :** Le prix du tarif Sortir! est le prix standard du produit. Créez un produit dédié (exemple : "Tarif Sortir!" à 4,50€) plutôt que d'utiliser le tarif plein.

#### Exemple de configuration

**Produit 1 : Tarif plein**
- Prix : 16,00€
- Sortir! : **Non coché**

**Produit 2 : Tarif Sortir!**
- Prix : 4,50€
- Sortir! : **Coché** ✓

---

## Utilisation

### Côté acheteur

#### 1. Sélection du tarif

L'acheteur voit les différents tarifs disponibles :

```
Tarif plein : 16,00€
Tarif Sortir! : 4,50€ (carte KorriGo requise)
```

#### 2. Validation de la carte

Lorsque l'acheteur sélectionne un tarif Sortir!, un champ de saisie apparaît :

- **Format attendu** : 10 chiffres exactement
- **Validation en temps réel** : Le numéro est vérifié auprès de l'API APRAS immédiatement
- **Feedback visuel** : Indication claire de validité (carte valide / carte invalide)

**Règles de validation :**
- La carte doit être active dans le système APRAS
- La carte ne doit pas avoir déjà été utilisée pour cet événement
- Le délai de validation est de 2 secondes maximum

#### 3. Cas particuliers

**Correction d'erreur de saisie :**
L'acheteur peut supprimer et ressaisir son numéro de carte dans un délai de 5 minutes sans erreur "déjà utilisée".

**Plusieurs billets :**
Si l'acheteur commande plusieurs billets Sortir!, il doit saisir un numéro de carte différent pour chaque billet.

#### 4. Paiement

Une fois toutes les cartes validées, l'acheteur peut procéder au paiement normalement. Après confirmation du paiement, le plugin envoie automatiquement une notification à l'APRAS pour la traçabilité.

---

## Sécurité et RGPD

### Stockage des données

| Donnée | Méthode de stockage |
|--------|---------------------|
| Numéro de carte | **Hash SHA-256** avec salt unique par organisateur |
| Token API | **Chiffrement** au repos (EncryptedTextField) |
| Logs | **Anonymisation automatique** des numéros de carte |

### Conformité RGPD

- **Minimisation** : Seules les données nécessaires sont stockées
- **Rétention** : Durées configurables selon les besoins
- **Traçabilité** : Logs d'audit pour toutes les opérations sensibles
- **Droit à l'oubli** : Suppression automatique selon la durée de rétention

### Protection API

- **HTTPS obligatoire** : Communication chiffrée avec l'API APRAS
- **Circuit breaker** : Coupure automatique en cas de panne API (5 minutes)
- **Rate limiting** : Protection contre les abus (10 tentatives / 5 minutes par IP)
- **Cache** : Réduction des appels API avec cache des erreurs 404/403

---

## Dépannage

### Problème : "API Sortir non configurée"

**Cause :** La configuration au niveau Organisateur n'est pas complète.

**Solution :**
1. Allez dans `Organisateur` → `Paramètres` → `Sortir!`
2. Vérifiez que l'URL API et le Token sont bien renseignés
3. Testez la connexion en validant un numéro de test

### Problème : "Carte non éligible, expirée ou inconnue"

**Causes possibles :**
- Le numéro de carte n'existe pas dans la base APRAS
- Les droits Sortir! de la carte ont expiré ou ne sont pas attribués
- Erreur de saisie du numéro (doit être exactement 10 chiffres)

**Solution :**
- Vérifiez le numéro auprès du bénéficiaire
- Contactez l'APRAS pour vérifier le statut de la carte

### Problème : "Cette carte a déjà été utilisée pour cet événement"

**Cause :** Une règle anti-fraude empêche l'utilisation multiple d'une même carte.

**Solutions :**
1. **Correction immédiate** : Si l'utilisateur vient de saisir le numéro et veut le corriger, il peut le supprimer et ressaisir dans les 5 minutes
2. **Utilisation précédente** : Si la carte a vraiment été utilisée pour une commande antérieure, c'est normal. Utiliser une autre carte
3. **Commande annulée** : Si "Libérer à l'annulation" est activé, la carte redevient disponible après annulation de la commande

### Problème : "Service temporairement indisponible"

**Cause :** Le circuit breaker est activé suite à plusieurs échecs consécutifs de l'API APRAS.

**Solution :**
- Attendre 5 minutes (réactivation automatique)
- Vérifier l'état de l'API APRAS
- Consulter les logs : `docker logs pretix | grep sortir`

### Problème : Le tarif réduit ne s'applique pas

**Vérifications :**
1. Le plugin est activé pour l'événement (`Événement` → `Paramètres` → `Plugins`)
2. Le produit a la case "Nécessite validation Sortir!" cochée
3. Le numéro de carte a été validé **avant** de passer au paiement
4. Le cache du navigateur n'est pas obsolète (Ctrl+F5 pour rafraîchir)

### Consulter les logs

```bash
# Logs généraux
docker logs pretix-dev | grep sortir

# Logs d'erreur uniquement
docker logs pretix-dev | grep -i "error.*sortir"

# Logs de validation de carte
docker logs pretix-dev | grep "Vérification droits Sortir"

# Logs de grant APRAS
docker logs pretix-dev | grep "Grant envoyé"
```

---

## Architecture technique

### Flux de données

```
1. Acheteur saisit numéro carte
   ↓
2. JavaScript → AJAX vers Pretix
   ↓
3. Pretix → GET /api/partners/{CARD} (API APRAS)
   ← Retour : service_key (string)
   ↓
4. Création SortirUsage (status='pending', service_key stocké)
   ↓
5. Acheteur finalise commande et paie
   ↓
6. Signal order_paid déclenché
   ↓
7. Pretix → POST /api/partners/grant (API APRAS avec service_key)
   ← Retour : apras_request_id
   ↓
8. SortirUsage mis à jour (status='used', apras_request_id stocké)
```

### Statuts des SortirUsage

| Statut | Description |
|--------|-------------|
| `pending` | Carte validée, en attente de paiement |
| `validated` | Commande créée mais pas encore payée |
| `used` | Commande payée et notification APRAS envoyée avec succès |
| `cancelled` | Commande annulée |

---

## Changelog

### v1.0.0 (2025-10-28)

**Ajouté**
- Validation en temps réel des cartes KorriGo via API APRAS
- Application automatique du tarif réduit
- Dashboard de suivi des utilisations
- Configuration à trois niveaux (Organisateur / Événement / Produit)
- Protection anti-fraude (une carte par événement)
- Système de correction de carte (5 minutes)
- Notification automatique APRAS via POST grant après paiement
- Circuit breaker et retry automatique
- Cache intelligent des erreurs API
- Logs d'audit complets
- Conformité RGPD avec rétention configurable

**Sécurité**
- Stockage chiffré des tokens API
- Hashage SHA-256 des numéros de carte
- Anonymisation automatique des logs
- Rate limiting (10 tentatives / 5 minutes)

---

## Licence

MIT - Voir [LICENSE](LICENSE)

---

## Support

- **Issues GitHub** : [github.com/valentin-gosselin/pretix-sortir/issues](https://github.com/valentin-gosselin/pretix-sortir/issues)
- **Contact APRAS** : Pour obtenir un token API et l'url de l'API APRAS
---

## Crédits

Plugin développé pour l'intégration du dispositif **Sortir!** de l'APRAS (Association pour la Promotion de l’Action et de l’Animation Sociale).

Développement : Valentin Gosselin

---

*Ce plugin est en développement actif. Les contributions sont les bienvenues !*
