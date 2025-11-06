# Système d'Auto-Collectstatic

## Problème résolu

Dans Pretix, quand on met à jour les fichiers JavaScript ou CSS d'un plugin, il faut normalement :
1. Faire `collectstatic` pour copier les nouveaux assets
2. Vider le cache pour forcer le rechargement
3. Redémarrer le serveur

C'est fastidieux en production et source d'erreurs.

## Solution implémentée

Le plugin Sortir inclut un système d'**auto-collectstatic** qui s'exécute automatiquement au démarrage de Pretix.

### Comment ça marche

Dans `apps.py`, la méthode `ready()` :

1. **Détecte la version** du plugin
2. **Vérifie en cache** si le collectstatic a déjà été fait pour cette version
3. Si non, **exécute automatiquement** :
   - `collectstatic --noinput`
   - Vide les clés de cache `*sortir*`
   - Met un flag en cache (expire après 24h)

### Avantages

- ✅ **Zero intervention manuelle** en production
- ✅ **Intelligent** : ne le fait qu'une fois par version
- ✅ **Sûr** : n'impacte pas Pretix si ça échoue
- ✅ **Traçable** : logs `[Sortir] Running collectstatic...`

### Configuration

Variable d'environnement optionnelle :
- `SORTIR_SKIP_AUTOCOLLECT=1` : désactive l'auto-collectstatic (utile en dev)

### En production

```bash
# Simple !
pip install pretix-sortir==X.X.X
docker restart pretix

# C'est tout ! Le plugin fait automatiquement :
# - collectstatic
# - cache clear pour sortir
```

## Pourquoi c'est important

Sans ce système, les mises à jour JavaScript/CSS peuvent ne pas être visibles côté client à cause du cache navigateur et du cache Pretix. L'auto-collectstatic garantit que chaque nouvelle version du plugin déploie correctement ses assets.