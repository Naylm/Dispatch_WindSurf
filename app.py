from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, send_file, g
)
from flask_socketio import SocketIO, join_room, emit
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
import pandas as pd
import pdfkit
from io import BytesIO
import secrets

# Garantir l'intégrité de la base de données au démarrage
from ensure_db_integrity import ensure_database_integrity
ensure_database_integrity()

# Système de notifications
from notification_helpers import (
    emit_new_assignment_notification,
    emit_status_change_notification,
    emit_urgent_update_notification,
    emit_reassignment_notification,
    is_urgent
)

# Gestionnaire d'exports asynchrones
from export_manager import export_manager

# Cache pour données de référence (optimisation performance)
from utils_stability import app_cache

app = Flask(__name__, static_folder='static')

# Route pour le favicon
@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('img/favicon.ico')

# Sécurité : SECRET_KEY est maintenant OBLIGATOIRE en production
if not os.environ.get("SECRET_KEY"):
    if os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError(
            "ERREUR CRITIQUE: SECRET_KEY doit être définie en production!\n"
            "Générez une clé avec: python -c \"import secrets; print(secrets.token_hex(32))\"\n"
            "Ajoutez-la dans votre fichier .env: SECRET_KEY=votre_cle_ici"
        )
    else:
        # En développement seulement, générer une clé temporaire
        app.secret_key = secrets.token_hex(32)
        print("WARNING: SECRET_KEY non définie, utilisation d'une clé temporaire (dev only)")
        print(f"   Ajoutez ceci dans votre fichier .env : SECRET_KEY={app.secret_key}")
else:
    app.secret_key = os.environ.get("SECRET_KEY")

# Configuration optimisée pour la production
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file upload

# CSRF Protection
csrf = CSRFProtect(app)
app.config['WTF_CSRF_ENABLED'] = os.environ.get('WTF_CSRF_ENABLED', 'true').lower() == 'true'
app.config['WTF_CSRF_TIME_LIMIT'] = None  # Pas d'expiration du token CSRF

# Configuration du cache de templates (optimisé pour production)
# En production: cache activé pour meilleures performances
# En développement: désactiver pour rechargement automatique
is_production = os.environ.get("FLASK_ENV", "production") == "production"

if is_production:
    # Production: activer cache pour performances
    app.config["TEMPLATES_AUTO_RELOAD"] = False
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000  # 1 an pour fichiers statiques
    app.jinja_env.auto_reload = False
    # Laisser Jinja gérer son cache par défaut (ne pas le vider)
else:
    # Développement: désactiver cache pour rechargement
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.jinja_env.auto_reload = True
    app.jinja_env.cache = {}

# SocketIO optimisé pour 10 utilisateurs concurrents
socketio = SocketIO(
    app, 
    async_mode="eventlet",
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1000000,
    logger=False,
    engineio_logger=False,
    allow_upgrades=True,
    transports=['polling', 'websocket']
)

# Configuration des chemins
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Import de la configuration DB PostgreSQL
from db_config import get_db as get_db_connection

# 1) Chemin vers wkhtmltopdf.exe – à adapter si nécessaire
# WKHTMLTOPDF_PATH = "/usr/bin/wkhtmltopdf"
# pdf_config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
pdf_config = None


def get_db():
    """
    Récupère ou crée une connexion DB pour la requête courante

    Utilise flask.g pour stocker une connexion unique par requête.
    La connexion sera automatiquement fermée par teardown_appcontext.

    IMPORTANT: Plus besoin d'appeler db.close() manuellement !
    La connexion est restituée au pool automatiquement.
    """
    if 'db' not in g:
        g.db = get_db_connection()
    return g.db


def get_reference_data():
    """
    Récupère les données de référence (priorites, sites, statuts, sujets) avec cache

    Cache TTL: 5 minutes
    Permet de réduire de ~80% les requêtes DB pour ces données fréquemment accédées
    """
    cache_key = "reference_data"
    cached = app_cache.get(cache_key)

    if cached:
        return cached

    # Données pas en cache, les récupérer de la DB
    db = get_db()
    data = {
        'priorites': db.execute("SELECT * FROM priorites ORDER BY nom").fetchall(),
        'sites': db.execute("SELECT * FROM sites ORDER BY nom").fetchall(),
        'statuts': db.execute("SELECT * FROM statuts ORDER BY nom").fetchall(),
        'sujets': db.execute("SELECT * FROM sujets ORDER BY nom").fetchall()
    }

    # Mettre en cache
    app_cache.set(cache_key, data)
    return data


def invalidate_reference_cache():
    """
    Invalide le cache des données de référence
    À appeler lors de modifications (add, edit, delete) sur ces tables
    """
    app_cache.clear("reference_data")


@app.teardown_appcontext
def close_connection(exception):
    """
    Ferme automatiquement la connexion DB à la fin de chaque requête
    Utilise flask.g pour stocker la connexion par requête
    """
    db = g.pop('db', None)
    if db is not None:
        try:
            if exception:
                db.rollback()
            db.close()
        except Exception as e:
            app.logger.error(f"Erreur lors de la fermeture de la connexion: {e}")


def get_contrast_color(hex_color):
    """
    Calcule la couleur de texte optimale (noir ou blanc) selon la luminosité du fond.
    Utilise la formule YIQ pour calculer la luminosité.
    """
    # Enlever le # si présent
    hex_color = hex_color.lstrip('#')
    
    # Convertir en RGB
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except (ValueError, IndexError):
        # En cas d'erreur, retourner blanc par défaut
        return '#ffffff'
    
    # Calculer la luminosité (formule YIQ)
    yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000
    
    # Retourner noir pour fond clair, blanc pour fond foncé
    return '#000000' if yiq >= 128 else '#ffffff'


# Exposer la fonction comme filtre Jinja2
app.jinja_env.filters['contrast_color'] = get_contrast_color


@app.template_filter("freshness_badge")
def freshness_badge_filter(date_value):
    """Retourne le badge de fraîcheur basé sur la date de mise à jour"""
    if not date_value:
        return {"text": "À revoir", "class": "bg-warning"}
    
    # Convertir en datetime si c'est une string
    if isinstance(date_value, str):
        try:
            from dateutil import parser
            date_value = parser.parse(date_value)
        except:
            return {"text": "À revoir", "class": "bg-warning"}
    
    # Calculer la différence en jours
    now = datetime.now()
    if date_value.tzinfo:
        from datetime import timezone
        now = now.replace(tzinfo=timezone.utc)
    
    delta = now - date_value
    days = delta.days
    
    if days < 30:
        return {"text": "Récent", "class": "bg-success"}
    elif days < 180:  # 6 mois
        return {"text": "À jour", "class": "bg-info"}
    else:
        return {"text": "À revoir", "class": "bg-warning"}

@app.template_filter("format_date")
def format_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")
    except:
        return d


@app.before_request
def renew_session():
    session.permanent = True


