from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from werkzeug.security import generate_password_hash
from app.utils.db_config import get_db
from app.utils.references import invalidate_reference_cache
from app.utils.incidents import _log_historique, update_relance_schedule, _emit_incident_event, _emit_bulk_refresh
from app.utils.references import get_reference_data, invalidate_reference_cache
from app.utils.notifications import emit_new_assignment_notification, emit_reassignment_notification
from app import socketio
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session or session.get("role") not in ("admin", "superadmin"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

# ---------- TECHNICIENS VUE PRINCIPALE ----------
@admin_bp.route("/techniciens")
@admin_required
def techniciens():
    db = get_db()
    techniciens = db.execute("SELECT * FROM techniciens ORDER BY ordre ASC, id ASC").fetchall()
    return render_template("techniciens.html", techniciens=techniciens)

@admin_bp.route("/add_technicien", methods=["POST"])
@admin_required
def add_technicien():
    nom = request.form.get("nom", "").strip()
    prenom = request.form.get("prenom", "").strip()
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    dect_number = request.form.get("dect_number", "").strip()
    role = request.form.get("role", "technicien")

    if not all([nom, prenom, username, email]):
        flash("Tous les champs sont obligatoires", "error")
        return redirect(url_for("admin.techniciens"))

    hashed_password = generate_password_hash("0000")
    db = get_db()
    try:
        existing = db.execute("SELECT id FROM techniciens WHERE username=%s", (username,)).fetchone()
        if existing:
            flash("Ce nom d'utilisateur existe déjà", "error")
            return redirect(url_for("admin.techniciens"))
        
        existing_email = db.execute("SELECT id FROM techniciens WHERE email=%s", (email,)).fetchone()
        if existing_email:
            flash("Cet email est déjà utilisé", "error")
            return redirect(url_for("admin.techniciens"))
        
        max_ordre_result = db.execute("SELECT COALESCE(MAX(ordre), 0) as max_ordre FROM techniciens").fetchone()
        new_ordre = (max_ordre_result['max_ordre'] if max_ordre_result else 0) + 1

        db.execute("""
            INSERT INTO techniciens (nom, prenom, username, email, dect_number, password, role, actif, ordre, force_password_reset)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s, 1)
        """, (nom, prenom, username, email, dect_number, hashed_password, role, new_ordre))
        db.commit()
        flash(f"Technicien {prenom} {nom} ajouté avec succès! Mot de passe par défaut: 0000", "success")
    except Exception as e:
        db.rollback()
        flash(f"Erreur lors de l'ajout : {str(e)}", "error")
    finally:
        db.close()
    return redirect(url_for("admin.techniciens"))

# ---------- GESTION TECHNICIENS (Edit, Toggle, Delete, Order) ----------

@admin_bp.route("/technicien/edit/<int:id>", methods=["POST"])
@admin_required
def edit_technicien(id):
    nom = request.form.get("nom", "").strip()
    prenom = request.form.get("prenom", "").strip()
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    dect_number = request.form.get("dect_number", "").strip()
    role = request.form.get("role", "technicien")
    new_pass = request.form.get("password", "").strip()

    if not all([nom, prenom, username, email]):
        flash("Les champs nom, prénom, username et email sont obligatoires", "error")
        return redirect(url_for("admin.techniciens"))

    if new_pass and len(new_pass) < 8:
        flash("Le mot de passe doit contenir au moins 8 caractères", "error")
        return redirect(url_for("admin.techniciens"))

    db = get_db()
    try:
        existing = db.execute("SELECT id FROM techniciens WHERE username=%s AND id!=%s", (username, id)).fetchone()
        if existing:
            flash("Ce nom d'utilisateur existe déjà", "error")
            return redirect(url_for("admin.techniciens"))

        existing_email = db.execute("SELECT id FROM techniciens WHERE email=%s AND id!=%s", (email, id)).fetchone()
        if existing_email:
            flash("Cet email est déjà utilisé", "error")
            return redirect(url_for("admin.techniciens"))

        if new_pass:
            hashed_password = generate_password_hash(new_pass)
            db.execute("""
                UPDATE techniciens
                SET nom=%s, prenom=%s, username=%s, email=%s, dect_number=%s, role=%s, password=%s
                WHERE id=%s
            """, (nom, prenom, username, email, dect_number, role, hashed_password, id))
        else:
            db.execute("""
                UPDATE techniciens
                SET nom=%s, prenom=%s, username=%s, email=%s, dect_number=%s, role=%s
                WHERE id=%s
            """, (nom, prenom, username, email, dect_number, role, id))

        db.commit()
        flash(f"Technicien {prenom} {nom} modifié avec succès!", "success")
    except Exception as e:
        db.rollback()
        flash(f"Erreur lors de la modification : {str(e)}", "error")
    finally:
        db.close()

    return redirect(url_for("admin.techniciens"))

@admin_bp.route("/technicien/incidents/<int:id>")
@admin_required
def technicien_incidents(id):
    db = get_db()
    tech = db.execute("SELECT prenom FROM techniciens WHERE id=%s", (id,)).fetchone()
    if not tech:
        return jsonify({"error": "Not found"}), 404

    incidents = db.execute(
        "SELECT * FROM incidents WHERE technicien_id=%s", (id,)
    ).fetchall()
    autres_techs = db.execute(
        "SELECT id, prenom FROM techniciens WHERE id != %s", (id,)
    ).fetchall()

    return jsonify(
        {
            "incidents": [dict(i) for i in incidents],
            "autres_techs": [dict(t) for t in autres_techs],
            "tech_prenom": tech["prenom"],
        }
    )

@admin_bp.route("/technicien/transfer_delete/<int:id>", methods=["POST"])
@admin_required
def transfer_and_delete_technicien(id):
    db = get_db()
    tech = db.execute("SELECT prenom FROM techniciens WHERE id=%s", (id,)).fetchone()
    if not tech:
        return jsonify({"status": "error", "message": "Tech introuvable"}), 404

    try:
        # Ré-affecter chaque incident sélectionné
        for key, value in request.form.items():
            if key.startswith("incident_"):
                incident_id = int(key.split("_")[1])
                nouveau_collab = value
                new_tech = db.execute(
                    "SELECT id FROM techniciens WHERE prenom=%s AND actif=1",
                    (nouveau_collab,),
                ).fetchone()
                if not new_tech:
                    db.rollback()
                    return jsonify({"status": "error", "message": f"Technicien cible invalide: {nouveau_collab}"}), 400
                db.execute(
                    "UPDATE incidents SET collaborateur=%s, technicien_id=%s WHERE id=%s",
                    (nouveau_collab, new_tech["id"], incident_id),
                )

        # Puis supprimer le technicien
        db.execute("DELETE FROM techniciens WHERE id=%s", (id,))
        db.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

@admin_bp.route("/technicien/delete/<int:id>", methods=["POST"])
@admin_required
def delete_technicien(id):
    db = get_db()
    db.execute("DELETE FROM techniciens WHERE id=%s", (id,))
    db.commit()
    db.close()
    return redirect(url_for("admin.techniciens"))

@admin_bp.route("/toggle_technicien/<int:id>", methods=["POST"])
@admin_required
def toggle_technicien(id):
    """Active ou désactive un technicien"""
    db = get_db()
    technicien = db.execute("SELECT actif FROM techniciens WHERE id=%s", (id,)).fetchone()
    
    if technicien:
        new_state = 0 if technicien['actif'] == 1 else 1
        db.execute("UPDATE techniciens SET actif=%s WHERE id=%s", (new_state, id))
        db.commit()
        flash(f"Technicien {'activé' if new_state == 1 else 'désactivé'} avec succès!", "success")
    
    db.close()
    return redirect(url_for("admin.techniciens"))

@admin_bp.route("/techniciens/update_order", methods=["POST"])
@admin_required
def update_techniciens_order():
    """Met à jour l'ordre d'affichage des techniciens"""
    data = request.get_json()
    if not data or "order" not in data:
        return jsonify({"error": "Données invalides"}), 400
    
    db = get_db()
    try:
        for index, tech_id in enumerate(data["order"], start=1):
            db.execute("UPDATE techniciens SET ordre=%s WHERE id=%s", (index, tech_id))
        db.commit()
        return jsonify({"success": True, "message": "Ordre mis à jour avec succès"})
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Erreur lors de la mise à jour de l'ordre: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@admin_bp.route("/force_password_reset", methods=["POST"])
@admin_required
def force_password_reset():
    """Force la réinitialisation du mot de passe pour un utilisateur"""
    username = request.form.get("username")
    user_type = request.form.get("user_type")
    
    if not username:
        return jsonify({"success": False, "error": "Nom d'utilisateur manquant"}), 400
        
    db = get_db()
    try:
        if user_type == "user":
            db.execute("UPDATE users SET force_password_reset=1 WHERE username=%s", (username,))
        else:
            db.execute("UPDATE techniciens SET force_password_reset=1 WHERE username=%s", (username,))
            
        db.commit()
        return jsonify({"success": True, "message": f"Réinitialisation forcée pour {username}"})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


# ---------- CONFIGURATION ----------
@admin_bp.route("/configuration")
@admin_required
def configuration():
    db = get_db()
    sujets = db.execute("SELECT * FROM sujets ORDER BY nom").fetchall()
    priorites = db.execute("SELECT * FROM priorites ORDER BY niveau").fetchall()
    sites = db.execute("SELECT * FROM sites ORDER BY nom").fetchall()
    statuts = db.execute("SELECT * FROM statuts ORDER BY nom").fetchall()
    
    unknown_statuts = db.execute("""
        SELECT etat, COUNT(*) as count
        FROM incidents
        WHERE archived=0 AND etat NOT IN (SELECT nom FROM statuts)
        GROUP BY etat
        ORDER BY count DESC
    """).fetchall()
    statuts_without_category = db.execute(
        "SELECT nom FROM statuts WHERE category IS NULL OR category = ''"
    ).fetchall()

    return render_template("configuration.html",
                         sujets=sujets,
                         priorites=priorites,
                         sites=sites,
                         statuts=statuts,
                         unknown_statuts=unknown_statuts,
                         statuts_without_category=statuts_without_category)

@admin_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_incident():
    db = get_db()
    techniciens = db.execute("SELECT * FROM techniciens").fetchall()
    sujets = db.execute("SELECT * FROM sujets ORDER BY nom").fetchall()
    priorites = db.execute("SELECT * FROM priorites ORDER BY niveau").fetchall()
    sites = db.execute("SELECT * FROM sites ORDER BY nom").fetchall()

    if request.method == "POST":
        numero = request.form["numero"]
        site = request.form["site"]
        sujet = request.form["sujet"]
        urgence = request.form["urgence"]
        technicien_id_str = request.form.get("technicien_id")
        date_aff = request.form["date_affectation"]
        note_dispatch = request.form.get("note_dispatch", "")
        localisation = request.form.get("localisation", "")

        technicien_id = int(technicien_id_str) if technicien_id_str else None

        collab_prenom = "Non affecté"
        if technicien_id:
            tech = db.execute("SELECT prenom FROM techniciens WHERE id=%s", (technicien_id,)).fetchone()
            if tech:
                collab_prenom = tech['prenom']

        sql = """
          INSERT INTO incidents (
            numero, site, sujet, urgence,
            collaborateur, technicien_id, etat, note_dispatch,
            valide, date_affectation, archived, localisation
          ) VALUES (%s, %s, %s, %s, %s, %s, 'Affecté', %s, 0, %s, 0, %s)
          RETURNING id
        """
        result = db.execute(sql, (numero, site, sujet, urgence, collab_prenom, technicien_id, note_dispatch, date_aff, localisation))
        incident_id = result.fetchone()["id"]
        update_relance_schedule(db, incident_id, new_etat="Affecté", new_urgence=urgence, changed_by=session["user"])
        db.commit()

        incident_data = {
            "id": incident_id,
            "numero": numero,
            "site": site,
            "sujet": sujet,
            "urgence": urgence,
            "note_dispatch": note_dispatch,
            "localisation": localisation
        }
        emit_new_assignment_notification(socketio, incident_data, collab_prenom)
        _emit_incident_event("incident_update", incident_id, db=db, technician_names=[collab_prenom], action="add")
        _emit_bulk_refresh("incident_added", technician_names=[collab_prenom], incident_id=incident_id)
        
        return redirect(url_for("main.home"))

    current = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "add_incident.html", current_date=current, techniciens=techniciens,
        sujets=sujets, priorites=priorites, sites=sites
    )

