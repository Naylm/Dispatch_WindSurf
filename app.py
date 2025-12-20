# Monkey-patch eventlet en PREMIER pour éviter les problèmes DNS et autres
import eventlet
eventlet.monkey_patch()

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
app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken', 'X-CSRF-Token']  # Accepter les tokens CSRF via headers

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

# SocketIO optimisé pour synchronisation temps réel
# Avec 1 worker Gunicorn, Redis n'est pas nécessaire pour le broadcast
redis_url = os.environ.get("REDIS_URL")
use_redis = False

# Tester Redis uniquement si configuré et si plus d'1 worker
if redis_url:
    import redis as redis_lib
    try:
        r = redis_lib.from_url(redis_url, socket_timeout=2, socket_connect_timeout=2)
        r.ping()
        use_redis = True
        print(f"✅ Redis connecté : {redis_url}")
    except Exception as e:
        print(f"⚠️ Redis non disponible ({e}), fonctionnement en mode single-worker")

socketio = SocketIO(
    app, 
    async_mode="eventlet",
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1000000,
    logger=True,  # Activer les logs pour déboguer
    engineio_logger=True,  # Activer les logs Engine.IO
    allow_upgrades=True,
    transports=['polling', 'websocket'],
    manage_session=False,  # Ne pas gérer les sessions Flask pour éviter les conflits
    message_queue=redis_url if use_redis else None  # Redis pour multi-workers
)

