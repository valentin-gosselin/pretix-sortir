# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [1.0.0] - 2025-10-27

### Ajouté
- 🎉 Version initiale du plugin Sortir! pour Pretix
- ✅ Validation en temps réel des cartes KorriGo via l'API APRAS
- 💰 Application automatique du tarif réduit Sortir!
- 🔒 Stockage sécurisé des numéros (hash SHA-256 avec salt)
- 🚫 Prévention des doublons au niveau événement
- 📊 Dashboard de suivi des utilisations dans l'admin
- 🌍 Interface bilingue français/anglais
- ♿ Interface accessible WCAG 2.1
- 🔄 Validation AJAX avec feedback visuel immédiat
- 📝 Pré-remplissage automatique des noms/prénoms si disponibles
- ⚡ Circuit breaker et cache pour protection API
- 🔧 Configuration flexible par événement et par tarif
- 📖 Documentation complète (README, CLAUDE.md)

### Sécurité
- Hashage SHA-256 avec salt unique par événement
- Aucun stockage de numéro en clair
- Logs anonymisés (affichage ***XXXX)
- Token API en variable d'environnement
- HTTPS obligatoire pour les appels API


## [À venir]

### Prévu pour v1.1.0
- [ ] Export CSV des utilisations pour comptabilité
- [ ] Statistiques détaillées par période
- [ ] Support multi-structures APRAS
- [ ] Webhook pour notifications asynchrones
- [ ] Intégration avec le système de scan à l'entrée

### Prévu pour v1.2.0
- [ ] API REST pour intégration externe
- [ ] Rapports automatiques mensuels
- [ ] Bulk validation pour import de listes
- [ ] Support des quotas par structure

---

Pour signaler un bug ou suggérer une amélioration : [GitHub Issues](https://github.com/gosselico/pretix-sortir/issues)