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

@api_bp.route('/calendar_events')
def calendar_events():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
        
    db = get_db()
    
    # Base query for scheduled incidents (with joined tech info for avatars)
    query = """
        SELECT i.id, i.sujet, i.numero, i.site, i.urgence, i.etat, i.date_rdv, i.collaborateur, i.notes, t.photo_profil
        FROM incidents i
        LEFT JOIN techniciens t ON (
            -- We try to match by technicien_id or by name in collaborateur field
            i.technicien_id = t.id OR i.collaborateur ILIKE '%' || t.prenom || '%'
        )
        WHERE i.date_rdv IS NOT NULL
    """
    params = []
    
    # The user wants a collaborative calendar where everyone can see everything.
    # We only apply filtering if it's a "standard" user (not admin/tech) if that even exists, 
    # but based on requirements, technicians should see all scheduled interventions.
    pass
             
    incidents = db.execute(query, tuple(params)).fetchall()
    
    # Priority colors
    priority_colors = {
        'critique': '#dc3545',
        'haute': '#fd7e14',
        'moyenne': '#ffc107',
        'basse': '#198754'
    }
    
    events = []
    # 1. Process scheduled incidents
    for inc in incidents:
        start_date = inc['date_rdv']
        if isinstance(start_date, str):
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                continue
                
        if not start_date:
            continue
            
        color = priority_colors.get((inc['urgence'] or '').lower(), '#0d6efd')
        
        events.append({
            'id': str(inc['id']),
            'type': 'incident',
            'title': f"[{inc['site']}] {inc['sujet']} ({inc['numero']})",
            'start': start_date.isoformat(),
            'allDay': False, 
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'numero': inc['numero'],
                'site': inc['site'],
                'urgence': inc['urgence'],
                'etat': inc['etat'],
                'collaborateur': inc['collaborateur'],
                'description': inc['notes'],
                'photo_profil': inc['photo_profil'],
                'is_manual': False
            }
        })
        
    # 2. Process manual calendar events
    manual_query = """
        SELECT c.id, c.title, c.description, c.start_time, c.end_time, c.created_by, c.incident_id, t.prenom, t.photo_profil
        FROM calendar_events c
        LEFT JOIN techniciens t ON c.technicien_id = t.id
    """
    manual_events = db.execute(manual_query).fetchall()
    
    for ev in manual_events:
        start_date = ev['start_time']
        if isinstance(start_date, str):
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                continue
                
        end_date_iso = None
        if ev['end_time']:
            end_date = ev['end_time']
            if isinstance(end_date, str):
                try:
                    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    end_date_iso = end_date.isoformat()
                except ValueError:
                    pass
            else:
                end_date_iso = end_date.isoformat()
                
        events.append({
            'id': f"manual_{ev['id']}",
            'type': 'manual',
            'title': ev['title'],
            'start': start_date.isoformat(),
            'end': end_date_iso,
            'allDay': False,
            'backgroundColor': '#6f42c1', # Purple for manual events
            'borderColor': '#6f42c1',
            'extendedProps': {
                'description': ev['description'],
                'collaborateur': ev['prenom'] or ev['created_by'],
                'photo_profil': ev['photo_profil'],
                'incident_id': ev['incident_id'],
                'is_manual': True
            }
        })
        
    return jsonify(events)

@api_bp.route('/calendar_events/add', methods=['POST'])
def add_calendar_event():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    if not data or not data.get('title') or not data.get('start_time'):
        return jsonify({"error": "Missing required fields"}), 400
        
    db = get_db()
    
    technicien_id = None
    if session.get("role") not in ["admin", "superadmin"]:
        tech_info = _get_current_tech_info(db)
        if tech_info:
            technicien_id = tech_info["id"]
            
    incident_id = data.get('incident_id')
    incident_numero = data.get('incident_numero')
    
    if incident_numero and not incident_id:
        inc = db.execute("SELECT id FROM incidents WHERE numero=%s", (incident_numero.strip().upper(),)).fetchone()
        if inc:
            incident_id = inc['id']
            
    try:
        db.execute(
            """INSERT INTO calendar_events 
               (title, description, start_time, end_time, created_by, technicien_id, incident_id) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                data['title'],
                data.get('description', ''),
                data['start_time'],
                data.get('end_time'),
                session['user'],
                technicien_id,
                incident_id
            )
        )
        db.commit()
        return jsonify({"success": True}), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
    return jsonify({"error": "Unknown error"}), 500

@api_bp.route('/calendar_events/<int:event_id>', methods=['DELETE'])
def delete_calendar_event(event_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
        
    db = get_db()
    
    # Check permissions: admins/superadmins can delete anything, techs can only delete their own
    is_admin = session.get("role") in ["admin", "superadmin"]
    
    try:
        if is_admin:
            # Admins can delete any manual event
            res = db.execute("DELETE FROM calendar_events WHERE id = %s RETURNING id", (event_id,)).fetchone()
        else:
            # Technicians can only delete events they created
            tech_info = _get_current_tech_info(db)
            if not tech_info:
                return jsonify({"error": "Unauthorized"}), 403
            res = db.execute(
                "DELETE FROM calendar_events WHERE id = %s AND (created_by = %s OR technicien_id = %s) RETURNING id", 
                (event_id, session['user'], tech_info['id'])
            ).fetchone()
            
        if res:
            db.commit()
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Event not found or unauthorized to delete"}), 404
            
    except Exception as e:
        print(f"Error deleting event {event_id}: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/save-preferences', methods=['POST'])
def save_preferences():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    db = get_db()
    table = "techniciens" if session.get("user_type") == "technicien" else "users"
    
    try:
        # PostgreSQL supports JSONB directly. Passing a dict/list to execute 
        # with %s will usually work if the driver handles it, or we use json.dumps.
        # psycopg2 handles dicts if we use Json wrapper or if we pass string.
        # For simplicity and compatibility with our wrapper, we pass json string.
        db.execute(
            f"UPDATE {table} SET preferences = %s WHERE username = %s",
            (json.dumps(data), session["user"])
        )
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error saving preferences: {e}")
        return jsonify({"error": str(e)}), 500
