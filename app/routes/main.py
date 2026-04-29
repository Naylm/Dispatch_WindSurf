from flask import Blueprint, render_template, session, redirect, url_for, flash
from app.utils.db_config import get_db
from app.utils.references import get_reference_data
from app.utils.constants import TECHNICIAN_FAQ, ADMIN_FAQ
from app.utils.settings import get_setting

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    db = get_db()

    # User display name logic
    user_display_name = session["user"].capitalize()
    user_full_name = session["user"].capitalize()
    current_tech_id = None
    photo_profil = None

    if session.get("user_type") == "technicien":
        tech = db.execute(
            "SELECT id, prenom, nom, photo_profil FROM techniciens WHERE username=%s",
            (session["user"],)
        ).fetchone()
        if tech:
            current_tech_id = tech['id']
            user_display_name = tech['prenom']
            nom = tech.get('nom') or ""
            user_full_name = f"{tech['prenom']} {nom}".strip()
            photo_profil = tech.get('photo_profil')
    else:
        user_row = db.execute(
            "SELECT prenom, nom, photo_profil FROM users WHERE username=%s",
            (session["user"],)
        ).fetchone()
        if user_row:
            prenom = user_row.get("prenom") or ""
            nom = user_row.get("nom") or ""
            if prenom:
                user_display_name = prenom
            if prenom or nom:
                user_full_name = f"{prenom} {nom}".strip()
            photo_profil = user_row.get('photo_profil')

    ref_data = get_reference_data()
    priorites = ref_data['priorites']
    sites = ref_data['sites']
    statuts = ref_data['statuts']
    statuts_by_category = ref_data['statuts_by_category']

    if session["role"] in ("admin", "superadmin"):
        incidents = db.execute(
            "SELECT * FROM incidents WHERE archived=0 AND is_deleted=FALSE ORDER BY id ASC"
        ).fetchall()
        techniciens = db.execute("SELECT * FROM techniciens WHERE actif=1 ORDER BY ordre ASC, id ASC").fetchall()
    else:
        if current_tech_id:
            incidents = db.execute(
                "SELECT * FROM incidents WHERE technicien_id=%s AND archived=0 AND is_deleted=FALSE ORDER BY id ASC",
                (current_tech_id,),
            ).fetchall()
        else:
            incidents = db.execute(
                "SELECT * FROM incidents WHERE collaborateur=%s AND archived=0 AND is_deleted=FALSE ORDER BY id ASC",
                (session["user"],),
            ).fetchall()
        techniciens = []

    stats_results = db.execute("""
        SELECT s.category, COUNT(*) as count
        FROM incidents i
        JOIN statuts s ON i.etat = s.nom
        WHERE i.archived=0 AND i.is_deleted=FALSE
        GROUP BY s.category
    """).fetchall()

    stats_by_category = {
        'en_cours': 0, 'suspendu': 0, 'transfere': 0, 'traite': 0
    }
    for row in stats_results:
        if row['category'] in stats_by_category:
            stats_by_category[row['category']] = row['count']
    
    # Récupérer les diffusions actives
    active_broadcasts = db.execute("SELECT * FROM broadcasts WHERE is_active=TRUE ORDER BY is_permanent DESC, created_at DESC").fetchall()

    return render_template(
        "home.html",
        incidents=incidents,
        user=user_display_name,
        user_full_name=user_full_name,
        photo_profil=photo_profil,
        username=session["user"],
        role=session["role"],
        user_type=session.get("user_type"),
        techniciens=techniciens,
        priorites=priorites,
        sites=sites,
        statuts=statuts,
        stats_by_category=stats_by_category,
        statuts_by_category=statuts_by_category,
        active_broadcasts=active_broadcasts,
        konami_hub_enabled=get_setting('konami_hub_enabled', True),
    )

