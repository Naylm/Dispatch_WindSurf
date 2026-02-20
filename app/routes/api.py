from flask import Blueprint, session, render_template, request, jsonify, send_file
from app.utils.db_config import get_db
from app.utils.references import get_reference_data
from app.utils.stability import app_cache
import hashlib
import json
import pandas as pd
from io import BytesIO
import pdfkit
from datetime import datetime

api_bp = Blueprint('api', __name__)

# To be implemented/moved from app.py:
# _can_access_incident helper
# helper for calculate_stats_kpis, calculate_stats_charts, calculate_stats_tables

# For now, just placeholder or basic impl
# I need to fetch the helpers from app.py effectively or rewrite them.
# Given constraints, I will assume we need to copy the logic.

def _get_current_tech_info(db):
    if "user" not in session or session.get("user_type") != "technicien":
        return None
    tech_info = db.execute(
        "SELECT id, prenom FROM techniciens WHERE username=%s AND actif=1",
        (session["user"],),
    ).fetchone()
    return tech_info

def _can_access_incident(db, incident):
    if not incident:
        return False
    if session.get("role") in ["admin", "superadmin"]:
        return True
    tech_info = _get_current_tech_info(db)
    if tech_info and incident.get("technicien_id") == tech_info.get("id"):
        return True
    if session.get("user_type") == "technicien":
        candidate_names = {session.get("user", "").strip().lower()}
        if tech_info and tech_info.get("prenom"):
            candidate_names.add(tech_info["prenom"].strip().lower())
        collab = (incident.get("collaborateur") or "").strip().lower()
        return collab in candidate_names
    return False

@api_bp.route("/incident/<int:id>")
def api_incident(id):
    if "user" not in session:
        return "", 403
    
    db = get_db()
    incident = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()
    
    if not incident:
        return "", 404
    
    if not _can_access_incident(db, incident):
        return "", 403
    
    ref_data = get_reference_data()
    priorites = ref_data['priorites']
    sites = ref_data['sites']
    statuts = ref_data['statuts']
    
    if session.get("role") in ["admin", "superadmin"]:
        techniciens_rows = db.execute("SELECT * FROM techniciens WHERE actif=1 ORDER BY ordre ASC, id ASC").fetchall()
        techniciens = [dict(row) for row in techniciens_rows]
    else:
        techniciens = []
    
    incidents = [incident]
    view_type = request.args.get('view', 'kanban')
    
    if view_type == 'grouped':
        template_name = "incident_card_grouped_partial.html"
    elif view_type == 'list':
        template_name = "incident_card_list_partial.html"
    elif view_type == 'tech':
        template_name = "incident_card_tech_partial.html"
    else:
        template_name = "incident_card_partial.html"
    
    return render_template(
        template_name,
        i=incident,
        incidents=incidents,
        user=session["user"],
        role=session["role"],
        techniciens=techniciens,
        priorites=priorites,
        sites=sites,
        statuts=statuts,
    )

# Add other API routes like stats/data here...
