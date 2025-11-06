# Changelog v1.0.2

## Corrections critiques

### ✅ Handler order_paid (depuis commit 154e04f)
- Envoie les notifications POST /api/partners/grant à l'APRAS après paiement
- Stockage service_key et apras_request_id pour traçabilité
- Mise à jour status de 'validated' vers 'used'

### ✅ Cache buster JavaScript/CSS
- Ajout de `?v={timestamp}` aux URLs des assets
- Force le rechargement après modifications

### ✅ Amélioration détection sélecteur quantité
- 7 stratégies de recherche au lieu de 4
- Logs de debug détaillés pour diagnostic
- Recherche par data-item-id et proximité

## Corrections de bugs

### ✅ Suppression correcte des champs
- Fix: les champs excédentaires sont maintenant supprimés quand la quantité diminue
- Boucle jusqu'à 20 pour nettoyer tous les champs orphelins

### ✅ Cleanup avant validation
- Nettoie les cartes "pending" avant revalidation
- Évite les doublons en base de données

## Améliorations techniques

### ✅ Logging amélioré
- Console.log détaillés dans sortir.js pour debug
- Messages d'erreur plus explicites
- Traçabilité complète du flux de validation

### ✅ Vue SortirConfigView (optionnel)
- Endpoint `/sortir/config/` pour approche alternative
- Permet le chargement global avec activation conditionnelle

## Migration depuis 1.0.1

```bash
# 1. Mettre à jour le package
pip install pretix-sortir==1.0.2

# 2. Collecter les assets et vider le cache
docker exec pretix python -m pretix collectstatic --noinput
docker exec pretix python -m pretix shell -c "from django.core.cache import cache; cache.clear()"

# 3. Redémarrer Pretix
docker compose restart pretix
```

## Notes importantes

- **CRITIQUE** : Le handler `order_paid` est essentiel pour la notification APRAS
- Le cache buster est nécessaire pour que les modifications JS soient visibles
- Les logs de debug peuvent être désactivés en production si nécessaire