@admin_bp.route("/delete_incident/<int:id>", methods=["POST"])
@admin_required
def delete_incident(id):
    db = get_db()
    incident = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()
    if not incident:
        return jsonify({"error": "Incident introuvable"}), 404

    _log_historique(db, id, "suppression", f"Ticket {incident['numero']}", "SUPPRIMÉ", session["user"])
    
    try:
        db.execute("DELETE FROM incidents WHERE id=%s", (id,))
        db.commit()
        _emit_incident_event("incident_deleted", id, technician_names=[incident["collaborateur"]], action="delete")
        _emit_bulk_refresh("incident_deleted", technician_names=[incident["collaborateur"]], incident_id=id)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "ok", "success": True}), 200
        
        flash("Incident supprimé", "success")
        return redirect(url_for("main.home"))
    except Exception as e:
        db.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": str(e)}), 500
        flash("Erreur lors de la suppression", "error")
        return redirect(url_for("main.home"))
    finally:
        db.close()

# ----------- DRAG & DROP INCIDENTS (DASHBOARD ADMIN) -----------
@admin_bp.route("/incidents/assign", methods=["POST"])
@admin_required
def assign_incident():
    incident_id = request.form.get("id")
    new_collab = request.form.get("collaborateur")
    if not incident_id or not new_collab:
        return jsonify({"status": "error", "message": "Paramètres manquants"}), 400

    db = None
    try:
        db = get_db()
        # Récupérer les données de l'incident AVANT modification
        incident = db.execute(
            """
            SELECT id, numero, site, sujet, urgence, note_dispatch, localisation,
                   collaborateur, technicien_id
            FROM incidents
            WHERE id=%s
            """,
            (incident_id,),
        ).fetchone()
        if not incident:
            return jsonify({"status": "error", "message": "Incident introuvable"}), 404

        old_collab = incident["collaborateur"]

        tech_row = db.execute(
            "SELECT id, prenom FROM techniciens WHERE prenom=%s AND actif=1",
            (new_collab,),
        ).fetchone()
        if not tech_row:
            return jsonify({"status": "error", "message": "Technicien introuvable"}), 404

        db.execute(
            "UPDATE incidents SET collaborateur=%s, technicien_id=%s WHERE id=%s",
            (new_collab, tech_row["id"], incident_id),
        )
        db.commit()

        # Préparer les données pour la notification
        incident_data = {
            "id": int(incident_id),
            "numero": incident["numero"],
            "site": incident["site"],
            "sujet": incident["sujet"],
            "urgence": incident["urgence"],
            "note_dispatch": incident.get("note_dispatch", ""),
            "localisation": incident.get("localisation", ""),
        }

        # Émettre la notification de réaffectation
        emit_reassignment_notification(socketio, incident_data, old_collab, new_collab)
        
        # Surcharger l'événement pour mettre à jour les cartes (tech + admin)
        _emit_incident_event("new_assignment", incident_id, db=db, technician_names=[old_collab, new_collab])
        
        return jsonify({"status": "ok", "message": "Réaffectation réussie"})
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur assignation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if db: db.close()

