from flask import Blueprint, session, render_template, request, jsonify, send_file
from app.utils.db_config import get_db
from app.utils.references import get_reference_data
from app.utils.stability import app_cache
from app.sockets import active_sids
import hashlib
import json
import pandas as pd
from io import BytesIO
import pdfkit
from datetime import datetime
from app.utils.concurrency import (
    IdempotencyError,
    IdempotencyReplay,
    begin_idempotent_request,
    complete_idempotent_request,
    get_idempotency_key,
)

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

@api_bp.route('/incidents/active')
def get_active_incidents():
    """Récupère les incidents actifs (non clôturés) pour le dropdown du calendrier"""
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
        
    db = get_db()
    
    # Récupérer les incidents non clôturés, triés par date de création desc
    query = """
        SELECT i.id, i.numero, i.sujet, i.site, i.etat
        FROM incidents i
        WHERE i.etat NOT IN ('Clôturé', 'Cloturé', 'Résolu', 'Fermé')
        ORDER BY i.id DESC
        LIMIT 100
    """
    
    incidents = db.execute(query).fetchall()
    
    result = []
    for inc in incidents:
        result.append({
            'id': inc['id'],
            'numero': inc['numero'],
            'sujet': inc['sujet'],
            'site': inc['site'],
            'etat': inc['etat'],
            'label': f"[{inc['numero']}] {inc['sujet']} - {inc['site']}"
        })
    
    return jsonify(result)

