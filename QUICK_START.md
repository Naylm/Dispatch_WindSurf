# Quick Start - Dispatch Manager v2.0

## ⚠️ AVANT DE DÉMARRER

1. **Éditez le fichier `.env`** et remplacez les placeholders :
   ```env
   SECRET_KEY=CHANGE_ME_GENERATE_WITH_PYTHON_SECRETS
   POSTGRES_PASSWORD=CHANGE_ME_GENERATE_WITH_PYTHON_SECRETS
   ```

   Générez des clés avec :
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

## 🚀 Démarrage Rapide

```bash
# 1. Arrêter les containers existants
docker compose down

# 2. Rebuild (première fois ou après changements)
docker compose build --no-cache

# 3. Démarrer
docker compose up -d

# 4. Vérifier les logs
docker logs dispatch_manager -f
# Attendez: "🚀 Note editing system initialized"

# 5. Appliquer les indexes (OBLIGATOIRE première fois)
docker exec -it dispatch_manager python apply_indexes.py

# 6. Test
curl http://localhost/health
# Devrait retourner: healthy
```

## 🔧 Commandes Utiles

```bash
# Voir les logs en temps réel
docker logs -f dispatch_manager

# Restart sans rebuild
docker compose restart

# Stop tout
docker compose down

# Accès PostgreSQL
docker exec -it dispatch_postgres psql -U dispatch_user -d dispatch
```

## ⚠️ Problèmes Courants

### "SECRET_KEY doit être définie"
→ Éditez `.env` et ajoutez une vraie SECRET_KEY

### "Votre mot de passe doit être réinitialisé"
→ Les mots de passe en clair ne sont plus acceptés. Utilisez :
```bash
docker exec -it dispatch_manager python
```
```python
from werkzeug.security import generate_password_hash
from db_config import get_db
db = get_db()
hash = generate_password_hash("nouveau_mdp")
db.execute("UPDATE users SET password=? WHERE username='admin'", (hash,))
db.commit()
db.close()
```

### Erreur CSRF
→ Désactivez temporairement dans `.env` :
```env
WTF_CSRF_ENABLED=false
```

## 📚 Documentation Complète

- **DEPLOYMENT_GUIDE.md** - Guide de déploiement complet
- **SECURITY_AUDIT_CHANGELOG.md** - Détails des changements
- **DB_CONTEXT_MANAGER_GUIDE.md** - Gestion des connexions DB

## ✅ Vérifications

- [ ] `.env` configuré avec secrets uniques
- [ ] Containers démarrés sans erreur
- [ ] Indexes appliqués
- [ ] http://localhost accessible
- [ ] Connexion admin fonctionne

**Prêt à l'emploi!** 🎉
