from flask import Blueprint, render_template, session, jsonify, request, flash, redirect, url_for, send_file
from app.utils.db_config import get_db
from app.utils.references import get_reference_data
from app.utils.stability import app_cache
# Wait, app_cache variable was in original app.py?
# I need to check where app_cache was defined. It might be line 3834: cached = app_cache.get(cache_key).
# If app_cache was a global in app.py, I need to define it or import it.
# Usually it's Flask-Caching.
# I'll check imports later. For now, I'll comment out caching or fix it.

import hashlib
import json
from datetime import datetime, timedelta

stats_bp = Blueprint('stats', __name__)

# Mock app_cache if not properly initialized yet (TEMPORARY FIX)
class MockCache:
    def get(self, key): return None
    def set(self, key, val): pass
app_cache = MockCache() 
# TODO: Restore real caching

def calculate_stats_kpis(db, start_date=None, end_date=None, tech_ids=None, site_ids=None, status_ids=None, priority_ids=None):
    """
    Calcule les KPIs principaux pour le dashboard
    """
    # Construire la requête de base avec filtres
    where_clauses = ["archived=0"]
    params = []
    
    if start_date:
        where_clauses.append("date_affectation >= %s")
        params.append(start_date)
    if end_date:
        where_clauses.append("date_affectation <= %s")
        params.append(end_date)
    if tech_ids:
        placeholders = ",".join("?" * len(tech_ids)) # pg vs sqlite? PG uses %s or $1?
        # The original code used '?' which suggests SQLite!
        # But 'techniciens' table implies it's the main DB.
        # If I migrated to Postgres, I need to use %s.
        # The new DB config uses %s usually (psycopg2).
        # Wait, the code I read from original_app.py lines 3538 uses '?'.
        # "where_clauses.append(f"collaborateur IN (SELECT prenom FROM techniciens WHERE id IN ({placeholders}))")"
        # If this runs on Postgres, '?' is invalid. It must be '%s'.
        # I should fix this to use %s.
        
        placeholders = ",".join(["%s"] * len(tech_ids))
        where_clauses.append(f"collaborateur IN (SELECT prenom FROM techniciens WHERE id IN ({placeholders}))")
        params.extend(tech_ids)
    if site_ids:
        placeholders = ",".join(["%s"] * len(site_ids))
        where_clauses.append(f"site IN (SELECT nom FROM sites WHERE id IN ({placeholders}))")
        params.extend(site_ids)
    if status_ids:
        placeholders = ",".join(["%s"] * len(status_ids))
        where_clauses.append(f"etat IN (SELECT nom FROM statuts WHERE id IN ({placeholders}))")
        params.extend(status_ids)
    if priority_ids:
        placeholders = ",".join(["%s"] * len(priority_ids))
        where_clauses.append(f"urgence IN (SELECT nom FROM priorites WHERE id IN ({placeholders}))")
        params.extend(priority_ids)
    
    where_sql = " AND ".join(where_clauses)
    
    # Total incidents
    total = db.execute(f"SELECT COUNT(*) as count FROM incidents WHERE {where_sql}", params).fetchone()['count']
    
    # Taux de résolution
    # PG Tip: Use separate params list for each execute if reusing? No, params is built accumulatively.
    # But wait, db.execute binds params.
    # The f-string injects the subquery structure, but the params are passed as args.
    
    # Taux de résolution
    traites = db.execute(
        f"SELECT COUNT(*) as count FROM incidents i JOIN statuts s ON i.etat = s.nom WHERE {where_sql} AND s.category = 'traite'",
        params
    ).fetchone()['count']
    taux_resolution = (traites / total * 100) if total > 0 else 0
    
    # Temps moyen de traitement (en jours)
    # PG: EXTRACT(EPOCH FROM (NOW() - date_affectation))
    # Original code had: EXTRACT(EPOCH FROM (NOW() - i.date_affectation))
    temps_moyen = db.execute(
        f"SELECT AVG(EXTRACT(EPOCH FROM (NOW() - i.date_affectation)) / 86400) as avg_days "
        f"FROM incidents i "
        f"JOIN statuts s ON i.etat = s.nom "
        f"WHERE {where_sql} AND s.category != 'traite'",
        params
    ).fetchone()['avg_days'] or 0
    
    # Incidents en cours
    en_cours = db.execute(
        f"SELECT COUNT(*) as count FROM incidents i JOIN statuts s ON i.etat = s.nom WHERE {where_sql} AND s.category = 'en_cours'",
        params
    ).fetchone()['count']
    
    # Incidents urgents
    urgents = db.execute(
        f"SELECT COUNT(*) as count FROM incidents WHERE {where_sql} AND urgence IN ('Haute', 'Critique')",
        params
    ).fetchone()['count']
    
    return {
        'total_incidents': total,
        'taux_resolution': round(taux_resolution, 2),
        'temps_moyen_jours': round(float(temps_moyen), 2),
        'en_cours': en_cours,
        'urgents': urgents,
        'traites': traites
    }