# Gestionnaires Socket.IO
@socketio.on('connect')
def handle_connect(auth):
    """Gestionnaire de connexion Socket.IO"""
    # Ne pas vérifier la session Flask pour éviter les erreurs "Invalid session"
    app.logger.info(f"✅ Client Socket.IO connecté: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Gestionnaire de déconnexion Socket.IO"""
    app.logger.info(f"❌ Client Socket.IO déconnecté: {request.sid}")

@socketio.on('join')
def handle_join(data):
    """Gestionnaire pour rejoindre une room"""
    room = data.get('room')
    if room:
        join_room(room)
        app.logger.info(f"📦 Client {request.sid} a rejoint la room: {room}")
    else:
        app.logger.warning(f"⚠️ Tentative de join sans room de la part de {request.sid}")

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
    # Convertir les DualAccessRow en dictionnaires pour éviter les problèmes de sérialisation
    priorites_rows = db.execute("SELECT * FROM priorites ORDER BY nom").fetchall()
    sites_rows = db.execute("SELECT * FROM sites ORDER BY nom").fetchall()
    statuts_rows = db.execute("SELECT * FROM statuts ORDER BY nom").fetchall()
    sujets_rows = db.execute("SELECT * FROM sujets ORDER BY nom").fetchall()
    
    data = {
        'priorites': [dict(row) for row in priorites_rows],
        'sites': [dict(row) for row in sites_rows],
        'statuts': [dict(row) for row in statuts_rows],
        'sujets': [dict(row) for row in sujets_rows]
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

    # Récupérer les informations du technicien connecté pour l'affichage
    user_display_name = session["user"].capitalize()
    current_tech_id = None

    if session.get("user_type") == "technicien":
        tech = db.execute(
            "SELECT id, prenom, nom FROM techniciens WHERE username=%s",
            (session["user"],)
        ).fetchone()
        if tech:
            current_tech_id = tech['id']
            user_display_name = tech['prenom']  # Utiliser le prénom pour l'affichage

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
        # Utiliser technicien_id au lieu de collaborateur (avec fallback sur collaborateur pour compatibilité)
        if current_tech_id:
            incidents = db.execute(
                "SELECT * FROM incidents WHERE technicien_id=%s AND archived=0 "
                "ORDER BY id ASC",
                (current_tech_id,),
            ).fetchall()
        else:
            # Fallback pour les utilisateurs non-techniciens ou anciens systèmes
            incidents = db.execute(
                "SELECT * FROM incidents WHERE collaborateur=%s AND archived=0 "
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
        user=user_display_name,
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

    # Récupérer les informations du technicien connecté
    current_tech_id = None
    if session.get("user_type") == "technicien":
        tech = db.execute(
            "SELECT id FROM techniciens WHERE username=%s",
            (session["user"],)
        ).fetchone()
        if tech:
            current_tech_id = tech['id']

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
        # Utiliser technicien_id au lieu de collaborateur
        if current_tech_id:
            incidents = db.execute(
                "SELECT * FROM incidents WHERE technicien_id=%s AND archived=0 "
                "ORDER BY id ASC",
                (current_tech_id,),
            ).fetchall()
        else:
            # Fallback pour compatibilité
            incidents = db.execute(
                "SELECT * FROM incidents WHERE collaborateur=%s AND archived=0 "
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


@app.route("/api/incident/<int:id>")
def api_incident(id):
    """API pour récupérer le HTML d'un seul incident (pour rechargement partiel)"""
    if "user" not in session:
        return "", 403
    
    db = get_db()
    
    # Récupérer l'incident
    incident = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()
    
    if not incident:
        return "", 404
    
    # Vérifier les permissions (technicien ne peut voir que ses incidents)
    if session.get("user_type") == "technicien":
        current_tech_id = None
        tech = db.execute(
            "SELECT id FROM techniciens WHERE username=%s",
            (session["user"],)
        ).fetchone()
        if tech:
            current_tech_id = tech['id']
        
        # Vérifier que l'incident appartient au technicien
        if current_tech_id and incident.get("technicien_id") != current_tech_id:
            # Fallback pour compatibilité
            if incident.get("collaborateur") != session["user"]:
                return "", 403
    
    # Récupérer les données de référence
    ref_data = get_reference_data()
    priorites = ref_data['priorites']
    sites = ref_data['sites']
    statuts = ref_data['statuts']
    
    # Récupérer les techniciens (pour le select)
    if session["role"] == "admin":
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


# ---------- ANNuaire DES TECHNICIENS (Accessible à tous) ----------
@app.route("/annuaire")
def annuaire():
    """Annuaire des techniciens accessible à tous les utilisateurs"""
    if "user" not in session:
        return redirect(url_for("login"))

    db = get_db()
    # Récupérer les techniciens actifs (y compris les admins dans la table techniciens)
    techniciens_list = db.execute("""
        SELECT id, nom, prenom, dect_number, email, actif, role, ordre
        FROM techniciens 
        WHERE actif=%s 
        ORDER BY ordre ASC, prenom ASC
    """, (1,)).fetchall()
    
    # Récupérer les admins de la table users (comme Melvin)
    admins_users = db.execute("""
        SELECT id, NULL as nom, username as prenom, NULL as dect_number, NULL as email, 1 as actif, role, 0 as ordre
        FROM users 
        WHERE role='admin'
    """).fetchall()
    
    # Combiner les deux listes
    all_people = list(techniciens_list) + list(admins_users)
    
    # Trier par ordre puis prénom
    all_people.sort(key=lambda x: (x.get('ordre', 0), x.get('prenom', '')))
    
    return render_template("annuaire.html", techniciens=all_people, role=session.get("role"))


# ---------- PROFIL UTILISATEUR ----------
@app.route("/profil")
def profil():
    """Page de profil utilisateur (technicien ou admin)"""
    if "user" not in session:
        return redirect(url_for("login"))
    
    db = get_db()
    username = session["user"]
    user_type = session.get("user_type", "user")
    
    # Récupérer les données de l'utilisateur
    if user_type == "technicien":
        user_data = db.execute("""
            SELECT id, nom, prenom, username, email, dect_number, role, photo_profil, created_at
            FROM techniciens 
            WHERE (username=%s OR prenom=%s) AND actif=1
        """, (username, username)).fetchone()
    else:
        # Pour les admins de la table users
        user_data = db.execute("""
            SELECT id, 
                   COALESCE(nom, NULL) as nom, 
                   COALESCE(prenom, username) as prenom, 
                   username, 
                   COALESCE(email, NULL) as email, 
                   COALESCE(dect_number, NULL) as dect_number, 
                   role, 
                   COALESCE(photo_profil, NULL) as photo_profil, 
                   NULL as created_at
            FROM users 
            WHERE username=%s
        """, (username,)).fetchone()
    
    db.close()
    
    if not user_data:
        flash("Utilisateur introuvable", "danger")
        return redirect(url_for("home"))
    
    return render_template("profil.html", user_data=dict(user_data), role=session.get("role"))


@app.route("/profil/update_info", methods=["POST"])
def update_profile_info():
    """Mise à jour des informations de profil (nom, prénom, téléphone, email)"""
    if "user" not in session:
        return redirect(url_for("login"))
    
    nom = request.form.get("nom", "").strip()
    prenom = request.form.get("prenom", "").strip()
    dect_number = request.form.get("dect_number", "").strip()
    email = request.form.get("email", "").strip()
    
    db = get_db()
    username = session["user"]
    user_type = session.get("user_type", "user")
    role = session.get("role", "")
    
    try:
        if user_type == "technicien":
            # Les techniciens ne peuvent modifier que téléphone et email (nom/prénom gérés par admin)
            db.execute("""
                UPDATE techniciens 
                SET dect_number=%s, email=%s
                WHERE (username=%s OR prenom=%s)
            """, (dect_number, email, username, username))
        else:
            # Pour les admins de la table users - peuvent modifier nom, prénom, téléphone et email
            if not prenom:
                flash("Le prénom est obligatoire", "danger")
                db.close()
                return redirect(url_for("profil"))
            
            db.execute("""
                UPDATE users 
                SET nom=%s, prenom=%s, dect_number=%s, email=%s
                WHERE username=%s
            """, (nom if nom else None, prenom, dect_number if dect_number else None, email if email else None, username))
        
        db.commit()
        flash("Informations mises à jour avec succès!", "success")
    except Exception as e:
        db.rollback()
        app.logger.error(f"Erreur mise à jour profil: {e}")
        flash("Erreur lors de la mise à jour", "danger")
    finally:
        db.close()
    
    return redirect(url_for("profil"))


@app.route("/profil/update_password", methods=["POST"])
def update_profile_password():
    """Changement de mot de passe par l'utilisateur"""
    if "user" not in session:
        return redirect(url_for("login"))
    
    current_password = request.form.get("current_password", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()
    
    # Validations
    if not current_password or not new_password or not confirm_password:
        flash("Tous les champs sont obligatoires", "danger")
        return redirect(url_for("profil"))
    
    if new_password != confirm_password:
        flash("Les mots de passe ne correspondent pas", "danger")
        return redirect(url_for("profil"))
    
    if len(new_password) < 8:
        flash("Le mot de passe doit contenir au moins 8 caractères", "danger")
        return redirect(url_for("profil"))
    
    db = get_db()
    username = session["user"]
    user_type = session.get("user_type", "user")
    
    try:
        # Récupérer l'utilisateur
        if user_type == "technicien":
            user = db.execute("""
                SELECT id, password FROM techniciens 
                WHERE (username=%s OR prenom=%s) AND actif=1
            """, (username, username)).fetchone()
        else:
            user = db.execute("SELECT id, password FROM users WHERE username=%s", (username,)).fetchone()
        
        if not user:
            db.close()
            flash("Utilisateur introuvable", "danger")
            return redirect(url_for("profil"))
        
        # Vérifier le mot de passe actuel
        is_password_hashed = user["password"] and (user["password"].startswith("pbkdf2:") or user["password"].startswith("scrypt:"))
        
        if is_password_hashed:
            password_valid = check_password_hash(user["password"], current_password)
        else:
            password_valid = (user["password"] == current_password)
        
        if not password_valid:
            db.close()
            flash("Mot de passe actuel incorrect", "danger")
            return redirect(url_for("profil"))
        
        # Hasher le nouveau mot de passe
        hashed_password = generate_password_hash(new_password)
        
        # Mettre à jour
        if user_type == "technicien":
            db.execute("UPDATE techniciens SET password=%s WHERE id=%s", (hashed_password, user["id"]))
        else:
            db.execute("UPDATE users SET password=%s WHERE id=%s", (hashed_password, user["id"]))
        
        db.commit()
        app.logger.info(f"Mot de passe modifié pour {username}")
        flash("Mot de passe modifié avec succès!", "success")
        
    except Exception as e:
        db.rollback()
        app.logger.error(f"Erreur changement mot de passe: {e}")
        flash("Erreur lors du changement de mot de passe", "danger")
    finally:
        db.close()
    
    return redirect(url_for("profil"))


@app.route("/profil/update_photo", methods=["POST"])
def update_profile_photo():
    """Mise à jour de la photo de profil"""
    if "user" not in session:
        return redirect(url_for("login"))
    
    if 'photo' not in request.files:
        flash("Aucun fichier sélectionné", "danger")
        return redirect(url_for("profil"))
    
    file = request.files['photo']
    
    if file.filename == '':
        flash("Aucun fichier sélectionné", "danger")
        return redirect(url_for("profil"))
    
    # Extensions autorisées
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    if not allowed_file(file.filename):
        flash("Type de fichier non autorisé (PNG, JPG, GIF, WEBP uniquement)", "danger")
        return redirect(url_for("profil"))
    
    # Créer le dossier d'avatars si nécessaire
    import uuid
    UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads', 'avatars')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Générer un nom de fichier unique
    from werkzeug.utils import secure_filename
    file_extension = secure_filename(file.filename).rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    try:
        file.save(filepath)
        
        db = get_db()
        username = session["user"]
        user_type = session.get("user_type", "user")
        
        if user_type == "technicien":
            # Supprimer l'ancienne photo si elle existe
            old_photo = db.execute("""
                SELECT photo_profil FROM techniciens 
                WHERE (username=%s OR prenom=%s)
            """, (username, username)).fetchone()
            
            if old_photo and old_photo.get("photo_profil"):
                old_path = os.path.join(UPLOAD_FOLDER, old_photo["photo_profil"])
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            db.execute("""
                UPDATE techniciens SET photo_profil=%s
                WHERE (username=%s OR prenom=%s)
            """, (unique_filename, username, username))
        else:
            # Pour les admins de la table users
            # Supprimer l'ancienne photo si elle existe
            old_photo = db.execute("""
                SELECT photo_profil FROM users 
                WHERE username=%s
            """, (username,)).fetchone()
            
            if old_photo and old_photo.get("photo_profil"):
                old_path = os.path.join(UPLOAD_FOLDER, old_photo["photo_profil"])
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            db.execute("""
                UPDATE users SET photo_profil=%s
                WHERE username=%s
            """, (unique_filename, username))
        
        db.commit()
        flash("Photo de profil mise à jour!", "success")
        
    except Exception as e:
        app.logger.error(f"Erreur upload photo: {e}")
        flash("Erreur lors de l'upload de la photo", "danger")
        # Supprimer le fichier si l'upload a échoué
        if os.path.exists(filepath):
            os.remove(filepath)
    finally:
        db.close()
    
    return redirect(url_for("profil"))


@app.route("/profil/delete_photo", methods=["POST"])
def delete_profile_photo():
    """Suppression de la photo de profil"""
    if "user" not in session:
        return redirect(url_for("login"))
    
    db = get_db()
    username = session["user"]
    user_type = session.get("user_type", "user")
    
    try:
        # Récupérer le nom de la photo actuelle
        if user_type == "technicien":
            user = db.execute("""
                SELECT photo_profil FROM techniciens 
                WHERE (username=%s OR prenom=%s)
            """, (username, username)).fetchone()
        else:
            user = db.execute("""
                SELECT photo_profil FROM users 
                WHERE username=%s
            """, (username,)).fetchone()
        
        if not user:
            db.close()
            flash("Utilisateur introuvable", "danger")
            return redirect(url_for("profil"))
        
        # Supprimer le fichier physique si il existe
        if user.get("photo_profil"):
            UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads', 'avatars')
            photo_path = os.path.join(UPLOAD_FOLDER, user["photo_profil"])
            if os.path.exists(photo_path):
                try:
                    os.remove(photo_path)
                except Exception as e:
                    app.logger.warning(f"Impossible de supprimer le fichier photo: {e}")
        
        # Mettre à jour la base de données
        if user_type == "technicien":
            db.execute("""
                UPDATE techniciens SET photo_profil=NULL
                WHERE (username=%s OR prenom=%s)
            """, (username, username))
        else:
            db.execute("""
                UPDATE users SET photo_profil=NULL
                WHERE username=%s
            """, (username,))
        
        db.commit()
        flash("Photo de profil supprimée avec succès!", "success")
        
    except Exception as e:
        db.rollback()
        app.logger.error(f"Erreur suppression photo: {e}")
        flash("Erreur lors de la suppression de la photo", "danger")
    finally:
        db.close()
    
    return redirect(url_for("profil"))


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

    # Récupérer tous les champs du formulaire
    nom = request.form.get("nom", "").strip()
    prenom = request.form.get("prenom", "").strip()
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    dect_number = request.form.get("dect_number", "").strip()
    role = request.form.get("role", "technicien")

    # Validation des champs obligatoires (pas de password dans le formulaire)
    if not all([nom, prenom, username, email]):
        flash("Tous les champs sont obligatoires", "error")
        return redirect(url_for("techniciens"))

    # Mot de passe par défaut : 0000 (sera forcé à changer à la première connexion)
    hashed_password = generate_password_hash("0000")

    db = get_db()
    try:
        # Vérifier l'unicité du username
        existing = db.execute("SELECT id FROM techniciens WHERE username=%s", (username,)).fetchone()
        if existing:
            flash("Ce nom d'utilisateur existe déjà", "error")
            return redirect(url_for("techniciens"))

        # Vérifier l'unicité de l'email
        existing = db.execute("SELECT id FROM techniciens WHERE email=%s", (email,)).fetchone()
        if existing:
            flash("Cet email est déjà utilisé", "error")
            return redirect(url_for("techniciens"))

        # Récupérer le max ordre pour mettre le nouveau technicien à la fin
        max_ordre_result = db.execute("SELECT COALESCE(MAX(ordre), 0) as max_ordre FROM techniciens").fetchone()
        new_ordre = (max_ordre_result['max_ordre'] if max_ordre_result else 0) + 1

        # Insérer le nouveau technicien avec force_password_reset=1 pour forcer le changement à la première connexion
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

    return redirect(url_for("techniciens"))


@app.route("/technicien/edit/<int:id>", methods=["POST"])
def edit_technicien(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    # Récupérer tous les champs du formulaire
    nom = request.form.get("nom", "").strip()
    prenom = request.form.get("prenom", "").strip()
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    dect_number = request.form.get("dect_number", "").strip()
    role = request.form.get("role", "technicien")
    new_pass = request.form.get("password", "").strip()

    # Validation des champs obligatoires (sauf password qui est optionnel en édition)
    if not all([nom, prenom, username, email]):
        flash("Les champs nom, prénom, username et email sont obligatoires", "error")
        return redirect(url_for("techniciens"))

    if new_pass and len(new_pass) < 8:
        flash("Le mot de passe doit contenir au moins 8 caractères", "error")
        return redirect(url_for("techniciens"))

    db = get_db()
    try:
        # Vérifier l'unicité du username (sauf pour l'utilisateur actuel)
        existing = db.execute("SELECT id FROM techniciens WHERE username=%s AND id!=%s", (username, id)).fetchone()
        if existing:
            flash("Ce nom d'utilisateur existe déjà", "error")
            return redirect(url_for("techniciens"))

        # Vérifier l'unicité de l'email (sauf pour l'utilisateur actuel)
        existing = db.execute("SELECT id FROM techniciens WHERE email=%s AND id!=%s", (email, id)).fetchone()
        if existing:
            flash("Cet email est déjà utilisé", "error")
            return redirect(url_for("techniciens"))

        # Mise à jour avec ou sans nouveau mot de passe
        if new_pass:
            # Hash du nouveau mot de passe
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

    return redirect(url_for("techniciens"))


@app.route("/technicien/incidents/<int:id>")
def technicien_incidents(id):
    if "user" not in session or session["role"] != "admin":
        return "", 403

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


@app.route("/technicien/transfer_delete/<int:id>", methods=["POST"])
def transfer_and_delete_technicien(id):
    if "user" not in session or session["role"] != "admin":
        return "", 403

    db = get_db()
    tech = db.execute("SELECT prenom FROM techniciens WHERE id=%s", (id,)).fetchone()
    if not tech:
        return jsonify({"status": "error", "message": "Tech introuvable"}), 404

    # Ré-affecter chaque incident sélectionné, si applicable
    for key, value in request.form.items():
        if key.startswith("incident_"):
            incident_id = int(key.split("_")[1])
            nouveau_collab = value
            db.execute(
                "UPDATE incidents SET collaborateur=%s WHERE id=%s", (nouveau_collab, incident_id)
            )

    # Puis supprimer le technicien
    db.execute("DELETE FROM techniciens WHERE id=%s", (id,))
    db.commit()
    return jsonify({"status": "ok"})


@app.route("/technicien/delete/<int:id>", methods=["POST"])
def delete_technicien(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM techniciens WHERE id=%s", (id,))
    db.commit()
    return redirect(url_for("techniciens"))


@app.route("/toggle_technicien/<int:id>", methods=["POST"])
def toggle_technicien(id):
    """Active ou désactive un technicien"""
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    # Récupérer l'état actuel
    technicien = db.execute("SELECT actif FROM techniciens WHERE id=%s", (id,)).fetchone()
    
    if technicien:
        # Inverser l'état (1 devient 0, 0 devient 1)
        new_state = 0 if technicien['actif'] == 1 else 1
        db.execute("UPDATE techniciens SET actif=%s WHERE id=%s", (new_state, id))
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
            db.execute("UPDATE techniciens SET ordre=%s WHERE id=%s", (index, tech_id))
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

    db = None
    try:
        db = get_db()

        # Récupérer les données de l'incident AVANT modification
        incident = db.execute("SELECT * FROM incidents WHERE id=%s", (incident_id,)).fetchone()
        if not incident:
            return jsonify({"status": "error", "message": "Incident introuvable"}), 404

        old_collab = incident['collaborateur']

        # PostgreSQL gère automatiquement les transactions, pas besoin de BEGIN explicite
        db.execute(
            "UPDATE incidents SET collaborateur=%s WHERE id=%s", (new_collab, incident_id)
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
        if db is not None:
            db.rollback()
        app.logger.error(f"Erreur assign_incident: {e}")
        return jsonify({"status": "error", "message": "Erreur serveur"}), 500


@app.route("/export/popup")
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
            # Récupérer les données via db.execute() puis convertir en DataFrame
            rows = db.execute(sql, techs).fetchall()
            if rows:
                # Convertir les DualAccessRow en dictionnaires puis en DataFrame
                data = [dict(row) for row in rows]
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame()

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
    db.execute("INSERT INTO sujets (nom) VALUES (%s)", (nom,))
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
    db.execute("UPDATE sujets SET nom=%s WHERE id=%s", (nom, id))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/sujet/delete/<int:id>", methods=["POST"])
def delete_sujet(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM sujets WHERE id=%s", (id,))
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
    db.execute("INSERT INTO priorites (nom, couleur, niveau) VALUES (%s, %s, %s)", (nom, couleur, niveau))
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
    db.execute("UPDATE priorites SET nom=%s, couleur=%s, niveau=%s WHERE id=%s", (nom, couleur, niveau, id))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/priorite/delete/<int:id>", methods=["POST"])
def delete_priorite(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM priorites WHERE id=%s", (id,))
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
    db.execute("INSERT INTO sites (nom, couleur) VALUES (%s, %s)", (nom, couleur))
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
    db.execute("UPDATE sites SET nom=%s, couleur=%s WHERE id=%s", (nom, couleur, id))
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/site/delete/<int:id>", methods=["POST"])
def delete_site(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM sites WHERE id=%s", (id,))
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
    has_relances = request.form.get("has_relances") == "1"
    has_rdv = request.form.get("has_rdv") == "1"

    db = get_db()
    db.execute(
        "INSERT INTO statuts (nom, couleur, category, has_relances, has_rdv) VALUES (%s, %s, %s, %s, %s)",
        (nom, couleur, category, has_relances, has_rdv)
    )
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
    has_relances = request.form.get("has_relances") == "1"
    has_rdv = request.form.get("has_rdv") == "1"

    db = get_db()
    db.execute(
        "UPDATE statuts SET nom=%s, couleur=%s, category=%s, has_relances=%s, has_rdv=%s WHERE id=%s",
        (nom, couleur, category, has_relances, has_rdv, id)
    )
    db.commit()
    invalidate_reference_cache()  # Invalider le cache
    return redirect(url_for("configuration"))


@app.route("/configuration/statut/delete/<int:id>", methods=["POST"])
def delete_statut(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM statuts WHERE id=%s", (id,))
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
                "UPDATE users SET force_password_reset=1 WHERE username=%s",
                (username,)
            )
        else:  # technicien
            db.execute(
                "UPDATE techniciens SET force_password_reset=1 WHERE (username=%s OR prenom=%s)",
                (username, username)
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

        # 1) Essayer dans users (insensible à la casse)
        user = db.execute(
            "SELECT * FROM users WHERE LOWER(username)=LOWER(%s)", (u,)
        ).fetchone()
        if user:
            app.logger.debug(f"Tentative de connexion pour l'utilisateur: {u}")
            # Vérifier le mot de passe hashé ou en clair (pour compatibilité)
            password_valid = False
            is_password_hashed = user["password"] and (user["password"].startswith("pbkdf2:") or user["password"].startswith("scrypt:"))
            
            if is_password_hashed:
                # Mot de passe hashé - vérifier avec check_password_hash
                password_valid = check_password_hash(user["password"], p)
            elif user["password"]:
                # Mot de passe en clair - vérifier directement (compatibilité)
                password_valid = (user["password"] == p)
            
            if password_valid:
                # Utiliser le username exact de la base de données (pas celui saisi)
                session["user"] = user["username"]
                session["role"] = user["role"]
                session["user_type"] = "user"  # Pour savoir quelle table
                session.permanent = True
                app.logger.info(f"Connexion réussie: {user['username']} (role: {user['role']})")

                # Vérifier si réinitialisation forcée requise ou si mot de passe en clair
                try:
                    force_reset = user["force_password_reset"]
                except (KeyError, IndexError):
                    force_reset = 0

                # Forcer la réinitialisation si le mot de passe n'est pas hashé
                if not is_password_hashed:
                    force_reset = 1
                    # Mettre à jour le flag dans la base
                    db.execute("UPDATE users SET force_password_reset=1 WHERE username=%s", (user["username"],))
                    db.commit()

                db.close()
                if force_reset == 1:
                    session["force_password_reset"] = True
                    app.logger.info(f"Réinitialisation forcée requise pour {user['username']}")
                    return redirect(url_for("change_password_forced"))

                return redirect(url_for("home"))
            else:
                app.logger.warning(f"Échec de connexion pour {u}: mot de passe incorrect")
                db.close()
                flash("Mauvais identifiants", "danger")
                return render_template("login.html")

        # 2) Sinon, essayer dans techniciens (recherche par username, insensible à la casse)
        tech = db.execute("""
            SELECT * FROM techniciens
            WHERE LOWER(username)=LOWER(%s) AND actif=1
        """, (u,)).fetchone()

        if tech and tech["password"]:
            app.logger.debug(f"Tentative de connexion pour le technicien: {u}")
            # Vérifier le mot de passe hashé ou en clair (pour compatibilité)
            password_valid = False
            is_password_hashed = tech["password"].startswith("pbkdf2:") or tech["password"].startswith("scrypt:")
            
            if is_password_hashed:
                # Mot de passe hashé - vérifier avec check_password_hash
                password_valid = check_password_hash(tech["password"], p)
            else:
                # Mot de passe en clair - vérifier directement (compatibilité)
                password_valid = (tech["password"] == p)
            
            if password_valid:
                # Utiliser le username exact de la base de données
                session["user"] = tech["username"]
                session["role"] = tech["role"] or "technicien"
                session["user_type"] = "technicien"  # Pour savoir quelle table
                session["user_display_name"] = f"{tech['prenom']} {tech['nom']}".strip()
                session.permanent = True
                app.logger.info(f"Connexion technicien réussie: {tech['username']}")

                # Vérifier si réinitialisation forcée requise ou si mot de passe en clair
                try:
                    force_reset = tech["force_password_reset"]
                except (KeyError, IndexError):
                    force_reset = 0

                # Forcer la réinitialisation si le mot de passe n'est pas hashé
                if not is_password_hashed:
                    force_reset = 1
                    # Mettre à jour le flag dans la base
                    db.execute("UPDATE techniciens SET force_password_reset=1 WHERE id=%s", (tech["id"],))
                    db.commit()

                db.close()
                if force_reset == 1:
                    session["force_password_reset"] = True
                    app.logger.info(f"Réinitialisation forcée requise pour technicien {tech['username']}")
                    return redirect(url_for("change_password_forced"))

                return redirect(url_for("home"))
            else:
                app.logger.warning(f"Échec de connexion pour technicien {u}: mot de passe incorrect")
                db.close()
                flash("Mauvais identifiants", "danger")
                return render_template("login.html")
        elif tech and not tech["password"]:
            # Technicien sans mot de passe - refuser la connexion
            app.logger.error(f"Échec de connexion pour technicien {u}: aucun mot de passe défini")
            db.close()
            flash("Aucun mot de passe défini. Contactez l'administrateur.", "danger")
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
            user = db.execute("SELECT * FROM users WHERE username=%s", (username,)).fetchone()
        else:
            # Pour les techniciens, chercher par username (qui peut être username ou prenom)
            user = db.execute("SELECT * FROM techniciens WHERE (username=%s OR prenom=%s) AND actif=1", (username, username)).fetchone()

        if not user:
            db.close()
            flash("Utilisateur introuvable", "danger")
            return redirect(url_for("logout"))

        # Vérifier le mot de passe actuel (hashé ou en clair)
        password_valid = False
        is_password_hashed = user["password"] and (user["password"].startswith("pbkdf2:") or user["password"].startswith("scrypt:"))
        
        if is_password_hashed:
            password_valid = check_password_hash(user["password"], current_password)
        else:
            password_valid = (user["password"] == current_password)
        
        if not password_valid:
            db.close()
            flash("Mot de passe actuel incorrect", "danger")
            return render_template("change_password_forced.html")

        # Vérifier que le nouveau mot de passe est différent
        new_is_same = False
        if is_password_hashed:
            new_is_same = check_password_hash(user["password"], new_password)
        else:
            new_is_same = (user["password"] == new_password)
        
        if new_is_same:
            db.close()
            flash("Le nouveau mot de passe doit être différent de l'ancien", "danger")
            return render_template("change_password_forced.html")

        # Hasher le nouveau mot de passe
        hashed_password = generate_password_hash(new_password)

        # Mettre à jour le mot de passe et réinitialiser le flag
        if user_type == "user":
            db.execute(
                "UPDATE users SET password=%s, force_password_reset=0 WHERE username=%s",
                (hashed_password, username)
            )
        else:
            # Pour les techniciens, utiliser l'ID si disponible, sinon username/prenom
            tech_id = user.get("id")
            if tech_id:
                db.execute(
                    "UPDATE techniciens SET password=%s, force_password_reset=0 WHERE id=%s",
                    (hashed_password, tech_id)
                )
            else:
                db.execute(
                    "UPDATE techniciens SET password=%s, force_password_reset=0 WHERE (username=%s OR prenom=%s)",
                    (hashed_password, username, username)
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
        technicien_id = int(request.form["technicien_id"])
        date_aff = request.form["date_affectation"]
        note_dispatch = request.form.get("note_dispatch", "")
        localisation = request.form.get("localisation", "")

        # Récupérer le prénom du technicien pour collaborateur (rétrocompatibilité) et notification
        tech = db.execute("SELECT prenom FROM techniciens WHERE id=%s", (technicien_id,)).fetchone()
        collab_prenom = tech['prenom'] if tech else "Non affecté"

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

        # Émettre la notification de nouveau ticket (utiliser le prénom pour compatibilité)
        emit_new_assignment_notification(socketio, incident_data, collab_prenom)

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
    incident = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()
    if not incident:
        return jsonify({"error": "Incident introuvable"}), 404

    # Enregistrement dans l'historique avant suppression
    hist_sql = """
      INSERT INTO historique (
        incident_id, champ, ancienne_valeur,
        nouvelle_valeur, modifie_par, date_modification
      ) VALUES (%s, %s, %s, %s, %s, %s)
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
        db.execute("DELETE FROM incidents WHERE id=%s", (id,))
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
    incident = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()
    if not incident:
        flash("Incident introuvable", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        numero = request.form["numero"].strip()
        site = request.form["site"].strip()
        sujet = request.form["sujet"].strip()
        urgence = request.form["urgence"].strip()
        technicien_id = int(request.form["technicien_id"])
        etat = request.form["etat"].strip()
        notes = request.form.get("notes", "").strip()
        note_dispatch = request.form.get("note_dispatch", "").strip()
        date_aff = request.form["date_affectation"]
        localisation = request.form.get("localisation", "").strip()

        # Récupérer le prénom du technicien pour collaborateur (rétrocompatibilité)
        tech = db.execute("SELECT prenom FROM techniciens WHERE id=%s", (technicien_id,)).fetchone()
        collaborateur = tech['prenom'] if tech else "Non affecté"

        # Mise à jour de l'incident avec protection transactionnelle
        try:
            db.execute("BEGIN")
            db.execute(
                """UPDATE incidents SET numero=%s, site=%s, sujet=%s, urgence=%s,
                   collaborateur=%s, technicien_id=%s, etat=%s, notes=%s, note_dispatch=%s, date_affectation=%s, localisation=%s WHERE id=%s""",
                (numero, site, sujet, urgence, collaborateur, technicien_id, etat, notes, note_dispatch, date_aff, localisation, id)
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
          ) VALUES (%s, %s, %s, %s, %s, %s)
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
    inc = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()
    # Comparaison exacte (sensible à la casse) pour sécurité
    # Vérifier les permissions (technicien propriétaire ou admin)
    if session["role"] != "admin":
        tech = db.execute("SELECT id FROM techniciens WHERE username=%s OR prenom=%s",
                         (session["user"], session["user"])).fetchone()
        if not tech or inc["technicien_id"] != tech["id"]:
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
              ) VALUES (%s, %s, %s, %s, %s, %s)
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
              ) VALUES (%s, %s, %s, %s, %s, %s)
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
            db.execute("UPDATE incidents SET notes=%s, localisation=%s WHERE id=%s", (note, localisation, id))
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
    inc = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()

    if not inc:
        return jsonify({"error": "Incident introuvable"}), 404

    # Vérifier les permissions (technicien propriétaire ou admin)
    # Utiliser technicien_id pour éviter les problèmes de username != prenom
    if session["role"] != "admin":
        # Récupérer l'ID du technicien connecté
        tech = db.execute("SELECT id FROM techniciens WHERE username=%s OR prenom=%s",
                         (session["user"], session["user"])).fetchone()
        if not tech or inc["technicien_id"] != tech["id"]:
            return jsonify({"error": "Permission refusée"}), 403

    new_note = request.json.get("note", "").strip()

    # Vérifier si la note a changé
    if inc["notes"] != new_note:
        # Enregistrer dans l'historique
        hist_sql = """
          INSERT INTO historique (
            incident_id, champ, ancienne_valeur,
            nouvelle_valeur, modifie_par, date_modification
          ) VALUES (%s, %s, %s, %s, %s, %s)
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
        db.execute("UPDATE incidents SET notes=%s WHERE id=%s", (new_note, id))
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
    inc = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()

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
          ) VALUES (%s, %s, %s, %s, %s, %s)
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
        db.execute("UPDATE incidents SET note_dispatch=%s WHERE id=%s", (new_note_dispatch, id))
        db.commit()
        socketio.emit("incident_update", {"action": "note_dispatch_edit"})

        return jsonify({"success": True, "note_dispatch": new_note_dispatch})

    return jsonify({"success": True, "note_dispatch": new_note_dispatch, "unchanged": True})


# ---------- UPDATE RELANCES ----------
@app.route("/api/incident/<int:id>/relances", methods=["POST"])
@csrf.exempt
def update_relances(id):
    """Met à jour les checkboxes de relances d'un incident"""
    if "user" not in session:
        return jsonify({"error": "Non authentifié"}), 401

    db = get_db()
    inc = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()
    
    if not inc:
        return jsonify({"error": "Incident non trouvé"}), 404

    # Récupérer les valeurs depuis le JSON ou form
    data = request.get_json() if request.is_json else request.form
    
    relance_mail = data.get("relance_mail") in [True, "true", "1", 1]
    relance_1 = data.get("relance_1") in [True, "true", "1", 1]
    relance_2 = data.get("relance_2") in [True, "true", "1", 1]
    relance_cloture = data.get("relance_cloture") in [True, "true", "1", 1]

    # Mettre à jour
    db.execute("""
        UPDATE incidents 
        SET relance_mail=%s, relance_1=%s, relance_2=%s, relance_cloture=%s
        WHERE id=%s
    """, (relance_mail, relance_1, relance_2, relance_cloture, id))
    
    # Historique
    changes = []
    if inc.get("relance_mail") != relance_mail:
        changes.append(("relance_mail", str(inc.get("relance_mail")), str(relance_mail)))
    if inc.get("relance_1") != relance_1:
        changes.append(("relance_1", str(inc.get("relance_1")), str(relance_1)))
    if inc.get("relance_2") != relance_2:
        changes.append(("relance_2", str(inc.get("relance_2")), str(relance_2)))
    if inc.get("relance_cloture") != relance_cloture:
        changes.append(("relance_cloture", str(inc.get("relance_cloture")), str(relance_cloture)))
    
    for champ, ancien, nouveau in changes:
        db.execute("""
            INSERT INTO historique (incident_id, champ, ancienne_valeur, nouvelle_valeur, modifie_par, date_modification)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (id, champ, ancien, nouveau, session["user"], datetime.now().strftime("%d-%m-%Y %H:%M")))
    
    db.commit()
    
    # Émettre un événement Socket.IO pour synchroniser tous les clients
    socketio.emit("incident_relances_changed", {
        "id": id,
        "relance_mail": relance_mail,
        "relance_1": relance_1,
        "relance_2": relance_2,
        "relance_cloture": relance_cloture
    })
    
    return jsonify({
        "success": True,
        "relance_mail": relance_mail,
        "relance_1": relance_1,
        "relance_2": relance_2,
        "relance_cloture": relance_cloture
    })


# ---------- UPDATE RDV ----------
@app.route("/api/incident/<int:id>/rdv", methods=["POST"])
@csrf.exempt
def update_rdv(id):
    """Met à jour la date de rendez-vous d'un incident"""
    print(f"📅 UPDATE_RDV appelé pour incident {id}", flush=True)
    
    if "user" not in session:
        print("❌ Non authentifié", flush=True)
        return jsonify({"error": "Non authentifié"}), 401

    db = get_db()
    inc = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()
    
    if not inc:
        print(f"❌ Incident {id} non trouvé", flush=True)
        return jsonify({"error": "Incident non trouvé"}), 404

    # Récupérer la valeur depuis le JSON ou form (avec silent=True pour éviter erreur 400)
    try:
        data = request.get_json(force=True, silent=True) or request.form or {}
    except Exception as e:
        print(f"❌ Erreur parsing JSON: {e}", flush=True)
        data = request.form or {}
    
    date_rdv_str = data.get("date_rdv", "").strip() if data else ""
    print(f"📅 Date reçue: '{date_rdv_str}'", flush=True)
    
    # Convertir en datetime ou None
    date_rdv = None
    if date_rdv_str:
        try:
            date_rdv = datetime.fromisoformat(date_rdv_str.replace("Z", "+00:00"))
        except ValueError:
            try:
                date_rdv = datetime.strptime(date_rdv_str, "%Y-%m-%dT%H:%M")
            except ValueError:
                return jsonify({"error": "Format de date invalide"}), 400

    # Mettre à jour
    db.execute("UPDATE incidents SET date_rdv=%s WHERE id=%s", (date_rdv, id))
    
    # Historique
    old_rdv = inc.get("date_rdv")
    old_rdv_str = old_rdv.strftime("%d/%m/%Y %H:%M") if old_rdv else "Non défini"
    new_rdv_str = date_rdv.strftime("%d/%m/%Y %H:%M") if date_rdv else "Non défini"
    
    if old_rdv_str != new_rdv_str:
        db.execute("""
            INSERT INTO historique (incident_id, champ, ancienne_valeur, nouvelle_valeur, modifie_par, date_modification)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (id, "date_rdv", old_rdv_str, new_rdv_str, session["user"], datetime.now().strftime("%d-%m-%Y %H:%M")))
    
    db.commit()
    print(f"✅ RDV sauvegardé pour incident {id}: {date_rdv}", flush=True)
    
    # Émettre un événement Socket.IO pour synchroniser tous les clients
    socketio.emit("incident_rdv_changed", {
        "id": id,
        "date_rdv": date_rdv.isoformat() if date_rdv else None,
        "date_rdv_formatted": date_rdv.strftime("%d/%m/%Y %H:%M") if date_rdv else None,
        "date_rdv_input": date_rdv.strftime("%Y-%m-%dT%H:%M") if date_rdv else ""
    })
    print(f"📡 Événement incident_rdv_changed émis", flush=True)
    
    return jsonify({
        "success": True,
        "date_rdv": date_rdv.isoformat() if date_rdv else None,
        "date_rdv_formatted": date_rdv.strftime("%d/%m/%Y %H:%M") if date_rdv else None,
        "date_rdv_input": date_rdv.strftime("%Y-%m-%dT%H:%M") if date_rdv else ""
    })


# ---------- UPDATE ETAT ----------
@app.route("/update_etat/<int:id>", methods=["POST"])
def update_etat(id):
    if "user" not in session:
        return redirect(url_for("login"))

    db = get_db()
    try:
        # PostgreSQL gère automatiquement les transactions, pas besoin de BEGIN explicite
        inc = db.execute("SELECT * FROM incidents WHERE id=%s", (id,)).fetchone()
        new = request.form["etat"]

        if inc["etat"] != new:
            db.execute("UPDATE incidents SET etat=%s WHERE id=%s", (new, id))
            hist_sql = """
              INSERT INTO historique (
                incident_id, champ, ancienne_valeur,
                nouvelle_valeur, modifie_par, date_modification
              ) VALUES (%s, %s, %s, %s, %s, %s)
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
            # Récupérer le prénom de l'utilisateur qui fait le changement
            changed_by = session["user"]  # Par défaut le username
            if session.get("user_type") == "technicien":
                tech_info = db.execute(
                    "SELECT prenom FROM techniciens WHERE username=%s",
                    (session["user"],)
                ).fetchone()
                if tech_info:
                    changed_by = tech_info["prenom"]
            
            # Toujours émettre la notification (l'admin doit tout recevoir)
            # Le filtrage côté client exclura le technicien s'il est l'auteur
            emit_status_change_notification(
                socketio,
                id,
                inc["numero"],
                inc["etat"],
                new,
                inc["collaborateur"],
                changed_by  # Qui a fait le changement
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

        # TOUJOURS émettre l'événement incident_etat_changed pour les mises à jour en temps réel
        # Récupérer les infos du statut (couleur)
        statut_info = db.execute("SELECT couleur FROM statuts WHERE nom=%s", (new,)).fetchone()
        statut_couleur = statut_info["couleur"] if statut_info else "#6c757d"
        statut_text_color = get_contrast_color(statut_couleur)

        # Émettre broadcast pour que les autres clients se rafraîchissent
        # Depuis une route Flask, socketio.emit() broadcast automatiquement à tous
        event_data = {
            "action": "etat",
            "id": id,
            "new_etat": new,
            "numero": inc["numero"],
            "couleur": statut_couleur,
            "text_color": statut_text_color
        }
        app.logger.info(f"📡 Émission Socket.IO: incident_etat_changed pour incident {id}, nouveau statut: {new}")
        app.logger.info(f"📡 Données à émettre: {event_data}")
        try:
            # Depuis une route Flask, socketio.emit() broadcast automatiquement
            socketio.emit("incident_etat_changed", event_data)
            app.logger.info(f"✅ Événement Socket.IO émis avec succès")
        except Exception as e:
            app.logger.error(f"❌ Erreur lors de l'émission Socket.IO: {e}")
            import traceback
            app.logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        if is_ajax:
            return jsonify({"status": "ok", "new_etat": new, "couleur": statut_couleur, "text_color": statut_text_color})
        else:
            # Requête normale (formulaire), émettre aussi le broadcast classique pour compatibilité
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
    db.execute("UPDATE incidents SET valide=%s WHERE id=%s", (val, id))
    db.commit()
    socketio.emit("incident_update", {"action": "valide"})
    return redirect(url_for("home"))


# ---------- SUPPRESSION INCIDENT ----------
@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM incidents WHERE id=%s", (id,))
    db.commit()
    socketio.emit("incident_update", {"action": "delete"})
    return redirect(url_for("home"))




# ---------- HISTORIQUE ----------
@app.route("/historique/<int:id>")
def historique(id):
    if "user" not in session:
        return redirect(url_for("login"))

    logs = get_db().execute(
        "SELECT * FROM historique WHERE incident_id=%s ORDER BY date_modification DESC", (id,)
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
    query = "SELECT * FROM incidents WHERE date_affectation=%s AND site=%s AND sujet=%s AND archived=0"
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

# ========== MODULE STATISTIQUES DASHBOARD (POWERBI STYLE) ==========

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
        placeholders = ",".join("?" * len(tech_ids))
        where_clauses.append(f"collaborateur IN (SELECT prenom FROM techniciens WHERE id IN ({placeholders}))")
        params.extend(tech_ids)
    if site_ids:
        placeholders = ",".join("?" * len(site_ids))
        where_clauses.append(f"site IN (SELECT nom FROM sites WHERE id IN ({placeholders}))")
        params.extend(site_ids)
    if status_ids:
        placeholders = ",".join("?" * len(status_ids))
        where_clauses.append(f"etat IN (SELECT nom FROM statuts WHERE id IN ({placeholders}))")
        params.extend(status_ids)
    if priority_ids:
        placeholders = ",".join("?" * len(priority_ids))
        where_clauses.append(f"urgence IN (SELECT nom FROM priorites WHERE id IN ({placeholders}))")
        params.extend(priority_ids)
    
    where_sql = " AND ".join(where_clauses)
    
    # Total incidents
    total = db.execute(f"SELECT COUNT(*) as count FROM incidents WHERE {where_sql}", params).fetchone()['count']
    
    # Taux de résolution
    traites = db.execute(
        f"SELECT COUNT(*) as count FROM incidents i JOIN statuts s ON i.etat = s.nom WHERE {where_sql} AND s.category = 'traite'",
        params
    ).fetchone()['count']
    taux_resolution = (traites / total * 100) if total > 0 else 0
    
    # Temps moyen de traitement (en jours)
    temps_moyen = db.execute(
        f"""SELECT AVG(EXTRACT(EPOCH FROM (NOW() - date_affectation)) / 86400) as avg_days 
            FROM incidents WHERE {where_sql} AND etat != 'Traité'""",
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
        'temps_moyen_jours': round(temps_moyen, 2),
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
        placeholders = ",".join("?" * len(tech_ids))
        where_clauses.append(f"collaborateur IN (SELECT prenom FROM techniciens WHERE id IN ({placeholders}))")
        params.extend(tech_ids)
    if site_ids:
        placeholders = ",".join("?" * len(site_ids))
        where_clauses.append(f"site IN (SELECT nom FROM sites WHERE id IN ({placeholders}))")
        params.extend(site_ids)
    if status_ids:
        placeholders = ",".join("?" * len(status_ids))
        where_clauses.append(f"etat IN (SELECT nom FROM statuts WHERE id IN ({placeholders}))")
        params.extend(status_ids)
    if priority_ids:
        placeholders = ",".join("?" * len(priority_ids))
        where_clauses.append(f"urgence IN (SELECT nom FROM priorites WHERE id IN ({placeholders}))")
        params.extend(priority_ids)
    
    where_sql = " AND ".join(where_clauses)
    
    # Par technicien et statut
    par_tech = db.execute(
        f"""SELECT i.collaborateur, s.nom as statut, COUNT(*) as count
            FROM incidents i
            JOIN statuts s ON i.etat = s.nom
            WHERE {where_sql}
            GROUP BY i.collaborateur, s.nom
            ORDER BY i.collaborateur, s.nom""",
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
        f"""SELECT DATE(date_affectation) as date, 
                   COUNT(*) as total,
                   SUM(CASE WHEN s.category = 'traite' THEN 1 ELSE 0 END) as traites
            FROM incidents i
            LEFT JOIN statuts s ON i.etat = s.nom
            WHERE {where_sql}
            GROUP BY DATE(date_affectation)
            ORDER BY date""",
        params
    ).fetchall()
    
    # Heatmap (charge par technicien et jour)
    heatmap = db.execute(
        f"""SELECT collaborateur, DATE(date_affectation) as date, COUNT(*) as count
            FROM incidents
            WHERE {where_sql}
            GROUP BY collaborateur, DATE(date_affectation)
            ORDER BY date, collaborateur""",
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
        placeholders = ",".join("?" * len(tech_ids))
        where_clauses.append(f"collaborateur IN (SELECT prenom FROM techniciens WHERE id IN ({placeholders}))")
        params.extend(tech_ids)
    if site_ids:
        placeholders = ",".join("?" * len(site_ids))
        where_clauses.append(f"site IN (SELECT nom FROM sites WHERE id IN ({placeholders}))")
        params.extend(site_ids)
    if status_ids:
        placeholders = ",".join("?" * len(status_ids))
        where_clauses.append(f"etat IN (SELECT nom FROM statuts WHERE id IN ({placeholders}))")
        params.extend(status_ids)
    if priority_ids:
        placeholders = ",".join("?" * len(priority_ids))
        where_clauses.append(f"urgence IN (SELECT nom FROM priorites WHERE id IN ({placeholders}))")
        params.extend(priority_ids)
    
    where_sql = " AND ".join(where_clauses)
    
    # Par technicien
    table_tech = db.execute(
        f"""SELECT collaborateur,
                   COUNT(*) as total,
                   SUM(CASE WHEN s.category = 'traite' THEN 1 ELSE 0 END) as traites,
                   SUM(CASE WHEN s.category = 'en_cours' THEN 1 ELSE 0 END) as en_cours,
                   SUM(CASE WHEN s.category = 'suspendu' THEN 1 ELSE 0 END) as suspendus
            FROM incidents i
            LEFT JOIN statuts s ON i.etat = s.nom
            WHERE {where_sql}
            GROUP BY collaborateur
            ORDER BY total DESC""",
        params
    ).fetchall()
    
    # Par site
    table_site = db.execute(
        f"""SELECT site,
                   COUNT(*) as total,
                   SUM(CASE WHEN s.category = 'traite' THEN 1 ELSE 0 END) as traites,
                   SUM(CASE WHEN s.category = 'en_cours' THEN 1 ELSE 0 END) as en_cours
            FROM incidents i
            LEFT JOIN statuts s ON i.etat = s.nom
            WHERE {where_sql}
            GROUP BY site
            ORDER BY total DESC""",
        params
    ).fetchall()
    
    # Par sujet
    table_sujet = db.execute(
        f"""SELECT sujet,
                   COUNT(*) as total,
                   SUM(CASE WHEN s.category = 'traite' THEN 1 ELSE 0 END) as traites
            FROM incidents i
            LEFT JOIN statuts s ON i.etat = s.nom
            WHERE {where_sql}
            GROUP BY sujet
            ORDER BY total DESC""",
        params
    ).fetchall()
    
    return {
        'par_technicien': [dict(row) for row in table_tech],
        'par_site': [dict(row) for row in table_site],
        'par_sujet': [dict(row) for row in table_sujet]
    }


@app.route("/dashboard/stats")
def dashboard_stats():
    """Route principale du dashboard de statistiques"""
    if "user" not in session:
        return redirect(url_for("login"))
    
    db = None
    try:
        db = get_db()
        
        # Récupérer les données de référence
        ref_data = get_reference_data()
        techniciens_rows = db.execute("SELECT id, prenom FROM techniciens WHERE actif=1 ORDER BY prenom").fetchall()
        # Convertir DualAccessRow en dictionnaires pour éviter les erreurs de sérialisation
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
            sujets=sujets
        )
    except Exception as e:
        app.logger.error(f"Erreur dashboard_stats: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        flash(f"Erreur lors du chargement des statistiques: {str(e)}", "danger")
        return redirect(url_for("home"))


@app.route("/api/stats/data")
def api_stats_data():
    """API pour récupérer les données statistiques filtrées avec cache"""
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Récupérer les paramètres de filtres
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    tech_ids = request.args.getlist("tech_ids[]", type=int) or None
    site_ids = request.args.getlist("site_ids[]", type=int) or None
    status_ids = request.args.getlist("status_ids[]", type=int) or None
    priority_ids = request.args.getlist("priority_ids[]", type=int) or None
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    
    # Créer une clé de cache basée sur les filtres
    import hashlib
    import json
    cache_key_data = {
        "start_date": start_date,
        "end_date": end_date,
        "tech_ids": sorted(tech_ids) if tech_ids else None,
        "site_ids": sorted(site_ids) if site_ids else None,
        "status_ids": sorted(status_ids) if status_ids else None,
        "priority_ids": sorted(priority_ids) if priority_ids else None,
        "page": page
    }
    cache_key = f"stats_data_{hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()}"
    
    # Vérifier le cache (TTL de 2 minutes pour les stats)
    cached = app_cache.get(cache_key)
    if cached:
        app.logger.debug(f"Cache hit pour stats: {cache_key}")
        return jsonify(cached)
    
    db = get_db()
    
    try:
        # Calculer les KPIs
        kpis = calculate_stats_kpis(db, start_date, end_date, tech_ids, site_ids, status_ids, priority_ids)
        
        # Calculer les variations (comparaison avec période précédente)
        if start_date and end_date:
            from datetime import datetime, timedelta
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            period_days = (end_dt - start_dt).days
            
            prev_start = (start_dt - timedelta(days=period_days + 1)).strftime("%Y-%m-%d")
            prev_end = (start_dt - timedelta(days=1)).strftime("%Y-%m-%d")
            
            prev_kpis = calculate_stats_kpis(db, prev_start, prev_end, tech_ids, site_ids, status_ids, priority_ids)
            
            variations = {}
            for key in ['total_incidents', 'taux_resolution', 'en_cours', 'urgents']:
                if key in prev_kpis and prev_kpis[key] > 0:
                    variations[key] = round(((kpis[key] - prev_kpis[key]) / prev_kpis[key]) * 100, 2)
                else:
                    variations[key] = 0
        else:
            variations = {'total_incidents': 0, 'taux_resolution': 0, 'en_cours': 0, 'urgents': 0}
        
        kpis['variations'] = variations
        
        # Calculer les données pour graphiques
        charts = calculate_stats_charts(db, start_date, end_date, tech_ids, site_ids, status_ids, priority_ids)
        
        # Calculer les données pour tableaux avec pagination
        tables_data = calculate_stats_tables(db, start_date, end_date, tech_ids, site_ids, status_ids, priority_ids)
        
        # Pagination pour les tableaux
        total_items = {
            'technicien': len(tables_data['par_technicien']),
            'site': len(tables_data['par_site']),
            'sujet': len(tables_data['par_sujet'])
        }
        
        # Appliquer pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        tables = {
            'par_technicien': tables_data['par_technicien'][start_idx:end_idx],
            'par_site': tables_data['par_site'][start_idx:end_idx],
            'par_sujet': tables_data['par_sujet'][start_idx:end_idx],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': max(total_items.values()),
                'total_pages': (max(total_items.values()) + per_page - 1) // per_page
            }
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
                "priority_ids": priority_ids or []
            }
        }
        
        # Mettre en cache (TTL de 2 minutes)
        app_cache.set(cache_key, result, ttl_seconds=120)
        
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Erreur api_stats_data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats/kpis")
def api_stats_kpis():
    """API optimisée pour récupérer uniquement les KPIs avec cache"""
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    # Cache pour KPIs (TTL plus court : 1 minute car plus fréquemment mis à jour)
    import hashlib
    import json
    cache_key_data = {"start_date": start_date, "end_date": end_date}
    cache_key = f"stats_kpis_{hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()}"
    
    cached = app_cache.get(cache_key)
    if cached:
        app.logger.debug(f"Cache hit pour KPIs: {cache_key}")
        return jsonify({"kpis": cached})
    
    db = get_db()
    try:
        kpis = calculate_stats_kpis(db, start_date, end_date)
        # Mettre en cache (TTL de 1 minute)
        app_cache.set(cache_key, kpis, ttl_seconds=60)
        return jsonify({"kpis": kpis})
    except Exception as e:
        app.logger.error(f"Erreur api_stats_kpis: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/dashboard/stats/export/excel")
def export_stats_excel():
    """Export Excel des statistiques"""
    if "user" not in session:
        return redirect(url_for("login"))
    
    # Récupérer les filtres depuis les paramètres
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    tech_ids = request.args.getlist("tech_ids[]", type=int) or None
    site_ids = request.args.getlist("site_ids[]", type=int) or None
    status_ids = request.args.getlist("status_ids[]", type=int) or None
    priority_ids = request.args.getlist("priority_ids[]", type=int) or None
    
    db = get_db()
    try:
        # Récupérer les données
        kpis = calculate_stats_kpis(db, start_date, end_date, tech_ids, site_ids, status_ids, priority_ids)
        charts = calculate_stats_charts(db, start_date, end_date, tech_ids, site_ids, status_ids, priority_ids)
        tables = calculate_stats_tables(db, start_date, end_date, tech_ids, site_ids, status_ids, priority_ids)
        
        # Créer le fichier Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Feuille 1 : Résumé KPIs
            kpis_df = pd.DataFrame([kpis])
            kpis_df.to_excel(writer, sheet_name='Résumé', index=False)
            
            # Feuille 2 : Données brutes
            where_clauses = ["archived=0"]
            params = []
            if start_date:
                where_clauses.append("date_affectation >= %s")
                params.append(start_date)
            if end_date:
                where_clauses.append("date_affectation <= %s")
                params.append(end_date)
            where_sql = " AND ".join(where_clauses)
            incidents_df = pd.read_sql_query(
                f"SELECT * FROM incidents WHERE {where_sql}",
                db.conn.conn if hasattr(db, 'conn') else db.conn,
                params=params
            )
            incidents_df.to_excel(writer, sheet_name='Données brutes', index=False)
            
            # Feuille 3 : Statistiques détaillées
            stats_data = []
            for row in tables['par_technicien']:
                stats_data.append({
                    'Type': 'Technicien',
                    'Nom': row['collaborateur'],
                    'Total': row['total'],
                    'Traités': row['traites'],
                    'En cours': row['en_cours'],
                    'Suspendus': row.get('suspendus', 0)
                })
            for row in tables['par_site']:
                stats_data.append({
                    'Type': 'Site',
                    'Nom': row['site'],
                    'Total': row['total'],
                    'Traités': row['traites'],
                    'En cours': row['en_cours'],
                    'Suspendus': 0
                })
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Statistiques détaillées', index=False)
        
        output.seek(0)
        filename = f"statistiques_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                        as_attachment=True, download_name=filename)
    except Exception as e:
        app.logger.error(f"Erreur export_stats_excel: {e}")
        flash(f"Erreur lors de l'export Excel: {str(e)}", "danger")
        return redirect(url_for("dashboard_stats"))


@app.route("/dashboard/stats/export/pdf")
def export_stats_pdf():
    """Export PDF des statistiques"""
    if "user" not in session:
        return redirect(url_for("login"))
    
    # Récupérer les filtres
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    tech_ids = request.args.getlist("tech_ids[]", type=int) or None
    site_ids = request.args.getlist("site_ids[]", type=int) or None
    status_ids = request.args.getlist("status_ids[]", type=int) or None
    priority_ids = request.args.getlist("priority_ids[]", type=int) or None
    
    db = get_db()
    try:
        kpis = calculate_stats_kpis(db, start_date, end_date, tech_ids, site_ids, status_ids, priority_ids)
        charts = calculate_stats_charts(db, start_date, end_date, tech_ids, site_ids, status_ids, priority_ids)
        tables = calculate_stats_tables(db, start_date, end_date, tech_ids, site_ids, status_ids, priority_ids)
        
        # Générer le HTML pour le PDF
        html = render_template("stats_pdf_export.html",
                             kpis=kpis,
                             charts=charts,
                             tables=tables,
                             start_date=start_date,
                             end_date=end_date,
                             generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"))
        
        pdf_data = pdfkit.from_string(html, False, configuration=pdf_config)
        filename = f"statistiques_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(BytesIO(pdf_data), mimetype='application/pdf',
                        as_attachment=True, download_name=filename)
    except Exception as e:
        app.logger.error(f"Erreur export_stats_pdf: {e}")
        flash(f"Erreur lors de l'export PDF: {str(e)}", "danger")
        return redirect(url_for("dashboard_stats"))


@app.route("/dashboard/stats/export/csv")
def export_stats_csv():
    """Export CSV des données brutes"""
    if "user" not in session:
        return redirect(url_for("login"))
    
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    tech_ids = request.args.getlist("tech_ids[]", type=int) or None
    site_ids = request.args.getlist("site_ids[]", type=int) or None
    status_ids = request.args.getlist("status_ids[]", type=int) or None
    priority_ids = request.args.getlist("priority_ids[]", type=int) or None
    
    db = get_db()
    try:
        where_clauses = ["archived=0"]
        params = []
        if start_date:
            where_clauses.append("date_affectation >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append("date_affectation <= %s")
            params.append(end_date)
        where_sql = " AND ".join(where_clauses)
        
        # Récupérer les données
        rows = db.execute(f"SELECT * FROM incidents WHERE {where_sql}", params).fetchall()
        data = [dict(row) for row in rows]
        df = pd.DataFrame(data)
        
        # Créer le CSV avec BOM UTF-8
        output = BytesIO()
        output.write('\ufeff'.encode('utf-8'))  # BOM pour Excel
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        
        filename = f"statistiques_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return send_file(output, mimetype='text/csv; charset=utf-8',
                        as_attachment=True, download_name=filename)
    except Exception as e:
        app.logger.error(f"Erreur export_stats_csv: {e}")
        flash(f"Erreur lors de l'export CSV: {str(e)}", "danger")
        return redirect(url_for("dashboard_stats"))


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