# ---------- ROUTE : Accueil ----------
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))

    db = get_db()

    # Récupérer les données de référence avec cache (optimisation)
    ref_data = get_reference_data()
    priorites = ref_data['priorites']
    sites = ref_data['sites']
    statuts = ref_data['statuts']

    if session["role"] == "admin":
        # Ordre d'affichage strictement basé sur l'ordre d'insertion
        incidents = db.execute(
            "SELECT * FROM incidents WHERE archived=0 ORDER BY id ASC"
        ).fetchall()
        # Ne récupérer que les techniciens actifs pour l'affichage des colonnes, triés par ordre
        techniciens = db.execute("SELECT * FROM techniciens WHERE actif=1 ORDER BY ordre ASC, id ASC").fetchall()
    else:
        # Comparaison exacte (sensible à la casse) pour éviter l'énumération d'utilisateurs
        incidents = db.execute(
            "SELECT * FROM incidents WHERE collaborateur=? AND archived=0 "
            "ORDER BY id ASC",
            (session["user"],),
        ).fetchall()
        techniciens = []
    
    # Calculer les statistiques par catégorie de statut (optimisé : 1 requête au lieu de 4)
    stats_results = db.execute("""
        SELECT s.category, COUNT(*) as count
        FROM incidents i
        JOIN statuts s ON i.etat = s.nom
        WHERE i.archived=0
        GROUP BY s.category
    """).fetchall()

    # Convertir en dictionnaire avec valeurs par défaut
    stats_by_category = {
        'en_cours': 0,
        'suspendu': 0,
        'transfere': 0,
        'traite': 0
    }
    for row in stats_results:
        if row['category'] in stats_by_category:
            stats_by_category[row['category']] = row['count']

    return render_template(
        "home.html",
        incidents=incidents,
        user=session["user"].capitalize(),
        role=session["role"],
        techniciens=techniciens,
        priorites=priorites,
        sites=sites,
        statuts=statuts,
        stats_by_category=stats_by_category,
    )


@app.route("/api/home-content")
def home_content_api():
    if "user" not in session:
        return "", 403

    db = get_db()

    # Récupérer les données de référence avec cache (optimisation)
    ref_data = get_reference_data()
    priorites = ref_data['priorites']
    sites = ref_data['sites']
    statuts = ref_data['statuts']

    if session["role"] == "admin":
        # Ordre strictement par id (ordre d'entrée)
        incidents = db.execute(
            "SELECT * FROM incidents WHERE archived=0 ORDER BY id ASC"
        ).fetchall()
        techniciens = db.execute("SELECT * FROM techniciens WHERE actif=1 ORDER BY ordre ASC, id ASC").fetchall()
    else:
        # Même ordre strict pour la vue technicien
        # Comparaison exacte (sensible à la casse) pour éviter l'énumération d'utilisateurs
        incidents = db.execute(
            "SELECT * FROM incidents WHERE collaborateur=? AND archived=0 "
            "ORDER BY id ASC",
            (session["user"],),
        ).fetchall()
        techniciens = []
    
    # Calculer les statistiques par catégorie de statut (optimisé : 1 requête au lieu de 4)
    stats_results = db.execute("""
        SELECT s.category, COUNT(*) as count
        FROM incidents i
        JOIN statuts s ON i.etat = s.nom
        WHERE i.archived=0
        GROUP BY s.category
    """).fetchall()

    # Convertir en dictionnaire avec valeurs par défaut
    stats_by_category = {
        'en_cours': 0,
        'suspendu': 0,
        'transfere': 0,
        'traite': 0
    }
    for row in stats_results:
        if row['category'] in stats_by_category:
            stats_by_category[row['category']] = row['count']

    return render_template(
        "home_content.html",
        incidents=incidents,
        user=session["user"],
        role=session["role"],
        techniciens=techniciens,
        priorites=priorites,
        sites=sites,
        statuts=statuts,
        stats_by_category=stats_by_category,
    )


# ---------- GESTION DES TECHNICIENS (CRUD) ----------
@app.route("/techniciens")
def techniciens():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    techniciens = db.execute("SELECT * FROM techniciens ORDER BY ordre ASC, id ASC").fetchall()
    return render_template("techniciens.html", techniciens=techniciens)


@app.route("/add_technicien", methods=["POST"])
def add_technicien():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    prenom = request.form["prenom"].strip()
    password = request.form["password"].strip()
    role = request.form.get("role", "technicien")
    
    # Hash du mot de passe
    hashed_password = generate_password_hash(password)

    db = get_db()
    # Récupérer le max ordre pour mettre le nouveau technicien à la fin
    max_ordre_result = db.execute("SELECT COALESCE(MAX(ordre), 0) as max_ordre FROM techniciens").fetchone()
    new_ordre = (max_ordre_result['max_ordre'] if max_ordre_result else 0) + 1
    
    db.execute(
        "INSERT INTO techniciens (prenom, role, password, ordre) VALUES (?, ?, ?, ?)",
        (prenom, role, hashed_password, new_ordre),
    )
    db.commit()
    return redirect(url_for("techniciens"))


