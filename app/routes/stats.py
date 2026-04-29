from flask import Blueprint, render_template, session, jsonify, request, flash, redirect, url_for, send_file
from app.utils.db_config import get_db
from app.utils.references import get_reference_data
import hashlib
import json
from datetime import datetime, timedelta
from functools import wraps

stats_bp = Blueprint('stats', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session or session.get("role") not in ("admin", "superadmin"):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return jsonify({"status": "error", "message": "Accès administrateur requis"}), 403
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def calculate_stats_kpis(db, start_date=None, end_date=None, tech_ids=None, site_ids=None, status_ids=None, priority_ids=None):
    try:
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
        
        total = db.execute(f"SELECT COUNT(*) as count FROM incidents WHERE {where_sql}", params).fetchone()['count'] or 0
        traites = db.execute(f"SELECT COUNT(*) as count FROM incidents i JOIN statuts s ON i.etat = s.nom WHERE {where_sql} AND s.category = 'traite'", params).fetchone()['count'] or 0
        en_cours = db.execute(f"SELECT COUNT(*) as count FROM incidents i JOIN statuts s ON i.etat = s.nom WHERE {where_sql} AND s.category = 'en_cours'", params).fetchone()['count'] or 0
        urgents = db.execute(f"SELECT COUNT(*) as count FROM incidents WHERE {where_sql} AND urgence IN ('Haute', 'Critique')", params).fetchone()['count'] or 0
        
        taux_resolution = (traites / total * 100) if total > 0 else 0
        res_tm = db.execute(f"SELECT AVG(EXTRACT(EPOCH FROM (NOW() - i.date_affectation)) / 86400) as avg_days FROM incidents i JOIN statuts s ON i.etat = s.nom WHERE {where_sql} AND s.category != 'traite' AND i.date_affectation IS NOT NULL", params).fetchone()
        temps_moyen = res_tm['avg_days'] if res_tm and res_tm['avg_days'] is not None else 0
        
        return {
            'total_incidents': total,
            'taux_resolution': round(float(taux_resolution), 1),
            'temps_moyen_jours': round(float(temps_moyen), 1),
            'en_cours': en_cours,
            'urgents': urgents,
            'traites': traites
        }
    except Exception as e:
        print(f"Error in calculate_stats_kpis: {e}")
        return {'total_incidents': 0, 'taux_resolution': 0, 'temps_moyen_jours': 0, 'en_cours': 0, 'urgents': 0, 'traites': 0}

def calculate_stats_charts(db, **filters):
    # Simplified reconstruction
    return {
        'par_site': [],
        'evolution': [],
        'repartition_statut': []
    }

def calculate_stats_tables(db, **filters):
    return {
        'techniciens': [],
        'sites': []
    }

@stats_bp.route("/dashboard_stats")
@admin_required
def dashboard_stats():
    db = get_db()
    # Get filter params
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    kpis = calculate_stats_kpis(db, start_date=start_date, end_date=end_date)
    charts = calculate_stats_charts(db, start_date=start_date, end_date=end_date)
    tables = calculate_stats_tables(db, start_date=start_date, end_date=end_date)
    
    ref_data = get_reference_data()
    
    return render_template(
        "dashboard_stats.html",
        kpis=kpis,
        charts=charts,
        tables=tables,
        techniciens=ref_data['techniciens'],
        sites=ref_data['sites'],
        statuts=ref_data['statuts'],
        priorites=ref_data['priorites']
    )

@stats_bp.route("/api/stats/export")
@admin_required
def export_stats():
    # Placeholder for export logic
    return jsonify({"status": "not_implemented"})
