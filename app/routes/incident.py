from flask import Blueprint, render_template, session, jsonify, request, flash, redirect, url_for, current_app
from app.utils.db_config import get_db
from app.utils.references import get_reference_data
from app.utils.incidents import (
    update_relance_schedule, 
    _emit_incident_event, 
    _emit_bulk_refresh, 
    _log_historique,
    _can_access_incident,
    _is_api_or_ajax_request,
    _get_current_tech_info
)
from app.utils.notifications import (
    emit_status_change_notification,
    emit_urgent_update_notification,
    is_urgent
)
from app.utils.contrast import get_contrast_color
from app.utils.concurrency import (
    ConcurrencyConflictError,
    IdempotencyError,
    IdempotencyReplay,
    begin_idempotent_request,
    complete_idempotent_request,
    get_idempotency_key,
    optimistic_incident_update,
    parse_expected_version,
)
from app import socketio
from datetime import datetime

incident_bp = Blueprint('incident', __name__)


def _json_conflict_response(exc: ConcurrencyConflictError):
    payload = {
        "status": "conflict",
        "error": str(exc),
        "message": "Conflit: ce ticket a été modifié par quelqu'un d'autre. Rechargez la carte puis recommencez.",
    }
    if exc.current_version is not None:
        payload["current_version"] = exc.current_version
    return jsonify(payload), 409

@incident_bp.route("/<int:id>")
def incident_detail_api(id):
   # Alias for api_incident from original app?
   # In original app, it was @app.route("/api/incident/<int:id>") line 1052
   # I should restore that one too.
   # I'll put it here.
   return api_incident(id)

@incident_bp.route("/api/<int:id>")
def api_incident(id):
    """API pour récupérer le HTML d'un seul incident (pour rechargement partiel)"""
    if "user" not in session:
        return "", 403
    
    db = get_db()
    
    # Récupérer l'incident
    incident = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()
    
    if not incident:
        return "", 404
    
    if not _can_access_incident(db, incident):
        return "", 403
    
    # Récupérer les données de référence
    ref_data = get_reference_data()
    priorites = ref_data['priorites']
    sites = ref_data['sites']
    statuts = ref_data['statuts']
    
    # Récupérer les techniciens (pour le select)
    if session.get("role") in ["admin", "superadmin"]:
        techniciens = db.execute("SELECT * FROM techniciens WHERE actif=1 ORDER BY ordre ASC, id ASC").fetchall()
    else:
        techniciens = []
    
    # Convertir l'incident en liste pour le template (compatibilité)
    incidents = [incident]
    
    # Détecter le type de vue demandé (par défaut kanban/li)
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