@main_bp.route("/api/home-content")
def home_content_api():
    if "user" not in session:
        return "", 403

    db = get_db()
    current_tech_id = None
    if session.get("user_type") == "technicien":
        tech = db.execute(
            "SELECT id FROM techniciens WHERE username=%s",
            (session["user"],)
        ).fetchone()
        if tech:
            current_tech_id = tech['id']

    ref_data = get_reference_data()
    priorites = ref_data['priorites']
    sites = ref_data['sites']
    statuts = ref_data['statuts']
    statuts_by_category = ref_data['statuts_by_category']

    if session["role"] in ("admin", "superadmin"):
        incidents = db.execute(
            "SELECT * FROM incidents WHERE archived=0 AND is_deleted=FALSE ORDER BY id ASC"
        ).fetchall()
        techniciens = db.execute("SELECT * FROM techniciens WHERE actif=1 ORDER BY ordre ASC, id ASC").fetchall()
    else:
        if current_tech_id:
            incidents = db.execute(
                "SELECT * FROM incidents WHERE technicien_id=%s AND archived=0 AND is_deleted=FALSE ORDER BY id ASC",
                (current_tech_id,),
            ).fetchall()
        else:
            incidents = db.execute(
                "SELECT * FROM incidents WHERE collaborateur=%s AND archived=0 AND is_deleted=FALSE ORDER BY id ASC",
                (session["user"],),
            ).fetchall()
        techniciens = []

    stats_results = db.execute("""
        SELECT s.category, COUNT(*) as count
        FROM incidents i
        JOIN statuts s ON i.etat = s.nom
        WHERE i.archived=0 AND i.is_deleted=FALSE
        GROUP BY s.category
    """).fetchall()

    stats_by_category = {
        'en_cours': 0, 'suspendu': 0, 'transfere': 0, 'traite': 0
    }
    for row in stats_results:
        if row['category'] in stats_by_category:
            stats_by_category[row['category']] = row['count']

    # Récupérer les diffusions actives
    active_broadcasts = db.execute("SELECT * FROM broadcasts WHERE is_active=TRUE ORDER BY is_permanent DESC, created_at DESC").fetchall()

    return render_template(
        "home_content.html",
        incidents=incidents,
        user=session["user"],
        username=session["user"],
        role=session["role"],
        techniciens=techniciens,
        priorites=priorites,
        sites=sites,
        statuts=statuts,
        stats_by_category=stats_by_category,
        statuts_by_category=statuts_by_category,
        active_broadcasts=active_broadcasts,
    )

@main_bp.route("/faq")
def faq():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    is_admin = session.get("role") in ("admin", "superadmin")
    is_technician = (
        session.get("user_type") == "technicien"
        or session.get("role") == "technicien"
    )

    if not (is_admin or is_technician):
        flash("Accès réservé aux techniciens et administrateurs.", "danger")
        return redirect(url_for("main.home"))

    return render_template(
        "faq.html",
        role=session.get("role"),
        is_admin=is_admin,
        technician_faq=TECHNICIAN_FAQ,
        admin_faq=ADMIN_FAQ,
    )

@main_bp.route("/annuaire")
def annuaire():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    db = get_db()
    techniciens_list = db.execute("""
        SELECT id, nom, prenom, dect_number, email, actif, role, ordre
        FROM techniciens 
        WHERE actif=%s 
        ORDER BY ordre ASC, prenom ASC
    """, (1,)).fetchall()
    
    users_list = db.execute("""
        SELECT id,
               COALESCE(nom, NULL) as nom,
               COALESCE(prenom, username) as prenom,               COALESCE(dect_number, NULL) as dect_number,
               COALESCE(email, NULL) as email,
               1 as actif,
               role,
               0 as ordre
        FROM users
        WHERE role IN ('admin', 'user')
        AND role != 'superadmin'
    """).fetchall()
    
    all_people = list(techniciens_list) + list(users_list)
    all_people.sort(key=lambda x: (x.get('ordre', 0), x.get('prenom', '')))
    
    return render_template("annuaire.html", techniciens=all_people, role=session.get("role"))