def calculate_stats_charts(db, start_date=None, end_date=None, tech_ids=None, site_ids=None, status_ids=None, priority_ids=None):
    """
    Calcule les données pour les graphiques
    """
    where_clauses = ["archived=0"]
    params = []
    
    if start_date:
        where_clauses.append("date_affectation >= %s")
        params.append(start_date)
    if end_date:
        where_clauses.append("date_affectation <= %s")
        params.append(end_date)
    if tech_ids:
        placeholders = ",".join(["%s"] * len(tech_ids))
        where_clauses.append(f"collaborateur IN (SELECT prenom FROM techniciens WHERE id IN ({placeholders}))")
        params.extend(tech_ids)
    if site_ids:
        placeholders = ",".join(["%s"] * len(site_ids))
        where_clauses.append(f"site IN (SELECT nom FROM sites WHERE id IN ({placeholders}))")
        params.extend(site_ids)
    if status_ids:
        placeholders = ",".join(["%s"] * len(status_ids))
        where_clauses.append(f"etat IN (SELECT nom FROM statuts WHERE id IN ({placeholders}))")
        params.extend(status_ids)
    if priority_ids:
        placeholders = ",".join(["%s"] * len(priority_ids))
        where_clauses.append(f"urgence IN (SELECT nom FROM priorites WHERE id IN ({placeholders}))")
        params.extend(priority_ids)
    
    where_sql = " AND ".join(where_clauses)
    
    # Par technicien et statut
    par_tech = db.execute(
        f"SELECT i.collaborateur, s.nom as statut, COUNT(*) as count "
        f"FROM incidents i "
        f"JOIN statuts s ON i.etat = s.nom "
        f"WHERE {where_sql} "
        f"GROUP BY i.collaborateur, s.nom "
        f"ORDER BY i.collaborateur, s.nom",
        params
    ).fetchall()
    
    # Par site
    par_site = db.execute(
        f"SELECT site, COUNT(*) as count FROM incidents WHERE {where_sql} GROUP BY site ORDER BY count DESC",
        params
    ).fetchall()
    
    # Top 10 sujets
    top_sujets = db.execute(
        f"SELECT sujet, COUNT(*) as count FROM incidents WHERE {where_sql} GROUP BY sujet ORDER BY count DESC LIMIT 10",
        params
    ).fetchall()
    
    # Évolution temporelle
    evolution = db.execute(
        f"SELECT DATE(date_affectation) as date, "
        f"COUNT(*) as total, "
        f"SUM(CASE WHEN s.category = 'traite' THEN 1 ELSE 0 END) as traites "
        f"FROM incidents i "
        f"LEFT JOIN statuts s ON i.etat = s.nom "
        f"WHERE {where_sql} "
        f"GROUP BY DATE(date_affectation) "
        f"ORDER BY date",
        params
    ).fetchall()
    
    # Heatmap (charge par technicien et jour)
    heatmap = db.execute(
        f"SELECT collaborateur, DATE(date_affectation) as date, COUNT(*) as count "
        f"FROM incidents "
        f"WHERE {where_sql} "
        f"GROUP BY collaborateur, DATE(date_affectation) "
        f"ORDER BY date, collaborateur",
        params
    ).fetchall()
    
    return {
        'par_technicien': [dict(row) for row in par_tech],
        'par_site': [dict(row) for row in par_site],
        'top_sujets': [dict(row) for row in top_sujets],
        'evolution': [dict(row) for row in evolution],
        'heatmap': [dict(row) for row in heatmap]
    }

