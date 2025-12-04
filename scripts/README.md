# Scripts Utilitaires

Ce dossier contient des **scripts d'exemple** pour créer des utilisateurs dans l'application Dispatch Manager.

---

## Scripts de Création Utilisateur

| Script | Langage | Description |
|--------|---------|-------------|
| `create_user_melvin.py` | Python | Exemple complet de création utilisateur |
| `create_melvin_simple.py` | Python | Version simplifiée |
| `create_melvin.ps1` | PowerShell | Version PowerShell pour Windows |

---

## Utilisation

Ces scripts sont des **exemples** pour créer des utilisateurs via Docker.

### Exécuter un script Python

```bash
docker compose exec app python scripts/create_user_melvin.py
```

### Exécuter un script PowerShell (Windows)

```powershell
# Depuis le dossier racine du projet
.\scripts\create_melvin.ps1
```

---

## Scripts de Maintenance

Pour les scripts de maintenance (reset password, diagnostics, migrations, etc.), voir le dossier **`maintenance/`** :

- **`maintenance/admin/`** : Scripts admin (reset passwords, diagnostics)
- **`maintenance/tests/`** : Scripts de test (debug login, stability tests)
- **`maintenance/migrations/`** : Scripts de migration de base de données
- **`maintenance/verify_database.py`** : Vérification intégrité base de données
- **`maintenance/vider_wiki.bat`** : Vider le contenu wiki

---

## Remarques

- Ces scripts sont fournis **à titre d'exemple** pour montrer comment interagir avec la base de données
- Pour un usage en production, créer les utilisateurs via l'interface admin (après connexion avec `admin/admin`)
- Les mots de passe doivent être hashés avec bcrypt avant insertion en base
- Tous les scripts supposent que les conteneurs Docker sont démarrés (`docker compose up -d`)

---

## Documentation Complémentaire

- [README principal](../README.md)
- [Guide d'intégration](../PROJECT_ONBOARDING.md)
- [Documentation maintenance](../maintenance/README.md)
