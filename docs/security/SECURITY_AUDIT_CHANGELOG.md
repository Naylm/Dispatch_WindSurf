# Audit de Sécurité et Corrections - Changelog

**Date**: 24 Novembre 2025
**Statut**: Phase 1 Terminée - Corrections Critiques de Sécurité

---

## ✅ Phase 1: Corrections Critiques de Sécurité (TERMINÉE)

### 1.1 Protection CSRF Ajoutée
**Fichiers modifiés**:
- `requirements.txt`: Ajout de Flask-WTF==1.2.1
- `app.py`:
  - Import de CSRFProtect (ligne 6)
  - Initialisation CSRF (lignes 47-50)
  - Configuration WTF_CSRF_ENABLED

**Impact**: Protection contre les attaques Cross-Site Request Forgery sur toutes les routes POST/PUT/DELETE

**Action requise**:
- Exécuter `pip install -r requirements.txt` dans le container
- Rebuild le container Docker

### 1.2 Suppression du Fallback Mot de Passe en Clair
**Fichiers modifiés**:
- `app.py` (lignes 673-717):
  - Supprimé le code qui acceptait les mots de passe en clair (lignes 689-698, 708-717 anciennes)
  - Ajouté des messages d'erreur appropriés
  - Remplacé `print()` par `app.logger`

**Impact**:
- ⚠️ **BREAKING CHANGE**: Les utilisateurs avec mots de passe en clair ne pourront plus se connecter
- Amélioration majeure de la sécurité

**Action requise**:
- Réinitialiser les mots de passe de tous les utilisateurs
- Ou créer un script de migration pour hasher tous les mots de passe existants

### 1.3 SECRET_KEY Obligatoire en Production
**Fichiers modifiés**:
- `app.py` (lignes 27-41):
  - SECRET_KEY maintenant obligatoire en production
  - L'application refuse de démarrer si SECRET_KEY absent en mode production
  - Génération temporaire uniquement en développement

**Impact**: Empêche le démarrage accidentel en production sans SECRET_KEY sécurisée

**Action requise**:
- Définir SECRET_KEY dans les variables d'environnement
- Ou créer un fichier .env avec SECRET_KEY

### 1.4 Fichier .env.example Mis à Jour
**Fichiers modifiés**:
- `.env.example`: Enrichi avec toutes les variables nécessaires

**Nouvelles variables documentées**:
```env
SECRET_KEY=supersecret_change_this_in_production_MANDATORY
POSTGRES_USER=dispatch_user
POSTGRES_PASSWORD=change_this_password_in_production_MANDATORY
WTF_CSRF_ENABLED=true
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_HTTPONLY=true
GUNICORN_WORKERS=4
```

**Action requise**:
- Créer un fichier .env basé sur .env.example
- Changer TOUS les mots de passe par défaut

### 1.5 Sécurisation des Uploads de Fichiers
**Fichiers modifiés**:
- `wiki_routes_v2.py`:
  - Retrait de SVG des extensions autorisées (ligne 12)
  - Ajout de validation par magic bytes (lignes 16-43)
  - Utilisation d'UUID au lieu de timestamps (lignes 507-509)

**Impact**:
- Prévention des attaques XSS via SVG
- Validation du contenu réel des fichiers
- Noms de fichiers imprévisibles

**Fonctionnalités ajoutées**:
- `validate_image_content()`: Vérifie les magic bytes
- UUID aléatoire pour les noms de fichiers

### 1.6 Corrections des Validations SQL et Auth
**Fichiers modifiés**:
- `app.py`:
  - Retrait de l'import `contextmanager` non utilisé (ligne 12 supprimée)
  - Remplacement des comparaisons `LOWER()` par comparaisons exactes (lignes 153, 204, 904, 978)

**Impact**:
- Prévention de l'énumération d'utilisateurs
- Authentification plus stricte et sécurisée

**Requêtes corrigées**:
```sql
-- AVANT (vulnérable)
WHERE LOWER(collaborateur)=LOWER(?)

-- APRÈS (sécurisé)
WHERE collaborateur=?
```

---

## ✅ Phase 2.1: Indexes de Performance (TERMINÉE)

### 2.1 Création des Indexes de Base de Données
**Fichiers créés**:
- `add_indexes.sql`: Script SQL avec 8 indexes
- `apply_indexes.py`: Script Python pour appliquer les indexes