@incident_bp.route("/edit_incident/<int:id>", methods=["GET", "POST"])
def edit_incident(id):
    if "user" not in session or session.get("role") not in ["admin", "superadmin"]:
        return redirect(url_for("auth.login"))

    db = get_db()
    incident = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()
    if not incident:
        flash("Incident introuvable", "danger")
        return redirect(url_for("main.home"))

    if request.method == "POST":
        try:
            numero = request.form["numero"].strip()
            site = request.form["site"].strip()
            sujet = request.form["sujet"].strip()
            urgence = request.form["urgence"].strip()
            technicien_id = int(request.form["technicien_id"])
            etat = request.form["etat"].strip()
            notes = request.form.get("notes", "").strip()
            note_dispatch = request.form.get("note_dispatch", "").strip()
            date_aff = request.form["date_affectation"]
            localisation = (request.form.get("localisation") or "").strip()
            
            # Get collaborateur from technicien_id to keep them in sync
            collaborateur = "Non affecté"
            if technicien_id:
                tech = db.execute("SELECT prenom FROM techniciens WHERE id=%s", (technicien_id,)).fetchone()
                if tech:
                    collaborateur = tech['prenom']
            
            payload = request.form.to_dict()
            expected_version = parse_expected_version(request, payload)
            
            set_clause = "numero=%s, site=%s, sujet=%s, urgence=%s, technicien_id=%s, collaborateur=%s, etat=%s, notes=%s, note_dispatch=%s, date_affectation=%s, localisation=%s"
            params = (numero, site, sujet, urgence, technicien_id, collaborateur, etat, notes, note_dispatch, date_aff, localisation)

            new_version = optimistic_incident_update(
                db, 
                incident_id=id, 
                expected_version=expected_version, 
                set_clause=set_clause, 
                params=params
            )
            
            # Log changes if any
            fields = ["numero", "site", "sujet", "urgence", "technicien_id", "collaborateur", "etat", "notes", "note_dispatch", "date_affectation", "localisation"]
            for f_name in fields:
                old_val = incident[f_name]
                new_val = request.form.get(f_name)
                if f_name == "technicien_id":
                    new_val = int(new_val)
                if str(old_val) != str(new_val):
                    _log_historique(db, id, f_name, str(old_val), str(new_val), session["user"])

            db.commit()
            _emit_incident_event("incident_update", id, db=db, action="edit", version=new_version)
            flash("Incident modifié avec succès", "success")
            return redirect(url_for("main.home"))
            
        except ConcurrencyConflictError:
            db.rollback()
            flash("Conflit de mise à jour: un autre technicien a modifié ce ticket. Rechargez puis recommencez.", "warning")
            return redirect(url_for("incident.edit_incident", id=id))
        except Exception as e:
            db.rollback()
            flash(f"Erreur de modification: {e}", "warning")
            return redirect(url_for("incident.edit_incident", id=id))

    techniciens = db.execute("SELECT * FROM techniciens WHERE actif=1 ORDER BY ordre ASC, id ASC").fetchall()
    ref_data = get_reference_data()
    return render_template(
        "edit_incident.html", 
        incident=incident, 
        techniciens=techniciens,
        sujets=ref_data['sujets'],
        priorites=ref_data['priorites'],
        sites=ref_data['sites'],
        statuts=ref_data['statuts']
    )

@incident_bp.route("/edit_note/<int:id>", methods=["GET", "POST"])
def edit_note(id):
    if "user" not in session:
        return redirect(url_for("auth.login"))

    db = get_db()
    inc = db.execute("SELECT id, numero, notes, localisation, technicien_id, collaborateur, version FROM incidents WHERE id=%s", (id,)).fetchone()
    if not inc:
        flash("Incident introuvable", "danger")
        return redirect(url_for("main.home"))
    
    if session.get("role") not in ["admin", "superadmin"]:
        tech = db.execute("SELECT id FROM techniciens WHERE username=%s",
                         (session["user"],)).fetchone()
        if not tech or inc["technicien_id"] != tech["id"]:
            return redirect(url_for("main.home"))

    if request.method == "POST":
        note = (request.form.get("note") or "").strip()
        localisation = (request.form.get("localisation") or "").strip()
        
        try:
            expected_version = parse_expected_version(request)
            if expected_version is None:
                flash("Version attendue manquante. Rechargez la page.", "warning")
                return redirect(url_for("incident.edit_note", id=id))
        except ValueError as exc:
            flash(str(exc), "warning")
            return redirect(url_for("incident.edit_note", id=id))

        changes_made = inc["notes"] != note or inc["localisation"] != (localisation or None)
        
        if changes_made:
            if inc["notes"] != note:
                _log_historique(db, id, "notes", inc["notes"] or "", note, session["user"])
            if inc["localisation"] != localisation:
                _log_historique(db, id, "localisation", inc["localisation"] or "", localisation, session["user"])
            
            try:
                new_version = optimistic_incident_update(
                    db,
                    incident_id=id,
                    expected_version=expected_version,
                    set_clause="notes=%s, localisation=%s",
                    params=(note, localisation),
                )
                db.commit()
                _emit_incident_event(
                    "incident_update",
                    id,
                    db=db,
                    technician_names=[inc.get("collaborateur")],
                    action="note",
                    version=new_version,
                )
                flash("Note mise à jour avec succès", "success")
            except ConcurrencyConflictError:
                db.rollback()
                flash("Conflit de mise à jour: un autre technicien a modifié ce ticket. Rechargez la page.", "warning")
                return redirect(url_for("incident.edit_note", id=id))
            except Exception as e:
                db.rollback()
                flash(f"Erreur lors de la mise à jour : {e}", "danger")
                return redirect(url_for("incident.edit_note", id=id))

        return redirect(url_for("main.home"))

    return render_template("edit_note.html", id=id, numero=inc["numero"], current_note=inc["notes"], current_localisation=inc["localisation"] or "", version=inc["version"])