# ---------- CONFIGURATION SUB-ROUTES ----------

@admin_bp.route("/configuration/sujet/add", methods=["POST"])
@admin_required
def add_sujet():
    nom = request.form["nom"].strip()
    db = get_db()
    db.execute("INSERT INTO sujets (nom) VALUES (%s)", (nom,))
    db.commit()
    invalidate_reference_cache()
    flash("Sujet ajouté", "success")
    return redirect(url_for("admin.configuration"))

@admin_bp.route("/configuration/sujet/edit", methods=["POST"])
@admin_required
def edit_sujet():
    id = request.form["id"].strip()
    nom = request.form["nom"].strip()
    db = get_db()
    db.execute("UPDATE sujets SET nom=%s WHERE id=%s", (nom, id))
    db.commit()
    invalidate_reference_cache()
    flash("Sujet modifié", "success")
    return redirect(url_for("admin.configuration"))

@admin_bp.route("/configuration/sujet/delete/<int:id>", methods=["POST"])
@admin_required
def delete_sujet(id):
    db = get_db()
    db.execute("DELETE FROM sujets WHERE id=%s", (id,))
    db.commit()
    invalidate_reference_cache()
    flash("Sujet supprimé", "success")
    return redirect(url_for("admin.configuration"))

@admin_bp.route("/configuration/priorite/add", methods=["POST"])
@admin_required
def add_priorite():
    nom = request.form["nom"].strip()
    couleur = request.form["couleur"].strip()
    niveau = request.form["niveau"].strip()
    db = get_db()
    db.execute("INSERT INTO priorites (nom, couleur, niveau) VALUES (%s, %s, %s)", (nom, couleur, niveau))
    db.commit()
    invalidate_reference_cache()
    flash("Priorité ajoutée", "success")
    return redirect(url_for("admin.configuration"))