@api_bp.route('/calendar_events')
def calendar_events():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
        
    db = get_db()
    
    # Base query for scheduled incidents (with joined tech info for avatars)
    query = """
        SELECT i.id, i.sujet, i.numero, i.site, i.urgence, i.priorite, i.etat, i.date_rdv, i.collaborateur, i.notes, t.photo_profil
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
    
    # Fonction pour générer une couleur HSL dynamique basée sur site + priorité
    def generate_event_color(site, urgence):
        """Génère une couleur HSL : hue = hash du site, saturation/lightness = priorité"""
        if not site:
            site = 'default'
        
        # Générer une teinte (hue) unique pour le site (0-360)
        site_hash = sum(ord(c) for c in site) % 360
        
        # Saturation et lightness selon l'urgence
        urgency_levels = {
            'critique': (90, 45),  # Très saturé, moyennement foncé
            'haute': (80, 50),     # Saturé, moyen
            'moyenne': (70, 55),   # Moyennement saturé, clair
            'basse': (60, 60)      # Moins saturé, plus clair
        }
        
        sat, light = urgency_levels.get((urgence or '').lower(), (75, 50))
        
        return f'hsl({site_hash}, {sat}%, {light}%)'
    
    # Couleurs HSL dynamiques stockées pour la légende
    site_colors_map = {}
    
    mine_only = request.args.get('mine_only') == '1'
    tech_info = _get_current_tech_info(db)
    current_prenom = tech_info['prenom'] if tech_info else None
    current_tech_id = tech_info['id'] if tech_info else None
    current_user = session.get('user')
    
    events = []
    # 1. Process scheduled incidents
    for inc in incidents:
        if mine_only:
            is_mine = False
            collab = (inc['collaborateur'] or '').lower()
            if current_prenom and current_prenom.lower() in collab:
                is_mine = True
            elif current_user and current_user.lower() in collab:
                is_mine = True
                
            if not is_mine:
                continue
                
        start_date = inc['date_rdv']
        if isinstance(start_date, str):
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                continue
                
        if not start_date:
            continue
            
        # Couleur HSL dynamique basée sur site + urgence
        color = generate_event_color(inc['site'], inc['urgence'])
        site_colors_map[inc['site']] = color
        
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
                'site_color': color,
                'urgence': inc['urgence'],
                'priorite': inc['priorite'],
                'etat': inc['etat'],
                'collaborateur': inc['collaborateur'],
                'description': inc['notes'],
                'photo_profil': inc['photo_profil'],
                'is_manual': False
            }
        })
        
    # 2. Process manual calendar events
    manual_query = """
        SELECT c.id, c.title, c.description, c.start_time, c.end_time, c.created_by, c.incident_id, c.technicien_id, 
               t.prenom, t.photo_profil,
               i.numero as incident_numero, i.sujet as incident_sujet, i.site as incident_site, i.etat as incident_etat
        FROM calendar_events c
        LEFT JOIN techniciens t ON c.technicien_id = t.id
        LEFT JOIN incidents i ON c.incident_id = i.id
    """
    manual_events = db.execute(manual_query).fetchall()
    
    for ev in manual_events:
        if mine_only:
            is_mine = False
            if ev['created_by'] == current_user:
                is_mine = True
            elif current_tech_id and ev.get('technicien_id') == current_tech_id:
                is_mine = True
            elif current_prenom and current_prenom.lower() in (ev['prenom'] or '').lower():
                is_mine = True
            elif current_user and current_user.lower() in (ev['prenom'] or '').lower():
                is_mine = True
                
            if not is_mine:
                continue
                
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
        
        # Construire le titre avec les infos de l'incident si lié
        title = ev['title']
        if ev['incident_numero']:
            title = f"🔗 [{ev['incident_numero']}] {ev['title']}"
                
        events.append({
            'id': f"manual_{ev['id']}",
            'type': 'manual',
            'title': title,
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
                'incident_numero': ev['incident_numero'],
                'incident_sujet': ev['incident_sujet'],
                'incident_site': ev['incident_site'],
                'incident_etat': ev['incident_etat'],
                'is_manual': True
            }
        })
        
    return jsonify({
        'events': events,
        'site_colors': site_colors_map
    })

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
        result = db.execute(
            """INSERT INTO calendar_events 
               (title, description, start_time, end_time, created_by, technicien_id, incident_id) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
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
        event_id = result.fetchone()['id']
        db.commit()
        
        # Émettre événement Socket.IO pour notifier tous les clients
        from app import socketio
        socketio.emit('calendar_event_added', {
            'id': event_id,
            'title': data['title'],
            'start_time': data['start_time'],
            'end_time': data.get('end_time'),
            'created_by': session['user'],
            'technicien_id': technicien_id,
            'incident_id': incident_id
        })
        
        return jsonify({"success": True, "id": event_id}), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
    return jsonify({"error": "Erreur interne du serveur"}), 500

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
            # Users can delete events they created, or events assigned to them
            tech_info = _get_current_tech_info(db)
            tech_id = tech_info['id'] if tech_info else -1
            
            res = db.execute(
                "DELETE FROM calendar_events WHERE id = %s AND (created_by = %s OR technicien_id = %s) RETURNING id", 
                (event_id, session['user'], tech_id)
            ).fetchone()
            
        if res:
            db.commit()
            # Émettre événement Socket.IO pour notifier tous les clients
            from app import socketio
            socketio.emit('calendar_event_deleted', {
                'id': event_id,
                'deleted_by': session['user']
            })
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Event not found or unauthorized to delete"}), 404
            
    except Exception as e:
        print(f"Error deleting event {event_id}: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


# ========== CALENDAR EVENT UPDATE (PUT) ==========

@api_bp.route('/calendar_events/<int:event_id>', methods=['PUT'])
def update_calendar_event(event_id):
    """Mettre à jour un événement calendrier (édition + drag & drop)"""
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    db = get_db()
    
    # Check permissions
    is_admin = session.get("role") in ["admin", "superadmin"]
    
    try:
        # Vérifier que l'événement existe et appartient à l'utilisateur (si non admin)
        if is_admin:
            event = db.execute(
                "SELECT * FROM calendar_events WHERE id = %s", (event_id,)
            ).fetchone()
        else:
            tech_info = _get_current_tech_info(db)
            tech_id = tech_info['id'] if tech_info else -1
            event = db.execute(
                "SELECT * FROM calendar_events WHERE id = %s AND (created_by = %s OR technicien_id = %s)",
                (event_id, session['user'], tech_id)
            ).fetchone()
            
        if not event:
            return jsonify({"error": "Event not found or unauthorized"}), 404
        
        # Construire la requête de mise à jour dynamiquement
        update_fields = []
        values = []
        
        if 'title' in data:
            update_fields.append("title = %s")
            values.append(data['title'])
        if 'description' in data:
            update_fields.append("description = %s")
            values.append(data['description'])
        if 'start_time' in data:
            update_fields.append("start_time = %s")
            values.append(data['start_time'])
        if 'end_time' in data:
            update_fields.append("end_time = %s")
            values.append(data['end_time'])
            
        if not update_fields:
            return jsonify({"error": "No fields to update"}), 400
            
        values.append(event_id)
        query = f"UPDATE calendar_events SET {', '.join(update_fields)} WHERE id = %s"
        
        db.execute(query, values)
        db.commit()
        
        # Émettre événement Socket.IO pour notifier tous les clients
        from app import socketio
        socketio.emit('calendar_event_updated', {
            'id': event_id,
            'title': data.get('title', event['title']),
            'start_time': data.get('start_time', event['start_time']),
            'end_time': data.get('end_time', event['end_time']),
            'updated_by': session['user']
        })
        
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Error updating event {event_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Erreur interne du serveur"}), 500

@api_bp.route('/save-preferences', methods=['POST'])
def save_preferences():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    db = get_db()
    table = "techniciens" if session.get("user_type") == "technicien" else "users"
    if table not in {"users", "techniciens"}: return jsonify({"error": "Invalid table"}), 400
    
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
        return jsonify({"error": "Erreur interne du serveur"}), 500

@api_bp.route('/runner/submit-score', methods=['POST'])
def submit_runner_score():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    if not data or 'score' not in data:
        return jsonify({"error": "Missing score"}), 400
        
    db = get_db()
    try:
        score = int(data['score'])
        if score < 0 or score > 10000000:
            return jsonify({"error": "Score invalide"}), 400

        idem_key = get_idempotency_key(request, data)
        idem_state = begin_idempotent_request(
            db,
            scope="arcade.runner.submit",
            key=idem_key,
            actor=session.get("user", "unknown"),
            payload={"score": score},
        )
        if isinstance(idem_state, IdempotencyReplay):
            return jsonify(idem_state.body), idem_state.status_code

        db.execute(
            "INSERT INTO dispatch_runner_scores (username, score) VALUES (%s, %s)",
            (session["user"], score)
        )
        response = {"success": True}
        complete_idempotent_request(db, idem_state, status_code=201, body=response)
        db.commit()
        return jsonify(response), 201
    except IdempotencyError as e:
        db.rollback()
        return jsonify({"error": "Erreur interne du serveur"}), e.status_code
    except ValueError:
        db.rollback()
        return jsonify({"error": "Score invalide"}), 400
    except Exception as e:
        print(f"Error submitting runner score: {e}")
        db.rollback()
        return jsonify({"error": "Erreur interne du serveur"}), 500

@api_bp.route('/runner/leaderboard')
def get_runner_leaderboard():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
        
    db = get_db()
    try:
        # Get top 10 scores
        scores = db.execute("""
            SELECT username, MAX(score) as score 
            FROM dispatch_runner_scores 
            GROUP BY username 
            ORDER BY score DESC 
            LIMIT 10
        """).fetchall()
        return jsonify([dict(s) for s in scores])
    except Exception as e:
        print(f"Error fetching runner leaderboard: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


# ========== GENERIC ARCADE LEADERBOARD ==========
VALID_GAMES = ['flappy', 'invaders', 'breakout', 'snake', 'memory', 'runner']

@api_bp.route('/arcade/submit-score', methods=['POST'])
def submit_arcade_score():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    if not data or 'score' not in data or 'game' not in data:
        return jsonify({"error": "Missing score or game"}), 400
    game = data['game']
    if game not in VALID_GAMES:
        return jsonify({"error": "Invalid game"}), 400
    db = get_db()
    try:
        score = int(data['score'])
        level = int(data.get('level', 1))
        if score < 0 or score > 10000000:
            return jsonify({"error": "Score invalide"}), 400
        if level < 1 or level > 10000:
            return jsonify({"error": "Niveau invalide"}), 400

        idem_key = get_idempotency_key(request, data)
        idem_state = begin_idempotent_request(
            db,
            scope="arcade.generic.submit",
            key=idem_key,
            actor=session.get("user", "unknown"),
            payload={"game": game, "score": score, "level": level},
        )
        if isinstance(idem_state, IdempotencyReplay):
            return jsonify(idem_state.body), idem_state.status_code

        db.execute(
            "INSERT INTO arcade_scores (game_name, username, score, level) VALUES (%s, %s, %s, %s)",
            (game, session["user"], score, level)
        )
        response = {"success": True}
        complete_idempotent_request(db, idem_state, status_code=201, body=response)
        db.commit()
        return jsonify(response), 201
    except IdempotencyError as e:
        db.rollback()
        return jsonify({"error": "Erreur interne du serveur"}), e.status_code
    except ValueError:
        db.rollback()
        return jsonify({"error": "Score ou niveau invalide"}), 400
    except Exception as e:
        print(f"Error submitting arcade score: {e}")
        db.rollback()
        return jsonify({"error": "Erreur interne du serveur"}), 500

@api_bp.route('/arcade/leaderboard/<game>')
def get_arcade_leaderboard(game):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
    if game not in VALID_GAMES:
        return jsonify({"error": "Invalid game"}), 400
    db = get_db()
    
    # For memory, lower score (attempts) is better
    score_agg = "MIN(score)" if game == "memory" else "MAX(score)"
    order_dir = "ASC" if game == "memory" else "DESC"
    
    try:
        query = f"""
            SELECT username, {score_agg} as score, MAX(level) as level
            FROM arcade_scores
            WHERE game_name = %s
            GROUP BY username
            ORDER BY score {order_dir}
            LIMIT 10
        """
        scores = db.execute(query, (game,)).fetchall()
        return jsonify([dict(s) for s in scores])
    except Exception as e:
        print(f"Error fetching arcade leaderboard: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


# ============================================
# STATS API - Pour le dashboard statistiques
# ============================================

@api_bp.route('/stats/data')
def api_stats_data():
    """API endpoint pour les données de statistiques (JSON)"""
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Seuls les admins peuvent voir les stats
    if session.get("role") not in ("admin", "superadmin"):
        return jsonify({"error": "Accès administrateur requis"}), 403
    
    db = get_db()
    
    # Récupérer les filtres
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    tech_ids = request.args.getlist('tech_ids[]', type=int)
    site_ids = request.args.getlist('site_ids[]', type=int)
    status_ids = request.args.getlist('status_ids[]', type=int)
    priority_ids = request.args.getlist('priority_ids[]', type=int)
    
    try:
        # Import des fonctions de stats
        from app.routes.stats import calculate_stats_kpis, calculate_stats_charts, calculate_stats_tables
        
        kpis = calculate_stats_kpis(db, start_date=start_date, end_date=end_date, 
                                    tech_ids=tech_ids, site_ids=site_ids, 
                                    status_ids=status_ids, priority_ids=priority_ids)
        charts = calculate_stats_charts(db, start_date=start_date, end_date=end_date)
        tables = calculate_stats_tables(db, start_date=start_date, end_date=end_date)
        
        return jsonify({
            'kpis': kpis,
            'charts': charts,
            'tables': tables,
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'tech_ids': tech_ids,
                'site_ids': site_ids,
                'status_ids': status_ids,
                'priority_ids': priority_ids
            }
        })
    except Exception as e:
        print(f"Error in api_stats_data: {e}")
        return jsonify({"error": str(e)}), 500


# ========== ACTIVE CONNECTIONS API - Fallback HTTP ==========
# ============================================================

@api_bp.route('/active_connections')
def api_active_connections():
    """API endpoint pour le nombre d'utilisateurs connectés (fallback HTTP)"""
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Récupérer la liste des utilisateurs connectés depuis active_sids
        connected_users = list(set([u for u in active_sids.values() if u and u != "anonymous"]))
        count = len(active_sids)
        
        return jsonify({
            "count": count,
            "users": connected_users
        })
    except Exception as e:
        print(f"Error in api_active_connections: {e}")
        return jsonify({"error": str(e)}), 500