@incident_bp.route("/edit_note_inline/<int:id>", methods=["POST"])
def edit_note_inline(id):
    if "user" not in session:
        return jsonify({"error": "Non authentifié"}), 403

    db = get_db()
    inc = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()

    if not inc:
        return jsonify({"error": "Incident introuvable"}), 404

    # Allow if admin/superadmin OR if assigned tech
    if session["role"] not in ["admin", "superadmin"]:
        tech = db.execute("SELECT id FROM techniciens WHERE username=%s",
                         (session["user"],)).fetchone()
        if not tech or inc["technicien_id"] != tech["id"]:
            return jsonify({"error": "Permission refusée"}), 403

    payload = request.get_json(silent=True) or {}
    new_note = (payload.get("note") or "").strip()

    try:
        expected_version = parse_expected_version(request, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if expected_version is None:
        return jsonify({"error": "Version attendue manquante"}), 400

    actor = session.get("user", "unknown")
    idem_key = None
    token = None
    try:
        idem_key = get_idempotency_key(request, payload)
        idem_state = begin_idempotent_request(
            db,
            scope="incident.edit_note_inline",
            key=idem_key,
            actor=actor,
            payload={"id": id, "note": new_note, "expected_version": expected_version},
            incident_id=id,
        )
        if isinstance(idem_state, IdempotencyReplay):
            return jsonify(idem_state.body), idem_state.status_code
        token = idem_state
    except IdempotencyError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

    if inc["notes"] != new_note:
        _log_historique(db, id, "notes", inc["notes"] or "", new_note, session["user"])
        try:
            new_version = optimistic_incident_update(
                db,
                incident_id=id,
                expected_version=expected_version,
                set_clause="notes=%s",
                params=(new_note,),
            )
        except ConcurrencyConflictError as exc:
            db.rollback()
            return _json_conflict_response(exc)
        response = {"success": True, "note": new_note, "version": new_version}
        complete_idempotent_request(db, token, status_code=200, body=response)
        db.commit()
        _emit_incident_event(
            "incident_update",
            id,
            db=db,
            technician_names=[inc.get("collaborateur")],
            action="note_edit",
            version=new_version,
        )
        return jsonify(response)

    response = {"success": True, "note": new_note, "unchanged": True, "version": inc.get("version")}
    complete_idempotent_request(db, token, status_code=200, body=response)
    db.commit()
    return jsonify(response)

@incident_bp.route("/edit_note_dispatch/<int:id>", methods=["POST"])
def edit_note_dispatch(id):
    if "user" not in session or session["role"] not in ["admin", "superadmin"]:
        return jsonify({"error": "Permission refusée - Admin/Superadmin uniquement"}), 403

    db = get_db()
    inc = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()
    if not inc:
        return jsonify({"error": "Incident introuvable"}), 404

    payload = request.get_json(silent=True) or {}
    new_note_dispatch = (payload.get("note_dispatch") or "").strip()
    old_note_dispatch = inc["note_dispatch"] if inc["note_dispatch"] else ""

    try:
        expected_version = parse_expected_version(request, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if expected_version is None:
        return jsonify({"error": "Version attendue manquante"}), 400

    token = None
    try:
        idem_key = get_idempotency_key(request, payload)
        idem_state = begin_idempotent_request(
            db,
            scope="incident.edit_note_dispatch",
            key=idem_key,
            actor=session.get("user", "unknown"),
            payload={"id": id, "note_dispatch": new_note_dispatch, "expected_version": expected_version},
            incident_id=id,
        )
        if isinstance(idem_state, IdempotencyReplay):
            return jsonify(idem_state.body), idem_state.status_code
        token = idem_state
    except IdempotencyError as exc:
        return jsonify({"error": str(exc)}), exc.status_code
    
    if old_note_dispatch != new_note_dispatch:
        _log_historique(db, id, "note_dispatch", old_note_dispatch, new_note_dispatch, session["user"])
        try:
            new_version = optimistic_incident_update(
                db,
                incident_id=id,
                expected_version=expected_version,
                set_clause="note_dispatch=%s",
                params=(new_note_dispatch,),
            )
        except ConcurrencyConflictError as exc:
            db.rollback()
            return _json_conflict_response(exc)
        response = {"success": True, "note_dispatch": new_note_dispatch, "version": new_version}
        complete_idempotent_request(db, token, status_code=200, body=response)
        db.commit()
        _emit_incident_event(
            "incident_update",
            id,
            db=db,
            technician_names=[inc.get("collaborateur")],
            action="note_dispatch_edit",
            version=new_version,
        )
        return jsonify(response)

    response = {"success": True, "note_dispatch": new_note_dispatch, "unchanged": True, "version": inc.get("version")}
    complete_idempotent_request(db, token, status_code=200, body=response)
    db.commit()
    return jsonify(response)

@incident_bp.route("/api/<int:id>/relances", methods=["POST"])
def update_relances(id):
    if "user" not in session:
        return jsonify({"error": "Non authentifie"}), 401

    db = get_db()
    inc = db.execute("SELECT id, technicien_id, collaborateur, relance_mail, relance_1, relance_2, relance_cloture, version FROM incidents WHERE id=%s", (id,)).fetchone()

    if not inc:
        return jsonify({"error": "Incident non trouve"}), 404

    if not _can_access_incident(db, inc):
        return jsonify({"error": "Acces non autorise"}), 403

    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}

    try:
        expected_version = parse_expected_version(request, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if expected_version is None:
        return jsonify({"error": "Version attendue manquante"}), 400

    token = None
    try:
        idem_key = get_idempotency_key(request, data)
        idem_state = begin_idempotent_request(
            db,
            scope="incident.update_relances",
            key=idem_key,
            actor=session.get("user", "unknown"),
            payload={
                "id": id,
                "expected_version": expected_version,
                "relance_mail": data.get("relance_mail"),
                "relance_1": data.get("relance_1"),
                "relance_2": data.get("relance_2"),
                "relance_cloture": data.get("relance_cloture"),
            },
            incident_id=id,
        )
        if isinstance(idem_state, IdempotencyReplay):
            return jsonify(idem_state.body), idem_state.status_code
        token = idem_state
    except IdempotencyError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

    relance_mail = data.get("relance_mail") in [True, "true", "1", 1]
    relance_1 = data.get("relance_1") in [True, "true", "1", 1]
    relance_2 = data.get("relance_2") in [True, "true", "1", 1]
    relance_cloture = data.get("relance_cloture") in [True, "true", "1", 1]

    if (
        inc.get("relance_mail") == relance_mail
        and inc.get("relance_1") == relance_1
        and inc.get("relance_2") == relance_2
        and inc.get("relance_cloture") == relance_cloture
    ):
        response_body = {
            "success": True,
            "unchanged": True,
            "relance_mail": relance_mail,
            "relance_1": relance_1,
            "relance_2": relance_2,
            "relance_cloture": relance_cloture,
            "version": inc.get("version"),
        }
        complete_idempotent_request(db, token, status_code=200, body=response_body)
        db.commit()
        return jsonify(response_body)

    try:
        new_version = optimistic_incident_update(
            db,
            incident_id=id,
            expected_version=expected_version,
            set_clause="relance_mail=%s, relance_1=%s, relance_2=%s, relance_cloture=%s",
            params=(relance_mail, relance_1, relance_2, relance_cloture),
        )
    except ConcurrencyConflictError as exc:
        db.rollback()
        return _json_conflict_response(exc)

    if inc.get("relance_mail") != relance_mail:
        _log_historique(db, id, "relance_mail", str(inc.get("relance_mail")), str(relance_mail), session["user"])
    if inc.get("relance_1") != relance_1:
        _log_historique(db, id, "relance_1", str(inc.get("relance_1")), str(relance_1), session["user"])
    if inc.get("relance_2") != relance_2:
        _log_historique(db, id, "relance_2", str(inc.get("relance_2")), str(relance_2), session["user"])
    if inc.get("relance_cloture") != relance_cloture:
        _log_historique(db, id, "relance_cloture", str(inc.get("relance_cloture")), str(relance_cloture), session["user"])
    
    response_body = {
        "success": True,
        "relance_mail": relance_mail,
        "relance_1": relance_1,
        "relance_2": relance_2,
        "relance_cloture": relance_cloture,
        "version": new_version,
    }
    complete_idempotent_request(db, token, status_code=200, body=response_body)
    db.commit()

    event_payload = _emit_incident_event(
        "incident_relances_changed",
        id,
        db=db,
        technician_names=[inc.get("collaborateur")],
        relance_mail=relance_mail,
        relance_1=relance_1,
        relance_2=relance_2,
        relance_cloture=relance_cloture,
        version=new_version,
    )

    response_body["version"] = event_payload.get("version", new_version)
    return jsonify(response_body)

@incident_bp.route("/api/<int:id>/rdv", methods=["POST"])
def update_rdv(id):
    if "user" not in session:
        return jsonify({"error": "Non authentifie"}), 401

    db = get_db()
    inc = db.execute("SELECT id, technicien_id, collaborateur, date_rdv, version FROM incidents WHERE id=%s", (id,)).fetchone()
    if not inc or not _can_access_incident(db, inc):
        return jsonify({"error": "Acces non autorise"}), 403

    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}

    try:
        expected_version = parse_expected_version(request, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if expected_version is None:
        return jsonify({"error": "Version attendue manquante"}), 400

    token = None
    try:
        idem_key = get_idempotency_key(request, data)
        idem_state = begin_idempotent_request(
            db,
            scope="incident.update_rdv",
            key=idem_key,
            actor=session.get("user", "unknown"),
            payload={"id": id, "expected_version": expected_version, "date_rdv": data.get("date_rdv")},
            incident_id=id,
        )
        if isinstance(idem_state, IdempotencyReplay):
            return jsonify(idem_state.body), idem_state.status_code
        token = idem_state
    except IdempotencyError as exc:
        return jsonify({"error": str(exc)}), exc.status_code
    date_rdv_str = (data.get("date_rdv") or "").strip()

    date_rdv = None
    if date_rdv_str:
        try:
            date_rdv = datetime.fromisoformat(date_rdv_str.replace("Z", "+00:00"))
        except ValueError:
             return jsonify({"error": "Format de date invalide"}), 400

    old_rdv = inc.get("date_rdv")
    if old_rdv == date_rdv:
        response_body = {
            "success": True,
            "unchanged": True,
            "date_rdv": date_rdv.isoformat() if date_rdv else None,
            "type": "rdv",
            "version": inc.get("version"),
        }
        complete_idempotent_request(db, token, status_code=200, body=response_body)
        db.commit()
        return jsonify(response_body)

    try:
        new_version = optimistic_incident_update(
            db,
            incident_id=id,
            expected_version=expected_version,
            set_clause="date_rdv=%s",
            params=(date_rdv,),
        )
    except ConcurrencyConflictError as exc:
        db.rollback()
        return _json_conflict_response(exc)
    
    # Log handled by logic? Original had explicit log.
    old_rdv_str = old_rdv.strftime("%d/%m/%Y %H:%M") if old_rdv else "Non defini"
    new_rdv_str = date_rdv.strftime("%d/%m/%Y %H:%M") if date_rdv else "Non defini"
    if old_rdv_str != new_rdv_str:
        _log_historique(db, id, "date_rdv", old_rdv_str, new_rdv_str, session["user"])

    response_body = {
        "success": True,
        "date_rdv": date_rdv.isoformat() if date_rdv else None,
        "type": "rdv",
        "version": new_version,
    }
    complete_idempotent_request(db, token, status_code=200, body=response_body)
    db.commit()

    event_payload = _emit_incident_event(
        "incident_rdv_changed",
        id,
        db=db,
        technician_names=[inc.get("collaborateur")],
        date_rdv=date_rdv.isoformat() if date_rdv else None,
        date_rdv_formatted=date_rdv.strftime("%d/%m/%Y %H:%M") if date_rdv else None,
        version=new_version,
    )

    response_body["version"] = event_payload.get("version", new_version)
    return jsonify(response_body)

@incident_bp.route("/update_etat/<int:id>", methods=["POST"])
def update_etat(id):
    if "user" not in session:
        return jsonify({"error": "Non authentifie"}), 401

    db = get_db()
    try:
        inc = db.execute("SELECT id, numero, etat, urgence, collaborateur, technicien_id, version FROM incidents WHERE id=%s", (id,)).fetchone()
        if not inc or not _can_access_incident(db, inc):
             return jsonify({"error": "Acces non autorise"}), 403

        new = request.form.get("etat", "").strip()
        if not new:
             return jsonify({"error": "Statut manquant"}), 400

        expected_version = parse_expected_version(request)
        if expected_version is None:
            return jsonify({"error": "Version attendue manquante"}), 400

        # Validation serveur: statut doit exister en base
        statut_exists = db.execute("SELECT 1 FROM statuts WHERE nom=%s", (new,)).fetchone()
        if not statut_exists:
            return jsonify({"error": "Statut invalide"}), 400

        idem_key = get_idempotency_key(request)
        idem_state = begin_idempotent_request(
            db,
            scope="incident.update_etat",
            key=idem_key,
            actor=session.get("user", "unknown"),
            payload={"id": id, "etat": new, "expected_version": expected_version},
            incident_id=id,
        )
        if isinstance(idem_state, IdempotencyReplay):
            return jsonify(idem_state.body), idem_state.status_code
        token = idem_state

        old_status = inc["etat"]
        new_version = inc.get("version")
        if old_status != new:
            new_version = optimistic_incident_update(
                db,
                incident_id=id,
                expected_version=expected_version,
                set_clause="etat=%s",
                params=(new,),
            )
            _log_historique(db, id, "etat", old_status, new, session["user"])

            changed_by = session["user"]
            tech_info = _get_current_tech_info(db)
            if tech_info: changed_by = tech_info["prenom"]

            emit_status_change_notification(socketio, id, inc["numero"], old_status, new, inc["collaborateur"], changed_by)

            if is_urgent(inc["urgence"]) and new in ["Suspendu", "En intervention"]:
                emit_urgent_update_notification(socketio, id, inc["numero"], f"Statut change: {new}", inc["collaborateur"])

            update_relance_schedule(db, id, new_etat=new, new_urgence=inc["urgence"], changed_by=session["user"])

        statut_info = db.execute("SELECT couleur FROM statuts WHERE nom=%s", (new,)).fetchone()
        statut_couleur = statut_info["couleur"] if statut_info else "#6c757d"
        statut_text_color = get_contrast_color(statut_couleur)

        response_body = {
            "status": "ok",
            "new_etat": new,
            "couleur": statut_couleur,
            "text_color": statut_text_color,
            "version": new_version,
        }
        complete_idempotent_request(db, token, status_code=200, body=response_body)
        db.commit()

        event_data = _emit_incident_event(
            "incident_etat_changed",
            id,
            db=db,
            technician_names=[inc.get("collaborateur")],
            action="etat",
            new_etat=new,
            couleur=statut_couleur,
            text_color=statut_text_color,
            version=new_version,
        )
        
        response_body["version"] = event_data.get("version", new_version)
        return jsonify(response_body)

    except ConcurrencyConflictError as exc:
        db.rollback()
        return _json_conflict_response(exc)
    except IdempotencyError as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), exc.status_code
    except ValueError as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@incident_bp.route("/valider/<int:id>", methods=["POST"])
def valider(id):
    if "user" not in session or session.get("role") not in ["admin", "superadmin"]:
        return redirect(url_for("auth.login"))

    val = 1 if request.form.get("valide") == "on" else 0
    db = get_db()
    
    try:
        inc = db.execute("SELECT id, collaborateur, valide, version FROM incidents WHERE id=%s", (id,)).fetchone()
        if not inc:
            flash("Incident introuvable", "danger")
            return redirect(url_for("main.home"))

        # Opt-in validation: check version if provided in form
        expected_version = parse_expected_version(request)
        
        if inc["valide"] != val:
            if expected_version is not None:
                new_version = optimistic_incident_update(
                    db,
                    incident_id=id,
                    expected_version=expected_version,
                    set_clause="valide=%s",
                    params=(val,),
                )
            else:
                # Force update if no version provided (legacy or bulk)
                db.execute("UPDATE incidents SET valide=%s WHERE id=%s", (val, id))
                new_version = inc["version"] + 1 # Approximate for event
                
            _log_historique(db, id, "validation", "NON VALIDÉ" if inc["valide"] == 0 else "VALIDÉ", "VALIDÉ" if val == 1 else "NON VALIDÉ", session["user"])
            db.commit()
            _emit_incident_event("incident_update", id, db=db, technician_names=[inc.get("collaborateur")], action="valide", version=new_version)
            flash("Statut de validation mis à jour", "success")
            
    except ConcurrencyConflictError:
        db.rollback()
        flash("Conflit de validation: le ticket a été modifié par un autre technicien.", "warning")
    except Exception as e:
        db.rollback()
        import logging
        logging.error(f"Erreur validation incident {id}: {e}")
        flash("Erreur lors de la validation", "danger")
    
    return redirect(url_for("main.home"))


@incident_bp.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    current_app.logger.error(f"DEBUG_DELETE: session={session.get('user')}, role={session.get('role')} for ticket {id}")
    if "user" not in session or session.get("role") not in ("admin", "superadmin"):
        current_app.logger.error("DEBUG_DELETE: Unauthorized, redirecting to login")
        return redirect(url_for("auth.login"))
        
    db = get_db()
    inc = db.execute("SELECT id, collaborateur FROM incidents WHERE id=%s", (id,)).fetchone()
    if inc:
        try:
            current_app.logger.error(f"DEBUG_DELETE: Found incident, preparing to soft-delete {id}")
            
            # Perform soft delete instead of hard delete
            db.execute(
                "UPDATE incidents SET is_deleted=TRUE, deleted_at=CURRENT_TIMESTAMP WHERE id=%s",
                (id,)
            )
            db.commit()
            current_app.logger.error("DEBUG_DELETE: Success soft-deleting in DB")
            
            _emit_incident_event("incident_deleted", id, technician_names=[inc.get("collaborateur")], action="delete")
            _emit_bulk_refresh("incident_deleted", technician_names=[inc.get("collaborateur")], incident_id=id)
        except Exception as e:
            current_app.logger.error(f"Erreur lors de la suppression de l'incident {id}: {e}")
            db.rollback()
            return "Erreur", 500
    else:
        current_app.logger.error("DEBUG_DELETE: Incident not found in DB")

    return redirect(url_for("main.home"))

@incident_bp.route("/historique/<int:id>")
def historique(id):
    if "user" not in session:
        return redirect(url_for("auth.login"))

    db = get_db()
    inc = db.execute("SELECT id, technicien_id, collaborateur FROM incidents WHERE id=%s", (id,)).fetchone()
    
    if not inc or not _can_access_incident(db, inc):
        flash("Incident non trouve ou accès refusé", "warning")
        return redirect(url_for("main.home"))

    logs = db.execute("SELECT * FROM historique WHERE incident_id=%s ORDER BY date_modification DESC", (id,)).fetchall()
    return render_template("historique.html", logs=logs, id=id)

@incident_bp.route("/details")
def details():
    if "user" not in session or session.get("role") not in ["admin", "superadmin"]:
        return redirect(url_for("auth.login"))

    date = request.args.get("date")
    site = request.args.get("site")
    sujet = request.args.get("sujet")
    ttype = request.args.get("type")

    db = get_db()
    ref_data = get_reference_data()
    statuts = ref_data['statuts']

    query = """
        SELECT i.*
        FROM incidents i
        JOIN statuts s ON i.etat = s.nom
        WHERE i.date_affectation=%s AND i.site=%s AND i.sujet=%s AND i.archived=0
    """
    params = [date, site, sujet]

    if ttype == "traite":
        query += " AND s.category = 'traite'"
    elif ttype == "transfere":
        query += " AND s.category = 'transfere'"
    else:
        query += " AND s.category IN ('en_cours', 'suspendu')"

    incs = db.execute(query, params).fetchall()
    return render_template("details.html",
                           incidents=incs,
                           date=date,
                           site=site,
                           sujet=sujet,
                           type=ttype,
                           statuts=statuts,
                           # Pass 'site' as variable too for template
                           )