@app.route("/technicien/edit/<int:id>", methods=["POST"])
def edit_technicien(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    prenom = request.form["prenom"].strip()
    role = request.form.get("role", "technicien")
    new_pass = request.form.get("password", "").strip()

    db = get_db()
    if new_pass:
        # Hash du nouveau mot de passe
        hashed_password = generate_password_hash(new_pass)
        db.execute(
            "UPDATE techniciens SET prenom=?, role=?, password=? WHERE id=?",
            (prenom, role, hashed_password, id),
        )
    else:
        db.execute(
            "UPDATE techniciens SET prenom=?, role=? WHERE id=?",
            (prenom, role, id),
        )
    db.commit()
    return redirect(url_for("techniciens"))


@app.route("/technicien/incidents/<int:id>")
def technicien_incidents(id):
    if "user" not in session or session["role"] != "admin":
        return "", 403

    db = get_db()
    tech = db.execute("SELECT prenom FROM techniciens WHERE id=?", (id,)).fetchone()
    if not tech:
        return jsonify({"error": "Not found"}), 404

    incidents = db.execute(
        "SELECT * FROM incidents WHERE collaborateur=?", (tech["prenom"],)
    ).fetchall()
    autres_techs = db.execute(
        "SELECT id, prenom FROM techniciens WHERE id != ?", (id,)
    ).fetchall()

    return jsonify(
        {
            "incidents": [dict(i) for i in incidents],
            "autres_techs": [dict(t) for t in autres_techs],
            "tech_prenom": tech["prenom"],
        }
    )


@app.route("/technicien/transfer_delete/<int:id>", methods=["POST"])
def transfer_and_delete_technicien(id):
    if "user" not in session or session["role"] != "admin":
        return "", 403

    db = get_db()
    tech = db.execute("SELECT prenom FROM techniciens WHERE id=?", (id,)).fetchone()
    if not tech:
        return jsonify({"status": "error", "message": "Tech introuvable"}), 404

    # Ré-affecter chaque incident sélectionné, si applicable
    for key, value in request.form.items():
        if key.startswith("incident_"):
            incident_id = int(key.split("_")[1])
            nouveau_collab = value
            db.execute(
                "UPDATE incidents SET collaborateur=? WHERE id=?", (nouveau_collab, incident_id)
            )

    # Puis supprimer le technicien
    db.execute("DELETE FROM techniciens WHERE id=?", (id,))
    db.commit()
    return jsonify({"status": "ok"})


@app.route("/technicien/delete/<int:id>", methods=["POST"])
def delete_technicien(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM techniciens WHERE id=?", (id,))
    db.commit()
    return redirect(url_for("techniciens"))


@app.route("/toggle_technicien/<int:id>", methods=["POST"])
def toggle_technicien(id):
    """Active ou désactive un technicien"""
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    # Récupérer l'état actuel
    technicien = db.execute("SELECT actif FROM techniciens WHERE id=?", (id,)).fetchone()
    
    if technicien:
        # Inverser l'état (1 devient 0, 0 devient 1)
        new_state = 0 if technicien['actif'] == 1 else 1
        db.execute("UPDATE techniciens SET actif=? WHERE id=?", (new_state, id))
        db.commit()
        flash(f"Technicien {'activé' if new_state == 1 else 'désactivé'} avec succès!", "success")
    
    return redirect(url_for("techniciens"))


@app.route("/techniciens/update_order", methods=["POST"])
def update_techniciens_order():
    """Met à jour l'ordre d'affichage des techniciens"""
    if "user" not in session or session["role"] != "admin":
        return jsonify({"error": "Non autorisé"}), 403
    
    data = request.get_json()
    if not data or "order" not in data:
        return jsonify({"error": "Données invalides"}), 400
    
    db = get_db()
    try:
        # Mettre à jour l'ordre pour chaque technicien
        for index, tech_id in enumerate(data["order"], start=1):
            db.execute("UPDATE techniciens SET ordre=? WHERE id=?", (index, tech_id))
        db.commit()
        return jsonify({"success": True, "message": "Ordre mis à jour avec succès"})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Erreur lors de la mise à jour de l'ordre: {e}")
        return jsonify({"error": str(e)}), 500


# ----------- DRAG & DROP INCIDENTS (DASHBOARD ADMIN) -----------
@app.route("/incidents/assign", methods=["POST"])
def assign_incident():
    if "user" not in session or session["role"] != "admin":
        return "", 403

    incident_id = request.form.get("id")
    new_collab = request.form.get("collaborateur")
    if not incident_id or not new_collab:
        return jsonify({"status": "error", "message": "Paramètres manquants"}), 400

    try:
        db = get_db()

        # Récupérer les données de l'incident AVANT modification
        incident = db.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if not incident:
            return jsonify({"status": "error", "message": "Incident introuvable"}), 404

        old_collab = incident['collaborateur']

        db.execute("BEGIN")
        db.execute(
            "UPDATE incidents SET collaborateur=? WHERE id=?", (new_collab, incident_id)
        )
        db.commit()

        # Préparer les données pour la notification
        incident_data = {
            "id": incident_id,
            "numero": incident['numero'],
            "site": incident['site'],
            "sujet": incident['sujet'],
            "urgence": incident['urgence'],
            "note_dispatch": incident.get('note_dispatch', ''),
            "localisation": incident.get('localisation', '')
        }

        # Émettre la notification de réaffectation
        emit_reassignment_notification(socketio, incident_data, old_collab, new_collab)

        socketio.emit("incident_update", {"action": "reassign", "incident_id": incident_id, "new_collab": new_collab})
        return jsonify({"status": "ok"})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Erreur assign_incident: {e}")
        return jsonify({"status": "error", "message": "Erreur serveur"}), 500
def export_popup():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    techniciens = db.execute("SELECT id, prenom FROM techniciens").fetchall()
    return render_template("export_popup.html", techniciens=techniciens)


def _generate_excel_export(tech_ids):
    """
    Fonction helper pour générer un export Excel
    Utilisée par la route asynchrone
    """
    db = get_db()
    try:
        placeholders = ",".join("?" for _ in tech_ids)
        query = f"SELECT prenom FROM techniciens WHERE id IN ({placeholders})"
        techs = [row["prenom"] for row in db.execute(query, tech_ids).fetchall()]

        if not techs:
            df = pd.DataFrame()
        else:
            params = ",".join("?" for _ in techs)
            sql = f"SELECT * FROM incidents WHERE collaborateur IN ({params}) AND archived=0"
            df = pd.read_sql_query(sql, db.conn, params=techs)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Incidents")
        output.seek(0)

        return output.getvalue()
    finally:
        db.close()


@app.route("/export/incidents/excel", methods=["POST"])
def export_incidents_excel():
    """
    Démarre un export Excel asynchrone
    Retourne immédiatement un job_id pour suivre la progression
    """
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    tech_ids = request.form.getlist("tech_ids")
    if not tech_ids:
        flash("Veuillez sélectionner au moins un technicien.", "warning")
        return redirect(url_for("export_popup"))

    # Créer un job d'export
    job_id = export_manager.create_job('excel', 'incidents_filtrés.xlsx')

    # Démarrer l'export en arrière-plan
    export_manager.start_job(job_id, _generate_excel_export, tech_ids)

    # Rediriger vers une page de statut
    return redirect(url_for("export_status", job_id=job_id))


def _generate_pdf_export(tech_ids):
    """
    Fonction helper pour générer un export PDF
    Utilisée par la route asynchrone
    """
    db = get_db()
    try:
        placeholders = ",".join("?" for _ in tech_ids)
        query = f"SELECT prenom FROM techniciens WHERE id IN ({placeholders})"
        techs = [row["prenom"] for row in db.execute(query, tech_ids).fetchall()]

        if not techs:
            incidents = []
        else:
            params = ",".join("?" for _ in techs)
            sql = f"SELECT * FROM incidents WHERE collaborateur IN ({params}) AND archived=0"
            incidents = db.execute(sql, techs).fetchall()

        # Générer le HTML depuis le template
        html = render_template("export_pdf.html", incidents=incidents, techniciens=techs)

        pdf_data = pdfkit.from_string(html, False, configuration=pdf_config)
        return pdf_data
    finally:
        db.close()


@app.route("/export/incidents/pdf", methods=["POST"])
def export_incidents_pdf():
    """
    Démarre un export PDF asynchrone
    Retourne immédiatement un job_id pour suivre la progression
    """
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    tech_ids = request.form.getlist("tech_ids")
    if not tech_ids:
        flash("Veuillez sélectionner au moins un technicien.", "warning")
        return redirect(url_for("export_popup"))

    # Créer un job d'export
    job_id = export_manager.create_job('pdf', 'incidents_filtrés.pdf')

    # Démarrer l'export en arrière-plan
    export_manager.start_job(job_id, _generate_pdf_export, tech_ids)

    # Rediriger vers une page de statut
    return redirect(url_for("export_status", job_id=job_id))


@app.route("/export/status/<job_id>")
def export_status(job_id):
    """
    Page de statut pour suivre la progression d'un export
    Affiche un loader pendant la génération et redirige vers le téléchargement quand prêt
    """
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    status = export_manager.get_job_status(job_id)
    if not status:
        flash("Export introuvable ou expiré.", "warning")
        return redirect(url_for("export_popup"))

    return render_template("export_status.html", job_id=job_id, status=status)


@app.route("/export/api/status/<job_id>")
def export_api_status(job_id):
    """
    API pour vérifier le statut d'un export (polling depuis le frontend)
    """
    if "user" not in session or session["role"] != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    status = export_manager.get_job_status(job_id)
    if not status:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(status)


@app.route("/export/download/<job_id>")
def export_download(job_id):
    """
    Télécharge le fichier généré par l'export
    """
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    status = export_manager.get_job_status(job_id)
    if not status:
        flash("Export introuvable ou expiré.", "warning")
        return redirect(url_for("export_popup"))

    if status['status'] != 'completed':
        flash("L'export n'est pas encore terminé.", "info")
        return redirect(url_for("export_status", job_id=job_id))

    file_data = export_manager.get_job_file(job_id)
    if not file_data:
        flash("Fichier d'export introuvable.", "danger")
        return redirect(url_for("export_popup"))

    # Déterminer le type MIME
    mimetype = (
        "application/pdf" if status['export_type'] == 'pdf'
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    return send_file(
        BytesIO(file_data),
        mimetype=mimetype,
        as_attachment=True,
        download_name=status['filename']
    )


# ---------- CONFIGURATION (ADMIN ONLY) ----------
@app.route("/configuration")
def configuration():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    sujets = db.execute("SELECT * FROM sujets ORDER BY nom").fetchall()
    priorites = db.execute("SELECT * FROM priorites ORDER BY niveau").fetchall()
    sites = db.execute("SELECT * FROM sites ORDER BY nom").fetchall()
    statuts = db.execute("SELECT * FROM statuts ORDER BY nom").fetchall()

    return render_template("configuration.html",
                         sujets=sujets,
                         priorites=priorites,
                         sites=sites,
                         statuts=statuts)


@app.route("/configuration/sujet/add", methods=["POST"])
def add_sujet():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    nom = request.form["nom"].strip()
    db = get_db()
    db.execute("INSERT INTO sujets (nom) VALUES (?)", (nom,))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/sujet/edit", methods=["POST"])
def edit_sujet():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    id = request.form["id"].strip()
    nom = request.form["nom"].strip()

    db = get_db()
    db.execute("UPDATE sujets SET nom=? WHERE id=?", (nom, id))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/sujet/delete/<int:id>", methods=["POST"])
def delete_sujet(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM sujets WHERE id=?", (id,))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/priorite/add", methods=["POST"])
def add_priorite():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    
    nom = request.form["nom"].strip()
    couleur = request.form["couleur"].strip()
    niveau = request.form["niveau"].strip()
    db = get_db()
    db.execute("INSERT INTO priorites (nom, couleur, niveau) VALUES (?, ?, ?)", (nom, couleur, niveau))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/priorite/edit", methods=["POST"])
def edit_priorite():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    id = request.form["id"].strip()
    nom = request.form["nom"].strip()
    couleur = request.form["couleur"].strip()
    niveau = request.form["niveau"].strip()

    db = get_db()
    db.execute("UPDATE priorites SET nom=?, couleur=?, niveau=? WHERE id=?", (nom, couleur, niveau, id))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/priorite/delete/<int:id>", methods=["POST"])
def delete_priorite(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM priorites WHERE id=?", (id,))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/site/add", methods=["POST"])
def add_site():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    nom = request.form["nom"].strip()
    couleur = request.form["couleur"].strip()
    db = get_db()
    db.execute("INSERT INTO sites (nom, couleur) VALUES (?, ?)", (nom, couleur))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/site/edit", methods=["POST"])
def edit_site():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    id = request.form["id"].strip()
    nom = request.form["nom"].strip()
    couleur = request.form["couleur"].strip()

    db = get_db()
    db.execute("UPDATE sites SET nom=?, couleur=? WHERE id=?", (nom, couleur, id))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/site/delete/<int:id>", methods=["POST"])
def delete_site(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM sites WHERE id=?", (id,))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/statut/add", methods=["POST"])
def add_statut():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    nom = request.form["nom"].strip()
    couleur = request.form["couleur"].strip()
    category = request.form["category"].strip()

    db = get_db()
    db.execute("INSERT INTO statuts (nom, couleur, category) VALUES (?, ?, ?)", (nom, couleur, category))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/statut/edit", methods=["POST"])
def edit_statut():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    id = request.form["id"].strip()
    nom = request.form["nom"].strip()
    couleur = request.form["couleur"].strip()
    category = request.form["category"].strip()

    db = get_db()
    db.execute("UPDATE statuts SET nom=?, couleur=?, category=? WHERE id=?", (nom, couleur, category, id))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/statut/delete/<int:id>", methods=["POST"])
def delete_statut(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM statuts WHERE id=?", (id,))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/force_password_reset", methods=["POST"])
def force_password_reset():
    """Force un utilisateur à réinitialiser son mot de passe à la prochaine connexion"""
    if "user" not in session or session["role"] != "admin":
        return jsonify({"error": "Non autorisé"}), 403

    username = request.form.get("username", "").strip()
    user_type = request.form.get("user_type", "user").strip()

    if not username:
        return jsonify({"error": "Nom d'utilisateur requis"}), 400

    db = get_db()

    try:
        if user_type == "user":
            db.execute(
                "UPDATE users SET force_password_reset=1 WHERE username=?",
                (username,)
            )
        else:  # technicien
            db.execute(
                "UPDATE techniciens SET force_password_reset=1 WHERE prenom=?",
                (username,)
            )

        db.commit()
        db.close()

        app.logger.info(f"Réinitialisation de mot de passe forcée pour {username} ({user_type}) par {session['user']}")
        return jsonify({"success": True, "message": f"Réinitialisation forcée pour {username}"}), 200

    except Exception as e:
        app.logger.error(f"Erreur lors de la réinitialisation forcée: {e}")
        return jsonify({"error": "Erreur lors de la mise à jour"}), 500


# ---------- AUTH (users + techniciens) ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"].strip()
        p = request.form["password"].strip()
        db = get_db()

        # 1) Essayer dans users
        user = db.execute(
            "SELECT * FROM users WHERE username=?", (u,)
        ).fetchone()
        if user:
            app.logger.debug(f"Tentative de connexion pour l'utilisateur: {u}")
            # Vérifier le mot de passe hashé (OBLIGATOIRE - plus de fallback en clair)
            if user["password"] and (user["password"].startswith("pbkdf2:") or user["password"].startswith("scrypt:")):
                if check_password_hash(user["password"], p):
                    session["user"] = u
                    session["role"] = user["role"]
                    session["user_type"] = "user"  # Pour savoir quelle table
                    session.permanent = True
                    app.logger.info(f"Connexion réussie: {u} (role: {user['role']})")

                    # Vérifier si réinitialisation forcée requise
                    try:
                        force_reset = user["force_password_reset"]
                    except (KeyError, IndexError):
                        force_reset = 0

                    db.close()
                    if force_reset == 1:
                        session["force_password_reset"] = True
                        app.logger.info(f"Réinitialisation forcée requise pour {u}")
                        return redirect(url_for("change_password_forced"))

                    return redirect(url_for("home"))
                else:
                    app.logger.warning(f"Échec de connexion pour {u}: mot de passe incorrect")
                    db.close()
                    flash("Mauvais identifiants", "danger")
                    return render_template("login.html")
            else:
                # Mot de passe non hashé ou vide - REFUSER LA CONNEXION
                app.logger.error(f"Échec de connexion pour {u}: mot de passe non hashé (réinitialisation requise)")
                db.close()
                flash("Votre mot de passe doit être réinitialisé. Contactez l'administrateur.", "danger")
                return render_template("login.html")

        # 2) Sinon, essayer dans techniciens (ATTENTION: utilise prenom - devrait être username)
        tech = db.execute(
            "SELECT * FROM techniciens WHERE prenom=?",
            (u,),
        ).fetchone()
        if tech and tech["password"]:
            app.logger.debug(f"Tentative de connexion pour le technicien: {u}")
            # Vérifier le mot de passe hashé (OBLIGATOIRE - plus de fallback en clair)
            if tech["password"].startswith("pbkdf2:") or tech["password"].startswith("scrypt:"):
                if check_password_hash(tech["password"], p):
                    session["user"] = tech["prenom"]
                    session["role"] = tech["role"] or "technicien"
                    session["user_type"] = "technicien"  # Pour savoir quelle table
                    session.permanent = True
                    app.logger.info(f"Connexion technicien réussie: {tech['prenom']}")

                    # Vérifier si réinitialisation forcée requise
                    try:
                        force_reset = tech["force_password_reset"]
                    except (KeyError, IndexError):
                        force_reset = 0

                    db.close()
                    if force_reset == 1:
                        session["force_password_reset"] = True
                        app.logger.info(f"Réinitialisation forcée requise pour technicien {tech['prenom']}")
                        return redirect(url_for("change_password_forced"))

                    return redirect(url_for("home"))
                else:
                    app.logger.warning(f"Échec de connexion pour technicien {u}: mot de passe incorrect")
                    db.close()
                    flash("Mauvais identifiants", "danger")
                    return render_template("login.html")
            else:
                # Mot de passe non hashé ou vide - REFUSER LA CONNEXION
                app.logger.error(f"Échec de connexion pour technicien {u}: mot de passe non hashé")
                db.close()
                flash("Votre mot de passe doit être réinitialisé. Contactez l'administrateur.", "danger")
                return render_template("login.html")

        # Aucun utilisateur trouvé
        db.close()
        flash("Mauvais identifiants", "danger")
        app.logger.warning(f"Échec de connexion: identifiants invalides pour {u}")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/change_password_forced", methods=["GET", "POST"])
def change_password_forced():
    """Route pour le changement de mot de passe forcé (demandé par l'admin)"""
    if "user" not in session:
        return redirect(url_for("login"))

    # Vérifier que l'utilisateur doit vraiment changer son mot de passe
    if not session.get("force_password_reset", False):
        return redirect(url_for("home"))

    if request.method == "POST":
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # Validation
        if not current_password or not new_password or not confirm_password:
            flash("Tous les champs sont obligatoires", "danger")
            return render_template("change_password_forced.html")

        if new_password != confirm_password:
            flash("Les mots de passe ne correspondent pas", "danger")
            return render_template("change_password_forced.html")

        if len(new_password) < 8:
            flash("Le mot de passe doit contenir au moins 8 caractères", "danger")
            return render_template("change_password_forced.html")

        db = get_db()
        user_type = session.get("user_type", "user")
        username = session["user"]

        # Récupérer l'utilisateur selon le type
        if user_type == "user":
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        else:
            user = db.execute("SELECT * FROM techniciens WHERE prenom=?", (username,)).fetchone()

        if not user:
            db.close()
            flash("Utilisateur introuvable", "danger")
            return redirect(url_for("logout"))

        # Vérifier le mot de passe actuel
        if not check_password_hash(user["password"], current_password):
            db.close()
            flash("Mot de passe actuel incorrect", "danger")
            return render_template("change_password_forced.html")

        # Vérifier que le nouveau mot de passe est différent
        if check_password_hash(user["password"], new_password):
            db.close()
            flash("Le nouveau mot de passe doit être différent de l'ancien", "danger")
            return render_template("change_password_forced.html")

        # Hasher le nouveau mot de passe
        hashed_password = generate_password_hash(new_password)

        # Mettre à jour le mot de passe et réinitialiser le flag
        if user_type == "user":
            db.execute(
                "UPDATE users SET password=?, force_password_reset=0 WHERE username=?",
                (hashed_password, username)
            )
        else:
            db.execute(
                "UPDATE techniciens SET password=?, force_password_reset=0 WHERE prenom=?",
                (hashed_password, username)
            )

        db.commit()
        db.close()

        # Supprimer le flag de session
        session.pop("force_password_reset", None)

        app.logger.info(f"Mot de passe réinitialisé avec succès pour {username}")
        flash("Mot de passe réinitialisé avec succès!", "success")

        # Rediriger vers la page d'accueil
        return redirect(url_for("home"))

    return render_template("change_password_forced.html")


# ---------- AJOUT INCIDENT ----------
@app.route("/add", methods=["GET", "POST"])
def add_incident():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

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
        collab = request.form["collaborateur"]
        date_aff = request.form["date_affectation"]
        note_dispatch = request.form.get("note_dispatch", "")
        localisation = request.form.get("localisation", "")

        sql = """
          INSERT INTO incidents (
            numero, site, sujet, urgence,
            collaborateur, etat, note_dispatch,
            valide, date_affectation, archived, localisation
          ) VALUES (?, ?, ?, ?, ?, 'Affecté', ?, 0, ?, 0, ?)
          RETURNING id
        """
        result = db.execute(sql, (numero, site, sujet, urgence, collab, note_dispatch, date_aff, localisation))
        incident_id = result.fetchone()["id"]
        db.commit()

        # Préparer les données pour la notification
        incident_data = {
            "id": incident_id,
            "numero": numero,
            "site": site,
            "sujet": sujet,
            "urgence": urgence,
            "note_dispatch": note_dispatch,
            "localisation": localisation
        }

        # Émettre la notification de nouveau ticket
        emit_new_assignment_notification(socketio, incident_data, collab)

        # Émettre aussi l'event classique pour le refresh
        socketio.emit("incident_update", {"action": "add"})
        return redirect(url_for("home"))

    current = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "add_incident.html", current_date=current, techniciens=techniciens,
        sujets=sujets, priorites=priorites, sites=sites
    )


# ---------- SUPPRIMER UN INCIDENT ----------
@app.route("/delete_incident/<int:id>", methods=["POST"])
def delete_incident(id):
    if "user" not in session or session["role"] != "admin":
        return jsonify({"error": "Non autorisé"}), 403

    db = get_db()
    incident = db.execute("SELECT * FROM incidents WHERE id=?", (id,)).fetchone()
    if not incident:
        return jsonify({"error": "Incident introuvable"}), 404

    # Enregistrement dans l'historique avant suppression
    hist_sql = """
      INSERT INTO historique (
        incident_id, champ, ancienne_valeur,
        nouvelle_valeur, modifie_par, date_modification
      ) VALUES (?, ?, ?, ?, ?, ?)
    """
    db.execute(
        hist_sql,
        (
            id,
            "suppression",
            f"Ticket {incident['numero']}",
            "SUPPRIMÉ",
            session["user"],
            datetime.now().strftime("%d-%m-%Y %H:%M"),
        ),
    )
    
    # Suppression de l'incident
    try:
        db.execute("DELETE FROM incidents WHERE id=?", (id,))
        db.commit()
        
        # Emit avec plus de détails pour la mise à jour temps réel
        socketio.emit("incident_deleted", {
            "action": "delete",
            "id": id,
            "numero": incident['numero'],
            "collaborateur": incident['collaborateur']
        })
        
        # Si c'est une requête AJAX, retourner JSON
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            return jsonify({"status": "ok", "success": True}), 200
        
        # Sinon, comportement classique (redirect)
        flash("Incident supprimé", "success")
        return redirect(url_for("home"))
    except Exception as e:
        db.rollback()
        app.logger.error(f"Erreur delete_incident: {e}")
        
        # Si c'est une requête AJAX, retourner JSON
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            if "conflit de modification" in str(e).lower():
                return jsonify({"error": "Conflit de modification"}), 409
            else:
                return jsonify({"error": "Erreur serveur"}), 500
        
        # Sinon, comportement classique
        flash("Erreur lors de la suppression", "error")
        return redirect(url_for("home"))
@app.route("/edit_incident/<int:id>", methods=["GET", "POST"])
def edit_incident(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    incident = db.execute("SELECT * FROM incidents WHERE id=?", (id,)).fetchone()
    if not incident:
        flash("Incident introuvable", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        numero = request.form["numero"].strip()
        site = request.form["site"].strip()
        sujet = request.form["sujet"].strip()
        urgence = request.form["urgence"].strip()
        collaborateur = request.form["collaborateur"].strip()
        etat = request.form["etat"].strip()
        notes = request.form.get("notes", "").strip()
        note_dispatch = request.form.get("note_dispatch", "").strip()
        date_aff = request.form["date_affectation"]
        localisation = request.form.get("localisation", "").strip()

        # Mise à jour de l'incident avec protection transactionnelle
        try:
            db.execute("BEGIN")
            db.execute(
                """UPDATE incidents SET numero=?, site=?, sujet=?, urgence=?,
                   collaborateur=?, etat=?, notes=?, note_dispatch=?, date_affectation=?, localisation=? WHERE id=?""",
                (numero, site, sujet, urgence, collaborateur, etat, notes, note_dispatch, date_aff, localisation, id)
            )
        except Exception:
            db.rollback()
            flash("Conflit de modification, veuillez réessayer", "warning")
            return redirect(url_for("edit_incident", id=id))
        
        # Enregistrement dans l'historique
        hist_sql = """
          INSERT INTO historique (
            incident_id, champ, ancienne_valeur,
            nouvelle_valeur, modifie_par, date_modification
          ) VALUES (?, ?, ?, ?, ?, ?)
        """
        db.execute(
            hist_sql,
            (
                id,
                "modification_complete",
                "Modification",
                f"Ticket modifié: {numero}",
                session["user"],
                datetime.now().strftime("%d-%m-%Y %H:%M"),
            ),
        )
        db.commit()
        socketio.emit("incident_update", {"action": "edit"})
        flash("Incident modifié avec succès", "success")
        return redirect(url_for("home"))

    techniciens = db.execute("SELECT * FROM techniciens").fetchall()
    sujets = db.execute("SELECT * FROM sujets ORDER BY nom").fetchall()
    priorites = db.execute("SELECT * FROM priorites ORDER BY niveau").fetchall()
    sites = db.execute("SELECT * FROM sites ORDER BY nom").fetchall()
    
    return render_template(
        "edit_incident.html", 
        incident=incident, 
        techniciens=techniciens,
        sujets=sujets,
        priorites=priorites,
        sites=sites
    )


# ---------- NOTES INCIDENTS ----------
@app.route("/edit_note/<int:id>", methods=["GET", "POST"])
def edit_note(id):
    if "user" not in session:
        return redirect(url_for("login"))

    db = get_db()
    inc = db.execute("SELECT * FROM incidents WHERE id=?", (id,)).fetchone()
    # Comparaison exacte (sensible à la casse) pour sécurité
    if inc["collaborateur"] != session["user"] and session["role"] != "admin":
        return redirect(url_for("home"))

    if request.method == "POST":
        note = request.form["note"] or ""
        localisation = request.form.get("localisation", "").strip()
        
        # Vérifier si des changements ont été faits
        changes_made = False
        
        if inc["notes"] != note:
            changes_made = True
            hist_sql = """
              INSERT INTO historique (
                incident_id, champ, ancienne_valeur,
                nouvelle_valeur, modifie_par, date_modification
              ) VALUES (?, ?, ?, ?, ?, ?)
            """
            db.execute(
                hist_sql,
                (
                    id,
                    "notes",
                    inc["notes"],
                    note,
                    session["user"],
                    datetime.now().strftime("%d-%m-%Y %H:%M"),
                ),
            )
        
        if inc["localisation"] != localisation:
            changes_made = True
            hist_sql = """
              INSERT INTO historique (
                incident_id, champ, ancienne_valeur,
                nouvelle_valeur, modifie_par, date_modification
              ) VALUES (?, ?, ?, ?, ?, ?)
            """
            db.execute(
                hist_sql,
                (
                    id,
                    "localisation",
                    inc["localisation"] or "",
                    localisation,
                    session["user"],
                    datetime.now().strftime("%d-%m-%Y %H:%M"),
                ),
            )
        
        if changes_made:
            db.execute("UPDATE incidents SET notes=?, localisation=? WHERE id=?", (note, localisation, id))
            db.commit()
            socketio.emit("incident_update", {"action": "note"})

        return redirect(url_for("home"))

    return render_template("edit_note.html", id=id, numero=inc["numero"], current_note=inc["notes"], current_localisation=inc["localisation"] or "")


# ---------- EDITION INLINE DES NOTES (AJAX) ----------
@app.route("/edit_note_inline/<int:id>", methods=["POST"])
def edit_note_inline(id):
    """Édition inline de la note technicien via AJAX"""
    if "user" not in session:
        return jsonify({"error": "Non authentifié"}), 403

    db = get_db()
    inc = db.execute("SELECT * FROM incidents WHERE id=?", (id,)).fetchone()

    if not inc:
        return jsonify({"error": "Incident introuvable"}), 404

    # Vérifier les permissions (technicien propriétaire ou admin)
    # Comparaison exacte (sensible à la casse) pour sécurité
    if inc["collaborateur"] != session["user"] and session["role"] != "admin":
        return jsonify({"error": "Permission refusée"}), 403

    new_note = request.json.get("note", "").strip()

    # Vérifier si la note a changé
    if inc["notes"] != new_note:
        # Enregistrer dans l'historique
        hist_sql = """
          INSERT INTO historique (
            incident_id, champ, ancienne_valeur,
            nouvelle_valeur, modifie_par, date_modification
          ) VALUES (?, ?, ?, ?, ?, ?)
        """
        db.execute(
            hist_sql,
            (
                id,
                "notes",
                inc["notes"] or "",
                new_note,
                session["user"],
                datetime.now().strftime("%d-%m-%Y %H:%M"),
            ),
        )

        # Mettre à jour la note
        db.execute("UPDATE incidents SET notes=? WHERE id=?", (new_note, id))
        db.commit()
        socketio.emit("incident_update", {"action": "note_edit"})

        return jsonify({"success": True, "note": new_note})

    return jsonify({"success": True, "note": new_note, "unchanged": True})


@app.route("/edit_note_dispatch/<int:id>", methods=["POST"])
def edit_note_dispatch(id):
    """Édition de la note dispatch (admin seulement) via AJAX"""
    if "user" not in session or session["role"] != "admin":
        return jsonify({"error": "Permission refusée - Admin uniquement"}), 403

    db = get_db()
    inc = db.execute("SELECT * FROM incidents WHERE id=?", (id,)).fetchone()

    if not inc:
        return jsonify({"error": "Incident introuvable"}), 404

    new_note_dispatch = request.json.get("note_dispatch", "").strip()

    # Vérifier si la note dispatch a changé
    old_note_dispatch = inc["note_dispatch"] if inc["note_dispatch"] else ""
    if old_note_dispatch != new_note_dispatch:
        # Enregistrer dans l'historique
        hist_sql = """
          INSERT INTO historique (
            incident_id, champ, ancienne_valeur,
            nouvelle_valeur, modifie_par, date_modification
          ) VALUES (?, ?, ?, ?, ?, ?)
        """
        db.execute(
            hist_sql,
            (
                id,
                "note_dispatch",
                old_note_dispatch,
                new_note_dispatch,
                session["user"],
                datetime.now().strftime("%d-%m-%Y %H:%M"),
            ),
        )

        # Mettre à jour la note dispatch
        db.execute("UPDATE incidents SET note_dispatch=? WHERE id=?", (new_note_dispatch, id))
        db.commit()
        socketio.emit("incident_update", {"action": "note_dispatch_edit"})

        return jsonify({"success": True, "note_dispatch": new_note_dispatch})

    return jsonify({"success": True, "note_dispatch": new_note_dispatch, "unchanged": True})


# ---------- UPDATE ETAT ----------
@app.route("/update_etat/<int:id>", methods=["POST"])
def update_etat(id):
    if "user" not in session:
        return redirect(url_for("login"))

    db = get_db()
    try:
        # PostgreSQL gère automatiquement les transactions, pas besoin de BEGIN explicite
        inc = db.execute("SELECT * FROM incidents WHERE id=?", (id,)).fetchone()
        new = request.form["etat"]

        if inc["etat"] != new:
            db.execute("UPDATE incidents SET etat=? WHERE id=?", (new, id))
            hist_sql = """
              INSERT INTO historique (
                incident_id, champ, ancienne_valeur,
                nouvelle_valeur, modifie_par, date_modification
              ) VALUES (?, ?, ?, ?, ?, ?)
            """
            db.execute(
                hist_sql,
                (
                    id,
                    "etat",
                    inc["etat"],
                    new,
                    session["user"],
                    datetime.now().strftime("%d-%m-%Y %H:%M"),
                ),
            )

            # Notification de changement de statut
            emit_status_change_notification(
                socketio,
                id,
                inc["numero"],
                inc["etat"],
                new,
                inc["collaborateur"]
            )

            # Si passage à un état critique sur ticket urgent
            if is_urgent(inc["urgence"]) and new in ["Suspendu", "En intervention"]:
                emit_urgent_update_notification(
                    socketio,
                    id,
                    inc["numero"],
                    f"Statut changé: {new}",
                    inc["collaborateur"]
                )

        db.commit()

        # Si c'est une requête AJAX, retourner JSON
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if is_ajax:
            # Récupérer les infos du statut (couleur)
            statut_info = db.execute("SELECT couleur FROM statuts WHERE nom=?", (new,)).fetchone()
            statut_couleur = statut_info["couleur"] if statut_info else "#6c757d"
            statut_text_color = get_contrast_color(statut_couleur)

            # Émettre broadcast pour que les autres clients se rafraîchissent
            # Note: emit() fait déjà un broadcast par défaut, pas besoin du paramètre
            socketio.emit("incident_etat_changed", {
                "action": "etat",
                "id": id,
                "new_etat": new,
                "numero": inc["numero"],
                "couleur": statut_couleur,
                "text_color": statut_text_color
            })
            return jsonify({"status": "ok", "new_etat": new, "couleur": statut_couleur, "text_color": statut_text_color})
        else:
            # Requête normale (formulaire), émettre le broadcast classique
            socketio.emit("incident_update", {"action": "etat"})

    except Exception as e:
        db.rollback()
        app.logger.error(f"Erreur update_etat: {e}")

        # Si c'est une requête AJAX, retourner erreur JSON
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            return jsonify({"status": "error", "message": str(e)}), 500

        flash("Conflit de modification", "warning")

    return redirect(url_for("home"))


# ---------- VALIDATION ----------
@app.route("/valider/<int:id>", methods=["POST"])
def valider(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    val = 1 if request.form.get("valide") == "on" else 0
    db = get_db()
    db.execute("UPDATE incidents SET valide=? WHERE id=?", (val, id))
    db.commit()
    socketio.emit("incident_update", {"action": "valide"})
    return redirect(url_for("home"))


# ---------- SUPPRESSION INCIDENT ----------
@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM incidents WHERE id=?", (id,))
    socketio.emit("incident_update", {"action": "delete"})
    return redirect(url_for("home"))




# ---------- HISTORIQUE ----------
@app.route("/historique/<int:id>")
def historique(id):
    if "user" not in session:
        return redirect(url_for("login"))

    logs = get_db().execute(
        "SELECT * FROM historique WHERE incident_id=? ORDER BY date_modification DESC", (id,)
    ).fetchall()
    return render_template("historique.html", logs=logs, id=id)




# ---------- DETAILS ----------
@app.route("/details")
def details():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    date = request.args.get("date")
    site = request.args.get("site")
    sujet = request.args.get("sujet")
    ttype = request.args.get("type")

    db = get_db()
    # On commence par filtrer date + site + sujet
    query = "SELECT * FROM incidents WHERE date_affectation=? AND site=? AND sujet=? AND archived=0"
    params = [date, site, sujet]

    # On ajoute ensuite le filtre sur l'état
    if ttype == "traite":
        query += " AND etat='Traité'"
    else:
        query += " AND etat IN ('Affecté','En cours de préparation','Suspendu')"

    incs = db.execute(query, params).fetchall()
    return render_template("details.html",
                           incidents=incs,
                           date=date,
                           site=site,
                           sujet=sujet,
                           type=ttype)



# ========== MODULE WIKI V2.0 - BASE DE CONNAISSANCE PROFESSIONNELLE ==========
# Anciennes routes Wiki V1 supprimées - Utilisation de Wiki V2 avec catégories, likes, historique
from wiki_routes_v2 import register_wiki_routes
register_wiki_routes(app)  # Wiki V2 réactivé avec support PostgreSQL

# ---------- IMPORT DE BASE DE DONNÉES ----------
@app.route("/import_database_preview", methods=["POST"])
def import_database_preview():
    """Analyse le fichier SQLite uploadé et affiche un aperçu avant migration"""
    if "user" not in session or session["role"] != "admin":
        return jsonify({"error": "Accès non autorisé"}), 403
    
    if 'dbFile' not in request.files:
        return jsonify({"error": "Aucun fichier fourni"}), 400
    
    file = request.files['dbFile']
    if file.filename == '':
        return jsonify({"error": "Aucun fichier sélectionné"}), 400
    
    # Vérifier l'extension
    if not file.filename.lower().endswith(('.db', '.sqlite', '.sqlite3')):
        return jsonify({"error": "Format de fichier invalide. Utilisez .db, .sqlite ou .sqlite3"}), 400
    
    try:
        # Sauvegarder temporairement le fichier
        import tempfile
        import sqlite3
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
            file.save(temp_file.name)
            temp_db_path = temp_file.name
        
        # Analyser la structure et les données
        analysis = analyze_sqlite_database(temp_db_path)
        
        # Nettoyer le fichier temporaire
        os.unlink(temp_db_path)
        
        return jsonify(analysis)
        
    except Exception as e:
        # Nettoyer en cas d'erreur
        if 'temp_db_path' in locals():
            try:
                os.unlink(temp_db_path)
            except:
                pass
        return jsonify({"error": f"Erreur lors de l'analyse: {str(e)}"}), 500

@app.route("/import_database_execute", methods=["POST"])
def import_database_execute():
    """Exécute la migration complète avec backup"""
    if "user" not in session or session["role"] != "admin":
        return jsonify({"error": "Accès non autorisé"}), 403
    
    if 'dbFile' not in request.files:
        return jsonify({"error": "Aucun fichier fourni"}), 400
    
    file = request.files['dbFile']
    
    try:
        import tempfile
        import sqlite3
        import subprocess
        from datetime import datetime
        
        # Sauvegarder temporairement le fichier
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
            file.save(temp_file.name)
            temp_db_path = temp_file.name
        
        # Créer un backup PostgreSQL
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"/app/data/backup_postgres_{timestamp}.sql"
        
        try:
            # Backup avec pg_dump (utiliser les variables d'environnement pour l'auth)
            env = os.environ.copy()
            env['PGPASSWORD'] = 'dispatch_pass'
            subprocess.run([
                'pg_dump', '-h', 'postgres', '-U', 'dispatch_user', 
                '-d', 'dispatch', '-f', backup_file
            ], check=True, capture_output=True, env=env)
        except subprocess.CalledProcessError as e:
            return jsonify({"error": f"Erreur lors du backup PostgreSQL: {e.stderr.decode()}"}), 500
        
        # Exécuter la migration
        migration_result = migrate_sqlite_to_postgres(temp_db_path)
        
        # Nettoyer le fichier temporaire
        os.unlink(temp_db_path)
        
        if migration_result['success']:
            return jsonify({
                "success": True,
                "message": "Migration réussie",
                "backup_file": backup_file,
                "migration_details": migration_result
            })
        else:
            # Restaurer le backup en cas d'échec
            try:
                env = os.environ.copy()
                env['PGPASSWORD'] = 'dispatch_pass'
                subprocess.run([
                    'psql', '-h', 'postgres', '-U', 'dispatch_user', 
                    '-d', 'dispatch', '-f', backup_file
                ], check=True, capture_output=True, env=env)
            except:
                pass  # Si la restauration échoue aussi, on ne peut rien faire de plus
            
            return jsonify({"error": f"Migration échouée: {migration_result['error']}"}), 500
            
    except Exception as e:
        # Nettoyer en cas d'erreur
        if 'temp_db_path' in locals():
            try:
                os.unlink(temp_db_path)
            except:
                pass
        return jsonify({"error": f"Erreur lors de la migration: {str(e)}"}), 500

def analyze_sqlite_database(db_path):
    """Analyse la structure et les données d'une base SQLite"""
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tables attendues
    expected_tables = ['incidents', 'techniciens', 'users', 'historique', 'priorites', 'sites', 'statuts', 'sujets']
    
    # Récupérer les tables existantes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    # Vérifier les tables manquantes
    missing_tables = set(expected_tables) - set(existing_tables)
    extra_tables = set(existing_tables) - set(expected_tables)
    
    # Compter les lignes par table
    table_counts = {}
    for table in existing_tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            table_counts[table] = cursor.fetchone()[0]
        except:
            table_counts[table] = "Erreur"
    
    conn.close()
    
    return {
        'valid': len(missing_tables) == 0,
        'missing_tables': list(missing_tables),
        'extra_tables': list(extra_tables),
        'table_counts': table_counts,
        'total_tables': len(existing_tables),
        'expected_tables': len(expected_tables)
    }

def migrate_sqlite_to_postgres(sqlite_db_path):
    """Utilise la logique existante de migration"""
    try:
        # Importer le script de migration existant
        import sys
        sys.path.append('/app')
        from maintenance.migrations.migrate_sqlite_to_postgres import migrate

        # Adapter le script pour utiliser notre fichier temporaire
        # Modifier la variable globale du chemin SQLite
        import maintenance.migrations.migrate_sqlite_to_postgres as migrate_module
        migrate_module.SQLITE_DB_PATH = sqlite_db_path
        
        result = migrate()
        return {'success': True, 'details': result}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    # Mode production : debug désactivé pour la stabilité
    is_development = os.environ.get("FLASK_ENV") == "development"
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=5000, 
        debug=is_development,
        log_output=not is_development
    )