@admin_bp.route("/configuration/priorite/edit", methods=["POST"])
@admin_required
def edit_priorite():
    id = request.form["id"].strip()
    nom = request.form["nom"].strip()
    couleur = request.form["couleur"].strip()
    niveau = request.form["niveau"].strip()
    db = get_db()
    db.execute("UPDATE priorites SET nom=%s, couleur=%s, niveau=%s WHERE id=%s", (nom, couleur, niveau, id))
    db.commit()
    invalidate_reference_cache()
    flash("Priorité modifiée", "success")
    return redirect(url_for("admin.configuration"))

@admin_bp.route("/configuration/priorite/delete/<int:id>", methods=["POST"])
@admin_required
def delete_priorite(id):
    db = get_db()
    db.execute("DELETE FROM priorites WHERE id=%s", (id,))
    db.commit()
    invalidate_reference_cache()
    flash("Priorité supprimée", "success")
    return redirect(url_for("admin.configuration"))

@admin_bp.route("/configuration/site/add", methods=["POST"])
@admin_required
def add_site():
    nom = request.form["nom"].strip()
    couleur = request.form["couleur"].strip()
    db = get_db()
    db.execute("INSERT INTO sites (nom, couleur) VALUES (%s, %s)", (nom, couleur))
    db.commit()
    invalidate_reference_cache()
    flash("Site ajouté", "success")
    return redirect(url_for("admin.configuration"))

