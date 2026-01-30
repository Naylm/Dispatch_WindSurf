# Scripts Utilitaires

Ce dossier contient des scripts helper et des exemples pour Dispatch Manager.

---

## 📜 Scripts Helper

### dispatch.ps1
**Helper PowerShell pour Windows** - Équivalent du Makefile

Commandes disponibles :
```powershell
.\scripts\dispatch.ps1 help         # Afficher l'aide
.\scripts\dispatch.ps1 up           # Démarrer les conteneurs
.\scripts\dispatch.ps1 down         # Arrêter les conteneurs
.\scripts\dispatch.ps1 logs         # Voir les logs
.\scripts\dispatch.ps1 db-backup    # Backup PostgreSQL
```

---

## 📁 Examples (Sous-dossier)

Le dossier `examples/` contient des **scripts de démonstration** pour créer des utilisateurs.

| Script | Langage | Description |
|--------|---------|-------------|
| `examples/create_user_melvin.py` | Python | Exemple complet de création utilisateur |
| `examples/create_melvin_simple.py` | Python | Version simplifiée |
| `examples/create_melvin.ps1` | PowerShell | Version PowerShell pour Windows |
| `examples/make_melvin_normal.py` | Python | Passer Melvin en compte normal (role=user) |

### Utilisation des exemples

```bash
# Exécuter un script Python
docker compose exec app python scripts/examples/create_user_melvin.py
docker compose exec app python scripts/examples/make_melvin_normal.py

# Exécuter PowerShell (Windows)
.\scripts\examples\create_melvin.ps1
```

**Note** : Ces scripts sont **uniquement des exemples** à des fins pédagogiques.
Pour créer des utilisateurs en production, utiliser l'interface admin (`admin/admin`).

---

## 🛠️ Scripts de Maintenance

Les scripts de maintenance (reset password, diagnostics, migrations) sont dans **`maintenance/`** :

| Dossier | Contenu |
|---------|---------|
| `maintenance/admin/` | Scripts admin (reset passwords, diagnostics) |
| `maintenance/tests/` | Scripts de test (debug login, stability) |
| `maintenance/migrations/` | Scripts de migration base de données |
| `maintenance/verify_database.py` | Vérification intégrité DB |
| `maintenance/vider_wiki.bat` | Vider contenu wiki |

---

## 📚 Documentation Complémentaire

- [README principal](../README.md)
- [Guide d'intégration (60 min)](../PROJECT_ONBOARDING.md)
- [Documentation complète](../docs/)
- [Guide maintenance](../maintenance/README.md)
