# Changelog v1.0.3

## 🚀 Améliorations

### Gestion automatique de la clé de chiffrement
- **Auto-génération** : Le plugin génère automatiquement une clé de chiffrement si elle n'existe pas
- **Stockage persistant** : La clé est sauvegardée dans `/data/.sortir_encryption_key`
- **Compatibilité** : Support des clés via variables d'environnement pour compatibilité avec les déploiements existants

### Gestion des erreurs améliorée
- **Récupération gracieuse** : Si la clé de chiffrement change, le plugin retourne une valeur vide au lieu de planter
- **Messages clairs** : Logs informatifs pour guider l'administrateur en cas de problème

## 🐛 Corrections

### Résolution du problème "SORTIR_ENCRYPTION_KEY n'est pas définie"
- Plus besoin de configuration manuelle de la clé
- Installation plug-and-play sans intervention sur le serveur

## 📝 Documentation

- Ajout d'une section sur la gestion de la clé de chiffrement dans le README
- Instructions pour les migrations et restaurations

## ⬆️ Migration depuis v1.0.2

Aucune action requise. Le plugin générera automatiquement une clé si elle n'existe pas.

**Note** : Si vous aviez déjà une clé configurée manuellement, elle sera conservée et utilisée en priorité.