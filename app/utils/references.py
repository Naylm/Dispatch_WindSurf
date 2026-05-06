from app.utils.db_config import get_db
from app.utils.stability import app_cache

def get_reference_data():
    """
    Récupère les données de référence (priorites, sites, statuts, sujets) avec cache
    Cache TTL: 5 minutes
    """
    cache_key = "reference_data"
    cached = app_cache.get(cache_key)

    if cached:
        return cached

    db = get_db()
    
    priorites_rows = db.execute(
        "SELECT id, nom, couleur, niveau, is_urgent FROM priorites ORDER BY niveau DESC"
    ).fetchall()
    sites_rows = db.execute(
        "SELECT id, nom, couleur FROM sites ORDER BY nom"
    ).fetchall()
    statuts_rows = db.execute(
        "SELECT id, nom, couleur, category, has_relances, has_rdv FROM statuts ORDER BY nom"
    ).fetchall()
    sujets_rows = db.execute(
        "SELECT id, nom FROM sujets ORDER BY nom"
    ).fetchall()
    techniciens_rows = db.execute(
        "SELECT id, prenom, nom, username, actif FROM techniciens WHERE actif=1 ORDER BY ordre, prenom"
    ).fetchall()

    priorites = [dict(row) for row in priorites_rows]
    sites = [dict(row) for row in sites_rows]
    statuts = [dict(row) for row in statuts_rows]
    sujets = [dict(row) for row in sujets_rows]
    techniciens = [dict(row) for row in techniciens_rows]

    statuts_by_category = {}
    for statut in statuts:
        category = statut.get("category") or "inconnu"
        statuts_by_category.setdefault(category, []).append(statut.get("nom"))

    data = {
        'priorites': priorites,
        'sites': sites,
        'statuts': statuts,
        'sujets': sujets,
        'techniciens': techniciens,
        'statuts_by_category': statuts_by_category
    }

    # Mettre en cache
    app_cache.set(cache_key, data)
    return data


def invalidate_reference_cache():
    """
    Invalide le cache des données de référence
    """
    app_cache.clear("reference_data")