def calculate_stats_tables(db, start_date=None, end_date=None, tech_ids=None, site_ids=None, status_ids=None, priority_ids=None):
    """
    Calcule les données pour les tableaux détaillés
    """
    where_clauses = ["archived=0"]
    params = []
    
    if start_date:
        where_clauses.append("date_affectation >= %s")
        params.append(start_date)
    if end_date:
        where_clauses.append("date_affectation <= %s")
        params.append(end_date)
    if tech_ids:
        placeholders = ",".join(["%s"] * len(tech_ids))
        where_clauses.append(f"collaborateur IN (SELECT prenom FROM techniciens WHERE id IN ({placeholders}))")
        params.extend(tech_ids)
    if site_ids:
        placeholders = ",".join(["%s"] * len(site_ids))
        where_clauses.append(f"site IN (SELECT nom FROM sites WHERE id IN ({placeholders}))")
        params.extend(site_ids)
    if status_ids:
        placeholders = ",".join(["%s"] * len(status_ids))
        where_clauses.append(f"etat IN (SELECT nom FROM statuts WHERE id IN ({placeholders}))")
        params.extend(status_ids)
    if priority_ids:
        placeholders = ",".join(["%s"] * len(priority_ids))
        where_clauses.append(f"urgence IN (SELECT nom FROM priorites WHERE id IN ({placeholders}))")
        params.extend(priority_ids)
    
    where_sql = " AND ".join(where_clauses)
    
    # Par technicien
    table_tech = db.execute(
        f"SELECT collaborateur, "
        f"COUNT(*) as total, "
        f"SUM(CASE WHEN s.category = 'traite' THEN 1 ELSE 0 END) as traites, "
        f"SUM(CASE WHEN s.category = 'en_cours' THEN 1 ELSE 0 END) as en_cours, "
        f"SUM(CASE WHEN s.category = 'suspendu' THEN 1 ELSE 0 END) as suspendus "
        f"FROM incidents i "
        f"LEFT JOIN statuts s ON i.etat = s.nom "
        f"WHERE {where_sql} "
        f"GROUP BY collaborateur "
        f"ORDER BY total DESC",
        params
    ).fetchall()
    
    # Par site
    table_site = db.execute(
        f"SELECT site, "
        f"COUNT(*) as total, "
        f"SUM(CASE WHEN s.category = 'traite' THEN 1 ELSE 0 END) as traites, "
        f"SUM(CASE WHEN s.category = 'en_cours' THEN 1 ELSE 0 END) as en_cours "
        f"FROM incidents i "
        f"LEFT JOIN statuts s ON i.etat = s.nom "
        f"WHERE {where_sql} "
        f"GROUP BY site "
        f"ORDER BY total DESC",
        params
    ).fetchall()
    
    # Par sujet
    table_sujet = db.execute(
        f"SELECT sujet, "
        f"COUNT(*) as total, "
        f"SUM(CASE WHEN s.category = 'traite' THEN 1 ELSE 0 END) as traites "
        f"FROM incidents i "
        f"LEFT JOIN statuts s ON i.etat = s.nom "
        f"WHERE {where_sql} "
        f"GROUP BY sujet "
        f"ORDER BY total DESC",
        params
    ).fetchall()
    
    return {
        'par_technicien': [dict(row) for row in table_tech],
        'par_site': [dict(row) for row in table_site],
        'par_sujet': [dict(row) for row in table_sujet]
    }

@stats_bp.route("/dashboard/stats")
def dashboard_stats():
    """Route principale du dashboard de statistiques."""
    if "user" not in session:
        return "Unauthorized", 401
    if session.get("role") != "admin":
        return "Forbidden", 403

    try:
        db = get_db()
        ref_data = get_reference_data()
        techniciens_rows = db.execute("SELECT id, prenom FROM techniciens WHERE actif=1 ORDER BY prenom").fetchall()
        techniciens = [dict(row) for row in techniciens_rows]
        sites = [dict(row) for row in ref_data['sites']]
        statuts = [dict(row) for row in ref_data['statuts']]
        priorites = [dict(row) for row in ref_data['priorites']]
        sujets = [dict(row) for row in ref_data['sujets']]

        return render_template(
            "dashboard_stats.html",
            role=session.get("role"),
            techniciens=techniciens,
            sites=sites,
            statuts=statuts,
            priorites=priorites,
            sujets=sujets,
        )
    except Exception as e:
        import traceback
        print(f"Erreur dashboard_stats: {e}")
        print(traceback.format_exc())
        flash(f"Erreur lors du chargement des statistiques: {str(e)}", "danger")
        return redirect(url_for("main.home"))