**Indexes créés**:
1. `idx_incidents_collaborateur` - Filtre par technicien
2. `idx_incidents_archived` - Filtre archivés/actifs
3. `idx_incidents_etat` - Statistiques par statut
4. `idx_incidents_date_affectation` - Tri chronologique
5. `idx_incidents_collab_archived` - Index composé (optimisation maximale)
6. `idx_techniciens_prenom` - Authentification techniciens
7. `idx_users_username` - Authentification users

**Impact Attendu**:
- Réduction de 70-90% du temps de requête sur grandes tables
- Passage de O(n) à O(log n) pour les recherches

**Action requise**:
```bash
# Dans le container
python apply_indexes.py
```

---

## 📋 Phase 2: Tâches Restantes (EN ATTENTE)

### 2.2 Context Managers pour Connexions DB
**Objectif**: Corriger les fuites de connexions DB

**Problème identifié**:
- 50+ routes ne ferment pas `db.close()`
- Risque d'épuisement du pool de connexions

**Solution proposée**:
```python
@contextmanager
def get_db_context():
    db = get_db()
    try:
        yield db
    finally:
        db.close()

# Usage
with get_db_context() as db:
    # ... requêtes ...
```

### 2.3 Optimisation des Requêtes
**Problème identifié**:
- 5 requêtes séparées au chargement de la page (incidents, techniciens, priorités, sites, statuts)
- Requêtes stats en boucle (4x SELECT dans une loop)

**Solution proposée**:
- JOIN pour combiner incidents + données de référence
- GROUP BY pour statistiques en une requête
- Cache Redis pour données de référence

---

## 📋 Phase 3: Qualité du Code (EN ATTENTE)

### 3.1 Refactorisation
- Extraire code dupliqué entre `home()` et `home_content_api()`
- Déplacer JavaScript inline vers fichiers externes
- Créer blueprints (auth, incidents, wiki, config)

### 3.2 Gestion d'Erreurs
- Remplacer `except:` par exceptions spécifiques
- Utiliser `app.logger` partout (plus de print())
- Ajouter try/except sur toutes les opérations DB

### 3.3 Configuration Docker
- Pinner versions exactes dans Dockerfile
- Augmenter workers Gunicorn (actuellement 1)
- Retirer wkhtmltopdf si non utilisé

### 3.4 Headers Sécurité Nginx
**Headers à ajouter**:
```nginx
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
add_header Referrer-Policy "strict-origin-when-cross-origin";
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()";
```

---

## ⚠️ ACTIONS CRITIQUES REQUISES AVANT DÉPLOIEMENT

### 1. Variables d'Environnement
```bash
# Créer .env avec:
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
POSTGRES_PASSWORD=$(python -c "import secrets; print(secrets.token_hex(16))")
```

### 2. Rebuild Docker
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 3. Appliquer les Indexes
```bash
docker exec -it dispatch_manager python apply_indexes.py
```

### 4. Réinitialiser les Mots de Passe
Tous les utilisateurs avec mots de passe en clair doivent être réinitialisés.

---

## 📊 Résumé des Améliorations

| Catégorie | Avant | Après | Impact |
|-----------|-------|-------|--------|
| **Sécurité CSRF** | ❌ Aucune protection | ✅ Flask-WTF | Critique |
| **Mots de passe** | ⚠️ Accepte texte clair | ✅ Hash obligatoire | Critique |
| **SECRET_KEY** | ⚠️ Optionnelle | ✅ Obligatoire (prod) | Critique |
| **Upload fichiers** | ⚠️ SVG acceptés | ✅ Validation magic bytes | Élevé |
| **SQL Injection** | ⚠️ LOWER() comparaisons | ✅ Comparaisons exactes | Élevé |
| **Performance DB** | ❌ Aucun index | ✅ 7 indexes | Élevé |

---

## 🔧 Commandes Utiles

### Vérifier les logs
```bash
docker logs dispatch_manager -f
```

### Tester la connexion DB
```bash
docker exec -it dispatch_postgres psql -U dispatch_user -d dispatch -c "\dt"
```

### Vérifier les indexes
```bash
docker exec -it dispatch_postgres psql -U dispatch_user -d dispatch -c "\di"
```

---

## 📝 Notes

- **Version Flask**: 2.3.3 (stable)
- **Version Flask-WTF**: 1.2.1 (nouvelle dépendance)
- **Base de données**: PostgreSQL 15-alpine
- **Nginx**: alpine

**Prochaine étape recommandée**: Tester l'application localement avant déploiement
