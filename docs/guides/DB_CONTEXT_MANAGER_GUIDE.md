# Guide d'utilisation du Context Manager pour les Connexions DB

## Problème Identifié

L'audit a révélé que **50+ routes** dans `app.py` ne ferment pas explicitement les connexions avec `db.close()`, causant des fuites de connexions qui peuvent mener à l'épuisement du pool PostgreSQL.

## Solution: Context Manager `get_db_context()`

Un context manager a été ajouté dans `db_config.py` pour gérer automatiquement la fermeture des connexions.

### Exemple d'utilisation

#### ❌ AVANT (avec fuites de connexion)
```python
@app.route("/example")
def example_route():
    db = get_db()
    results = db.execute("SELECT * FROM incidents").fetchall()
    # ⚠️ PROBLÈME: db.close() manquant!
    return render_template("example.html", results=results)
```

#### ✅ APRÈS (avec context manager)
```python
@app.route("/example")
def example_route():
    with get_db_context() as db:
        results = db.execute("SELECT * FROM incidents").fetchall()
    # ✓ Connexion fermée automatiquement
    return render_template("example.html", results=results)
```

### Avantages

1. **Fermeture automatique**: Même en cas d'exception
2. **Rollback automatique**: En cas d'erreur, rollback est appelé
3. **Code plus propre**: Moins de lignes, plus lisible
4. **Prévention des fuites**: Impossible d'oublier `db.close()`

## Routes à Corriger dans app.py

### Routes avec GET uniquement (lecture seule)

Ces routes peuvent utiliser le context manager directement :

```python
# Lignes 128-172: home()
# Lignes 174-222: home_content_api()
# Lignes 232-246: techniciens()
# Lignes 248-265: configuration()
# Lignes 267-287: priorites()
# Lignes 289-312: sites()
# Lignes 314-337: statuts()
# Et beaucoup d'autres...
```

**Pattern de conversion**:
```python
# AVANT
def some_route():
    db = get_db()
    data = db.execute("SELECT...").fetchall()
    return render_template("page.html", data=data)

# APRÈS
def some_route():
    with get_db_context() as db:
        data = db.execute("SELECT...").fetchall()
    return render_template("page.html", data=data)
```

### Routes avec POST/PUT/DELETE (modifications)

Pour les routes qui modifient des données, ajoutez explicitement le commit :

```python
# AVANT
@app.route("/add", methods=["POST"])
def add_item():
    db = get_db()
    db.execute("INSERT INTO table VALUES (?)", (value,))
    db.commit()
    return redirect(url_for("home"))

# APRÈS
@app.route("/add", methods=["POST"])
def add_item():
    with get_db_context() as db:
        db.execute("INSERT INTO table VALUES (?)", (value,))
        db.commit()
    return redirect(url_for("home"))
```

### Routes avec gestion d'erreurs

Le context manager gère déjà le rollback automatique :

```python
# AVANT
@app.route("/complex")
def complex_route():
    db = get_db()
    try:
        db.execute("UPDATE...")
        db.execute("INSERT...")
        db.commit()
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()
    return jsonify({"success": True})

# APRÈS (beaucoup plus simple!)
@app.route("/complex")
def complex_route():
    with get_db_context() as db:
        db.execute("UPDATE...")
        db.execute("INSERT...")
        db.commit()
    return jsonify({"success": True})
```

## Migration Progressive

Vu le nombre important de routes (50+), la migration peut se faire progressivement :

### Phase 1 (Critique) - Routes fréquemment appelées
- `/` (home)
- `/home_content` (home_content_api)
- `/login`
- `/add` (add_incident)
- `/update_etat/<id>`

### Phase 2 (Important) - Routes de configuration
- `/techniciens`
- `/configuration`
- `/priorites`
- `/sites`
- `/statuts`

### Phase 3 (Moyen) - Routes moins fréquentes
- Toutes les autres routes GET/POST

## Import Nécessaire

Dans `app.py`, remplacer:
```python
from db_config import get_db
```

Par:
```python
from db_config import get_db, get_db_context
```

## Monitoring

Pour détecter les fuites de connexions restantes:

```sql
-- Dans PostgreSQL
SELECT count(*) FROM pg_stat_activity
WHERE datname = 'dispatch';
```

Si ce nombre continue d'augmenter sans jamais diminuer, il reste des fuites à corriger.

## Note

Le context manager `get_db_context()` est maintenant disponible et prêt à l'emploi. Pour l'instant, `get_db()` fonctionne toujours, mais il est **fortement recommandé** de migrer vers `get_db_context()` pour éviter les fuites de connexions.