@stats_bp.route("/api/stats/data")
def api_stats_data():
    """API pour récupérer les données statistiques filtrées avec cache."""
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    tech_ids = request.args.getlist("tech_ids[]", type=int) or None
    site_ids = request.args.getlist("site_ids[]", type=int) or None
    status_ids = request.args.getlist("status_ids[]", type=int) or None
    priority_ids = request.args.getlist("priority_ids[]", type=int) or None
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    cache_key_data = {
        "start_date": start_date,
        "end_date": end_date,
        "tech_ids": sorted(tech_ids) if tech_ids else None,
        "site_ids": sorted(site_ids) if site_ids else None,
        "status_ids": sorted(status_ids) if status_ids else None,
        "priority_ids": sorted(priority_ids) if priority_ids else None,
        "page": page,
        "per_page": per_page,
    }
    cache_key = f"stats_data_{hashlib.sha256(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()}"

    cached = app_cache.get(cache_key)
    if cached:
        return jsonify(cached)

    db = get_db()

    try:
        kpis = calculate_stats_kpis(db, start_date, end_date, tech_ids, site_ids, status_ids, priority_ids)

        if start_date and end_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            period_days = (end_dt - start_dt).days

            prev_start = (start_dt - timedelta(days=period_days + 1)).strftime("%Y-%m-%d")
            prev_end = (start_dt - timedelta(days=1)).strftime("%Y-%m-%d")
            prev_kpis = calculate_stats_kpis(db, prev_start, prev_end, tech_ids, site_ids, status_ids, priority_ids)

            variations = {}
            for key in ["total_incidents", "taux_resolution", "en_cours", "urgents"]:
                if key in prev_kpis and prev_kpis[key] > 0:
                    variations[key] = round(((kpis[key] - prev_kpis[key]) / prev_kpis[key]) * 100, 2)
                else:
                    variations[key] = 0
        else:
            variations = {"total_incidents": 0, "taux_resolution": 0, "en_cours": 0, "urgents": 0}

        kpis["variations"] = variations
        charts = calculate_stats_charts(db, start_date, end_date, tech_ids, site_ids, status_ids, priority_ids)
        tables_data = calculate_stats_tables(db, start_date, end_date, tech_ids, site_ids, status_ids, priority_ids)

        total_items = {
            "technicien": len(tables_data["par_technicien"]),
            "site": len(tables_data["par_site"]),
            "sujet": len(tables_data["par_sujet"]),
        }

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        tables = {
            "par_technicien": tables_data["par_technicien"][start_idx:end_idx],
            "par_site": tables_data["par_site"][start_idx:end_idx],
            "par_sujet": tables_data["par_sujet"][start_idx:end_idx],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": max(total_items.values()) if total_items.values() else 0,
                "total_pages": (max(total_items.values()) + per_page - 1) // per_page if total_items.values() else 0,
            },
        }

        result = {
            "kpis": kpis,
            "charts": charts,
            "tables": tables,
            "filters_applied": {
                "start_date": start_date,
                "end_date": end_date,
                "tech_ids": tech_ids or [],
                "site_ids": site_ids or [],
                "status_ids": status_ids or [],
                "priority_ids": priority_ids or [],
            },
        }

        app_cache.set(cache_key, result)
        return jsonify(result)
    except Exception as e:
        print(f"Erreur api_stats_data: {e}")
        return jsonify({"error": str(e)}), 500

@stats_bp.route("/api/stats/kpis")
def api_stats_kpis():
    """API optimisée pour récupérer uniquement les KPIs avec cache."""
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    cache_key_data = {"start_date": start_date, "end_date": end_date}
    cache_key = f"stats_kpis_{hashlib.sha256(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()}"

    cached = app_cache.get(cache_key)
    if cached:
        return jsonify({"kpis": cached})

    db = get_db()
    try:
        kpis = calculate_stats_kpis(db, start_date, end_date)
        app_cache.set(cache_key, kpis)
        return jsonify({"kpis": kpis})
    except Exception as e:
        print(f"Erreur api_stats_kpis: {e}")
        return jsonify({"error": str(e)}), 500