@admin_bp.route("/configuration/site/edit", methods=["POST"])
@admin_required
def edit_site():
    id = request.form["id"].strip()
    nom = request.form["nom"].strip()
    couleur = request.form["couleur"].strip()
    db = get_db()
    db.execute("UPDATE sites SET nom=%s, couleur=%s WHERE id=%s", (nom, couleur, id))
    db.commit()
    invalidate_reference_cache()
    flash("Site modifié", "success")
    return redirect(url_for("admin.configuration"))

@admin_bp.route("/configuration/site/delete/<int:id>", methods=["POST"])
@admin_required
def delete_site(id):
    db = get_db()
    db.execute("DELETE FROM sites WHERE id=%s", (id,))
    db.commit()
    invalidate_reference_cache()
    flash("Site supprimé", "success")
    return redirect(url_for("admin.configuration"))

@admin_bp.route("/configuration/statut/add", methods=["POST"])
@admin_required
def add_statut():
    nom = request.form["nom"].strip()
    couleur = request.form["couleur"].strip()
    category = request.form["category"].strip()
    has_relances = request.form.get("has_relances") == "1"
    has_rdv = request.form.get("has_rdv") == "1"
    db = get_db()
    db.execute(
        "INSERT INTO statuts (nom, couleur, category, has_relances, has_rdv) VALUES (%s, %s, %s, %s, %s)",
        (nom, couleur, category, has_relances, has_rdv)
    )
    db.commit()
    invalidate_reference_cache()
    flash("Statut ajouté", "success")
    return redirect(url_for("admin.configuration"))

@admin_bp.route("/configuration/statut/edit", methods=["POST"])
@admin_required
def edit_statut():
    id = request.form["id"].strip()
    nom = request.form["nom"].strip()
    couleur = request.form["couleur"].strip()
    category = request.form["category"].strip()
    has_relances = request.form.get("has_relances") == "1"
    has_rdv = request.form.get("has_rdv") == "1"
    db = get_db()
    db.execute(
        "UPDATE statuts SET nom=%s, couleur=%s, category=%s, has_relances=%s, has_rdv=%s WHERE id=%s",
        (nom, couleur, category, has_relances, has_rdv, id)
    )
    db.commit()
    invalidate_reference_cache()
    flash("Statut modifié", "success")
    return redirect(url_for("admin.configuration"))

@admin_bp.route("/configuration/statut/delete/<int:id>", methods=["POST"])
@admin_required
def delete_statut(id):
    db = get_db()
    db.execute("DELETE FROM statuts WHERE id=%s", (id,))
    db.commit()
    invalidate_reference_cache()
    flash("Statut supprimé", "success")
    return redirect(url_for("admin.configuration"))
