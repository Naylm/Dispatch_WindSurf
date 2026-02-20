from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory, current_app
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime, timezone
import pytz
from app.utils.db_config import get_db
from app.utils.notifications import emit_wiki_update_requested_notification
from app import socketio
from flask_wtf.csrf import CSRFError

wiki_bp = Blueprint('wiki', __name__)

# Timezone Paris
TZ_PARIS = pytz.timezone("Europe/Paris")

def to_paris(dt):
    """Convertit une datetime en timezone Europe/Paris"""
    if dt is None:
        return None
    # Si dt est naïf, on le considère UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ_PARIS)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Magic bytes pour validation du type de fichier réel
MAGIC_BYTES = {
    b'\x89PNG': 'png',
    b'\xFF\xD8\xFF': 'jpg',  # JPEG
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'RIFF': 'webp',  # WebP (nécessite vérification supplémentaire)
}

def allowed_file(filename):
    """Vérifie l'extension du fichier"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image_content(file_stream):
    """Valide le contenu du fichier en vérifiant les magic bytes"""
    header = file_stream.read(12)
    file_stream.seek(0)  # Revenir au début du fichier

    # Vérifier les magic bytes
    for magic, filetype in MAGIC_BYTES.items():
        if header.startswith(magic):
            # Vérification supplémentaire pour WebP
            if filetype == 'webp' and header[8:12] == b'WEBP':
                return True
            elif filetype != 'webp':
                return True

    return False

# ========== ROUTE PRINCIPALE ==========
@wiki_bp.route("/wiki")
def wiki():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    db = get_db()
    
    # Récupérer toutes les catégories avec leurs sous-catégories et articles
    categories = db.execute("""
        SELECT * FROM wiki_categories ORDER BY position, name
    """).fetchall()
    
    # Pour chaque catégorie, récupérer ses sous-catégories
    wiki_structure = []
    for cat in categories:
        cat_dict = dict(cat)
        
        # Récupérer les sous-catégories
        subcategories = db.execute("""
            SELECT * FROM wiki_subcategories 
            WHERE category_id = %s 
            ORDER BY position, name
        """, (cat['id'],)).fetchall()
        
        subcat_list = []
        for subcat in subcategories:
            subcat_dict = dict(subcat)
            
            # Récupérer les articles de cette sous-catégorie
            articles = db.execute("""
                SELECT id, title, icon, created_by, created_at, 
                       likes_count, dislikes_count, views_count
                FROM wiki_articles 
                WHERE subcategory_id = %s 
                ORDER BY title
            """, (subcat['id'],)).fetchall()
            
            subcat_dict['articles'] = [dict(art) for art in articles]
            subcat_dict['article_count'] = len(articles)
            subcat_list.append(subcat_dict)
        
        cat_dict['subcategories'] = subcat_list
        cat_dict['total_articles'] = sum(s['article_count'] for s in subcat_list)
        wiki_structure.append(cat_dict)
    
    # Récupérer les articles récents
    recent_articles = db.execute("""
        SELECT a.*, s.name as subcat_name, c.name as cat_name, c.icon as cat_icon
        FROM wiki_articles a
        LEFT JOIN wiki_subcategories s ON a.subcategory_id = s.id
        LEFT JOIN wiki_categories c ON s.category_id = c.id
        ORDER BY a.created_at DESC
        LIMIT 5
    """).fetchall()
    
    db.close()
    
    return render_template(
        "wiki_v2.html",
        categories=wiki_structure,
        recent_articles=[dict(r) for r in recent_articles],
        user=session["user"],
        role=session["role"]
    )

# ========== GESTION DES CATÉGORIES ==========
@wiki_bp.route("/wiki/category/create", methods=["POST"])
def create_wiki_category():
    try:
        if "user" not in session:
            current_app.logger.error("wiki_category_create: user not in session")
            return jsonify({"error": "Non autorisé"}), 403
        
        # Récupérer les données (form ou JSON)
        if request.is_json:
            data = request.json
            name = data.get("name", "").strip()
            icon = data.get("icon", "📁").strip()
            description = data.get("description", "").strip()
            color = data.get("color", "#4f46e5").strip()
        else:
            name = request.form.get("name", "").strip()
            icon = request.form.get("icon", "📁").strip()
            description = request.form.get("description", "").strip()
            color = request.form.get("color", "#4f46e5").strip()
        
        if not name:
            current_app.logger.error("wiki_category_create: missing name parameter")
            return jsonify({"error": "Nom requis"}), 400
        
        db = get_db()
        max_pos = db.execute("SELECT MAX(position) as max FROM wiki_categories").fetchone()
        position = (max_pos['max'] or 0) + 1
        
        db.execute("""
            INSERT INTO wiki_categories (name, icon, description, color, position, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, icon, description, color, position, session["user"]))
        db.commit()
        db.close()
        
        # Si c'est une requête AJAX, retourner JSON
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({"success": True, "message": "Catégorie créée avec succès!"})
        
        flash("Catégorie créée avec succès!", "success")
        return redirect(url_for("wiki.wiki"))
    except Exception as e:
        current_app.logger.exception(f"wiki_category_create: exception: {e}")
        return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500

@wiki_bp.route("/wiki/category/<int:id>/edit", methods=["POST"])
def edit_wiki_category(id):
    if "user" not in session:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"error": "Non autorisé"}), 403
        flash("Non autorisé", "error")
        return redirect(url_for("wiki.wiki"))
    
    name = request.form.get("name", "").strip()
    icon = request.form.get("icon", "📁").strip()
    description = request.form.get("description", "").strip()
    color = request.form.get("color", "#4f46e5").strip()
    
    db = get_db()
    try:
        db.execute("""
            UPDATE wiki_categories 
            SET name=%s, icon=%s, description=%s, color=%s
            WHERE id=%s
        """, (name, icon, description, color, id))
        db.commit()
        
        # Si c'est une requête AJAX, retourner JSON
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({"success": True, "message": "Catégorie modifiée avec succès!"})
        
        # Sinon, rediriger vers la page wiki avec un message flash
        flash("Catégorie modifiée avec succès!", "success")
        return redirect(url_for("wiki.wiki"))
    except Exception as e:
        db.rollback()
        current_app.logger.exception(f"edit_wiki_category: exception: {e}")
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500
        flash(f"Erreur lors de la modification: {str(e)}", "error")
        return redirect(url_for("wiki.wiki"))
    finally:
        db.close()

@wiki_bp.route("/wiki/category/<int:id>/delete", methods=["POST"])
def delete_wiki_category(id):
    try:
        current_app.logger.info(f"delete_wiki_category: POST on category_id={id}, form={dict(request.form)}, headers={dict(request.headers)}")
        
        if "user" not in session:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "Non autorisé"}), 403
            return redirect(url_for("auth.login"))
        
        db = get_db()
        
        try:
            # Vérifier que la catégorie existe
            category = db.execute("SELECT id FROM wiki_categories WHERE id=%s", (id,)).fetchone()
            if not category:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"success": False, "error": "Catégorie non trouvée"}), 404
                flash("Catégorie non trouvée", "error")
                return redirect(url_for("wiki.wiki"))
            
            # Supprimer la catégorie
            db.execute("DELETE FROM wiki_categories WHERE id=%s", (id,))
            db.commit()
            db.close()
            
            current_app.logger.info(f"delete_wiki_category: Category {id} deleted successfully")
            
            # Réponse selon le type de requête
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "success": True,
                    "status": "ok"
                }), 200
            
            flash("Catégorie supprimée", "success")
            return redirect(url_for("wiki.wiki"))
            
        except Exception as db_error:
            db.rollback()
            db.close()
            current_app.logger.exception(f"delete_wiki_category: Database error for category {id}")
            raise
            
    except CSRFError as e:
        current_app.logger.warning(f"delete_wiki_category CSRF error: {e.description}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": "CSRF token invalide"}), 400
        flash("Erreur CSRF", "error")
        return redirect(url_for("wiki.wiki"))
    except Exception as e:
        current_app.logger.exception(f"delete_wiki_category: exception for category {id}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": "Erreur interne"}), 500
        flash("Erreur lors de la suppression", "error")
        return redirect(url_for("wiki.wiki"))

# ========== GESTION DES SOUS-CATÉGORIES ==========
@wiki_bp.route("/wiki/subcategory/create", methods=["POST"])
def create_wiki_subcategory():
    try:
        if "user" not in session:
            current_app.logger.error("wiki_subcategory_create: user not in session")
            return jsonify({"error": "Non autorisé"}), 403
        
        name = request.form.get("name", "").strip()
        category_id = request.form.get("category_id")
        icon = request.form.get("icon", "📄").strip()
        description = request.form.get("description", "").strip()
        
        if not name or not category_id:
            current_app.logger.error("wiki_subcategory_create: missing name or category_id")
            return jsonify({"error": "Nom et catégorie requis"}), 400
        
        db = get_db()
        max_pos = db.execute(
            "SELECT MAX(position) as max FROM wiki_subcategories WHERE category_id=%s", 
            (category_id,)
        ).fetchone()
        position = (max_pos['max'] or 0) + 1
        
        db.execute("""
            INSERT INTO wiki_subcategories (name, category_id, icon, description, position, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, category_id, icon, description, position, session["user"]))
        db.commit()
        db.close()
        
        # Si c'est une requête AJAX, retourner JSON
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({"success": True, "message": "Sous-catégorie créée avec succès!"})
        
        flash("Sous-catégorie créée avec succès!", "success")
        return redirect(url_for("wiki.wiki"))
    except Exception as e:
        current_app.logger.exception(f"wiki_subcategory_create: exception: {e}")
        return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500

@wiki_bp.route("/wiki/subcategory/<int:id>/edit", methods=["POST"])
def edit_wiki_subcategory(id):
    if "user" not in session:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"error": "Non autorisé"}), 403
        flash("Non autorisé", "error")
        return redirect(url_for("wiki.wiki"))
    
    name = request.form.get("name", "").strip()
    icon = request.form.get("icon", "📄").strip()
    description = request.form.get("description", "").strip()
    
    db = get_db()
    try:
        db.execute("""
            UPDATE wiki_subcategories 
            SET name=%s, icon=%s, description=%s
            WHERE id=%s
        """, (name, icon, description, id))
        db.commit()
        
        # Si c'est une requête AJAX, retourner JSON
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({"success": True, "message": "Sous-catégorie modifiée avec succès!"})
        
        # Sinon, rediriger vers la page wiki avec un message flash
        flash("Sous-catégorie modifiée avec succès!", "success")
        return redirect(url_for("wiki.wiki"))
    except Exception as e:
        db.rollback()
        current_app.logger.exception(f"edit_wiki_subcategory: exception: {e}")
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500
        flash(f"Erreur lors de la modification: {str(e)}", "error")
        return redirect(url_for("wiki.wiki"))
    finally:
        db.close()

@wiki_bp.route("/wiki/subcategory/<int:id>/delete", methods=["POST"])
def delete_wiki_subcategory(id):
    try:
        current_app.logger.info(f"delete_wiki_subcategory: POST on subcategory_id={id}, form={dict(request.form)}, headers={dict(request.headers)}")
        
        if "user" not in session:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "Non autorisé"}), 403
            return redirect(url_for("auth.login"))
        
        db = get_db()
        
        try:
            # Vérifier que la sous-catégorie existe
            subcategory = db.execute("SELECT id FROM wiki_subcategories WHERE id=%s", (id,)).fetchone()
            if not subcategory:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"success": False, "error": "Sous-catégorie non trouvée"}), 404
                flash("Sous-catégorie non trouvée", "error")
                return redirect(url_for("wiki.wiki"))
            
            # Supprimer la sous-catégorie (les articles seront orphelins ou supprimés selon cascade)
            db.execute("DELETE FROM wiki_subcategories WHERE id=%s", (id,))
            db.commit()
            db.close()
            
            current_app.logger.info(f"delete_wiki_subcategory: Subcategory {id} deleted successfully")
            
            # Réponse selon le type de requête
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "success": True,
                    "status": "ok"
                }), 200
            
            flash("Sous-catégorie supprimée", "success")
            return redirect(url_for("wiki.wiki"))
            
        except Exception as db_error:
            db.rollback()
            db.close()
            current_app.logger.exception(f"delete_wiki_subcategory: Database error for subcategory {id}")
            raise
            
    except CSRFError as e:
        current_app.logger.warning(f"delete_wiki_subcategory CSRF error: {e.description}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": "CSRF token invalide"}), 400
        flash("Erreur CSRF", "error")
        return redirect(url_for("wiki.wiki"))
    except Exception as e:
        current_app.logger.exception(f"delete_wiki_subcategory: exception for subcategory {id}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": "Erreur interne"}), 500
        flash("Erreur lors de la suppression", "error")
        return redirect(url_for("wiki.wiki"))

# ========== GESTION DES ARTICLES ==========
@wiki_bp.route("/wiki/article/create", methods=["GET", "POST"])
def create_wiki_article():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    if request.method == "GET":
        db = get_db()
        categories = db.execute("SELECT * FROM wiki_categories ORDER BY name").fetchall()
        subcategories = db.execute("SELECT * FROM wiki_subcategories ORDER BY name").fetchall()
        db.close()
        return render_template("wiki_article_edit_v2.html", 
                             categories=[dict(c) for c in categories],
                             subcategories=[dict(s) for s in subcategories],
                             article=None,
                             user=session["user"])
    
    # POST - Création
    current_app.logger.info("wiki_article_create: START")
    
    title = (request.form.get("title") or "").strip()
    subcategory_id_str = request.form.get("subcategory_id")
    content = (request.form.get("content") or "").strip()
    icon = request.form.get("icon", "📝").strip()
    tags = request.form.get("tags", "").strip()
    
    # Convertir subcategory_id en int
    try:
        subcategory_id = int(subcategory_id_str) if subcategory_id_str else None
    except (ValueError, TypeError):
        subcategory_id = None
    
    # Validation
    if not title or not subcategory_id:
        flash("Titre et sous-catégorie sont obligatoires.", "error")
        return redirect(request.referrer or url_for("wiki.wiki"))
    
    if not content or len(content.strip()) < 10:
        flash("Le contenu est obligatoire et doit contenir au moins 10 caractères.", "error")
        return redirect(request.referrer or url_for("wiki.wiki"))
    
    # Validation des tags (format: séparés par virgules)
    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        if len(tag_list) > 10:
            flash("Maximum 10 tags autorisés.", "error")
            return redirect(request.referrer or url_for("wiki.wiki"))
    
    # Récupérer le statut
    status = request.form.get("status", "published")
    if status not in ['draft', 'published', 'archived', 'obsolete']:
        status = 'published'
    
    owner = request.form.get("owner", session["user"])
    summary = request.form.get("summary", "").strip()
    
    db = get_db()
    try:
        result = db.execute(
            """
            INSERT INTO wiki_articles 
            (title, content, subcategory_id, icon, created_by, tags, status, owner, summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (title, content, subcategory_id, icon, session["user"], tags, status, owner, summary)
        )
        
        row = result.fetchone()
        article_id = row["id"]
        db.commit()
        
    except Exception as e:
        db.rollback()
        current_app.logger.exception("wiki_article_create: ERROR")
        flash(f"Erreur lors de la création de l'article: {str(e)}", "error")
        return redirect(request.referrer or url_for("wiki.wiki"))
    finally:
        db.close()
    
    flash("Article créé avec succès!", "success")
    return redirect(url_for("wiki.view_wiki_article", id=article_id))

@wiki_bp.route("/wiki/article/<int:id>")
def view_wiki_article(id):
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    db = get_db()
    try:
        # Récupérer l'article
        article = db.execute("SELECT * FROM wiki_articles WHERE id = %s", (id,)).fetchone()
        
        if not article:
            flash("Article non trouvé", "error")
            return redirect(url_for("wiki.wiki"))
        
        article_dict = dict(article)
        
        # Convertir les dates
        if article_dict.get('created_at'):
            article_dict['created_at'] = to_paris(article_dict['created_at'])
        if article_dict.get('updated_at'):
            article_dict['updated_at'] = to_paris(article_dict['updated_at'])
        
        # Récupérer les infos de catégorie
        subcat_name = None
        cat_name = None
        cat_icon = None
        cat_id = None
        
        if article_dict.get('subcategory_id'):
            subcat = db.execute("""
                SELECT s.*, c.name as cat_name, c.icon as cat_icon, c.id as cat_id
                FROM wiki_subcategories s
                LEFT JOIN wiki_categories c ON s.category_id = c.id
                WHERE s.id = %s
            """, (article_dict['subcategory_id'],)).fetchone()
            
            if subcat:
                subcat_dict = dict(subcat)
                subcat_name = subcat_dict.get('name')
                cat_name = subcat_dict.get('cat_name')
                cat_icon = subcat_dict.get('cat_icon')
                cat_id = subcat_dict.get('cat_id')
        
        # Incrémenter le compteur de vues
        db.execute("UPDATE wiki_articles SET views_count = views_count + 1 WHERE id=%s", (id,))
        db.commit()
        
        # Récupérer le vote de l'utilisateur
        user_vote_dict = None
        user_vote = db.execute("""
            SELECT vote_type FROM wiki_votes 
            WHERE article_id=%s AND user_name=%s
        """, (id, session["user"])).fetchone()
        if user_vote:
            user_vote_dict = dict(user_vote)
        
        # Récupérer l'historique
        history_list = []
        history = db.execute("""
            SELECT * FROM wiki_history 
            WHERE article_id=%s 
            ORDER BY modified_at DESC 
            LIMIT 10
        """, (id,)).fetchall()
        
        for h in history:
            hist_dict = dict(h)
            if hist_dict.get('modified_at'):
                hist_dict['modified_at'] = to_paris(hist_dict['modified_at'])
            history_list.append(hist_dict)

        # Vérifier s'il y a des feedbacks
        update_requested = False
        feedback_check = db.execute("""
            SELECT COUNT(*) as count FROM wiki_feedback
            WHERE article_id=%s AND feedback_type IN ('outdated', 'needs_update')
        """, (id,)).fetchone()
        if feedback_check and feedback_check['count'] > 0:
            update_requested = True

        article_dict['subcat_name'] = subcat_name
        article_dict['cat_name'] = cat_name
        article_dict['cat_icon'] = cat_icon
        article_dict['cat_id'] = cat_id

        return render_template("wiki_article_view_v2.html",
                             article=article_dict,
                             user_vote=user_vote_dict,
                             history=history_list,
                             update_requested=update_requested,
                             user=session["user"],
                             role=session["role"])
                             
    except Exception as e:
        current_app.logger.exception(f"view_wiki_article: EXCEPTION for article {id}: {e}")
        flash(f"Erreur lors de l'affichage de l'article: {str(e)}", "error")
        return redirect(url_for("wiki.wiki"))
    finally:
        db.close()

@wiki_bp.route("/wiki/article/<int:id>/edit", methods=["GET", "POST"])
def edit_wiki_article(id):
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    db = get_db()
    article = db.execute("SELECT * FROM wiki_articles WHERE id=%s", (id,)).fetchone()
    
    if not article:
        flash("Article non trouvé", "error")
        return redirect(url_for("wiki.wiki"))
    
    if request.method == "GET":
        categories = db.execute("SELECT * FROM wiki_categories ORDER BY name").fetchall()
        subcategories = db.execute("SELECT * FROM wiki_subcategories ORDER BY name").fetchall()
        db.close()
        return render_template("wiki_article_edit_v2.html",
                             article=dict(article),
                             categories=[dict(c) for c in categories],
                             subcategories=[dict(s) for s in subcategories],
                             user=session["user"])
    
    # POST - Mise à jour
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "")
    subcategory_id = request.form.get("subcategory_id")
    icon = request.form.get("icon", "📝").strip()
    tags = request.form.get("tags", "").strip()
    change_description = request.form.get("change_description", "").strip()
    
    if not title:
        flash("Le titre est obligatoire.", "error")
        return redirect(request.referrer or url_for("wiki.wiki"))
    
    if not content or len(content.strip()) < 10:
        flash("Le contenu est obligatoire et doit contenir au moins 10 caractères.", "error")
        return redirect(request.referrer or url_for("wiki.wiki"))
    
    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        if len(tag_list) > 10:
            flash("Maximum 10 tags autorisés.", "error")
            return redirect(request.referrer or url_for("wiki.wiki"))
    
    status = request.form.get("status", article.get('status', 'published'))
    if status not in ['draft', 'published', 'archived', 'obsolete']:
        status = article.get('status', 'published')
    
    owner = request.form.get("owner", article.get('owner', session["user"]))
    summary = (request.form.get("summary") or article.get('summary') or '').strip()
    
    db.execute("""
        INSERT INTO wiki_history (article_id, title, content, modified_by, change_description)
        VALUES (%s, %s, %s, %s, %s)
    """, (id, article['title'], article['content'], session["user"], change_description or "Modification"))
    
    db.execute("""
        UPDATE wiki_articles 
        SET title=%s, content=%s, subcategory_id=%s, icon=%s, tags=%s,
            status=%s, owner=%s, summary=%s,
            updated_at=CURRENT_TIMESTAMP, last_modified_by=%s
        WHERE id=%s
    """, (title, content, subcategory_id, icon, tags, status, owner, summary, session["user"], id))
    
    db.commit()
    db.close()
    
    flash("Article mis à jour avec succès!", "success")
    return redirect(url_for("wiki.view_wiki_article", id=id))

@wiki_bp.route("/wiki/article/<int:id>/delete", methods=["POST"])
def delete_wiki_article(id):
    try:
        current_app.logger.info(f"delete_wiki_article: POST on article_id={id}")
        
        if "user" not in session:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "Non autorisé"}), 403
            return redirect(url_for("auth.login"))
        
        db = get_db()
        
        try:
            article = db.execute("SELECT id FROM wiki_articles WHERE id=%s", (id,)).fetchone()
            if not article:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"success": False, "error": "Article non trouvé"}), 404
                flash("Article non trouvé", "error")
                return redirect(url_for("wiki.wiki"))
            
            db.execute("DELETE FROM wiki_articles WHERE id=%s", (id,))
            db.commit()
            db.close()
            
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "success": True,
                    "status": "ok",
                    "redirect_url": url_for("wiki.wiki")
                }), 200
            
            flash("Article supprimé", "success")
            return redirect(url_for("wiki.wiki"))
            
        except Exception as db_error:
            db.rollback()
            db.close()
            raise
            
    except CSRFError as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": "CSRF token invalide"}), 400
        flash("Erreur CSRF", "error")
        return redirect(url_for("wiki.wiki"))
    except Exception as e:
        current_app.logger.exception(f"delete_wiki_article: exception for article {id}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": "Erreur interne"}), 500
        flash("Erreur lors de la suppression", "error")
        return redirect(url_for("wiki.wiki"))

@wiki_bp.route("/wiki/article/<int:id>/move", methods=["POST"])
def move_wiki_article(id):
    if "user" not in session:
        return jsonify({"error": "Non autorisé"}), 403
    
    new_subcategory_id = request.form.get("new_subcategory_id")
    
    db = get_db()
    db.execute("UPDATE wiki_articles SET subcategory_id=%s WHERE id=%s", 
              (new_subcategory_id, id))
    db.commit()
    db.close()
    
    flash("Article déplacé avec succès!", "success")
    return redirect(url_for("wiki.view_wiki_article", id=id))

@wiki_bp.route("/wiki/article/<int:id>/vote", methods=["POST"])
def vote_wiki_article(id):
    try:
        if "user" not in session:
            return jsonify({"success": False, "error": "Non autorisé"}), 403

        data = request.json if request.is_json else request.form
        vote_type = data.get("vote_type") or data.get("direction")
        
        if vote_type not in ['like', 'dislike', 'up', 'down']:
            return jsonify({"success": False, "error": "Type de vote invalide"}), 400
        
        if vote_type == 'up': vote_type = 'like'
        elif vote_type == 'down': vote_type = 'dislike'
        
        db = get_db()
        try:
            existing_vote = db.execute("""
                SELECT vote_type FROM wiki_votes 
                WHERE article_id=%s AND user_name=%s
            """, (id, session["user"])).fetchone()
            
            if existing_vote:
                old_vote = existing_vote['vote_type']
                db.execute("DELETE FROM wiki_votes WHERE article_id=%s AND user_name=%s", 
                          (id, session["user"]))
                
                if old_vote == 'like':
                    db.execute("UPDATE wiki_articles SET likes_count = likes_count - 1 WHERE id=%s", (id,))
                else:
                    db.execute("UPDATE wiki_articles SET dislikes_count = dislikes_count - 1 WHERE id=%s", (id,))
                
                if old_vote == vote_type:
                    db.commit()
                    article = db.execute("SELECT likes_count, dislikes_count FROM wiki_articles WHERE id=%s", (id,)).fetchone()
                    return jsonify({
                        "success": True,
                        "status": "ok",
                        "likes": article['likes_count'],
                        "dislikes": article['dislikes_count'],
                        "user_vote": None
                    }), 200
            
            db.execute("""
                INSERT INTO wiki_votes (article_id, user_name, vote_type)
                VALUES (%s, %s, %s)
            """, (id, session["user"], vote_type))
            
            if vote_type == 'like':
                db.execute("UPDATE wiki_articles SET likes_count = likes_count + 1 WHERE id=%s", (id,))
            else:
                db.execute("UPDATE wiki_articles SET dislikes_count = dislikes_count + 1 WHERE id=%s", (id,))
            
            db.commit()
            
            article = db.execute("SELECT likes_count, dislikes_count FROM wiki_articles WHERE id=%s", (id,)).fetchone()
            return jsonify({
                "success": True,
                "status": "ok",
                "likes": article['likes_count'],
                "dislikes": article['dislikes_count'],
                "user_vote": vote_type
            }), 200
            
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
            
    except Exception as e:
        current_app.logger.exception(f"vote_wiki_article: exception for article {id}")
        return jsonify({"success": False, "error": "Erreur interne"}), 500

@wiki_bp.route("/wiki/upload", methods=["POST"])
def upload_wiki_image():
    try:
        if "user" not in session:
            return jsonify({"error": "Non autorisé"}), 403
        
        if 'file' not in request.files:
            return jsonify({"error": "Aucun fichier"}), 400
        
        file = request.files['file']
        
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({"error": "Fichier invalide"}), 400

        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({"error": f"Fichier trop volumineux (max 5MB)"}), 400

        if not validate_image_content(file.stream):
            return jsonify({"error": "Le contenu du fichier ne correspond pas à une image valide"}), 400

        UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads', 'wiki')
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'jpg'
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        
        db = get_db()
        db.execute("""
            INSERT INTO wiki_images (filename, original_filename, filepath, uploaded_by, file_size)
            VALUES (%s, %s, %s, %s, %s)
        """, (unique_filename, original_filename, filepath, session["user"], file_size))
        db.commit()
        db.close()
        
        image_url = url_for('static', filename=f'uploads/wiki/{unique_filename}')
        
        return jsonify({
            "success": True,
            "status": "ok",
            "url": image_url,
            "filename": unique_filename
        }), 200
    
    except Exception as e:
        current_app.logger.exception(f"wiki_upload_image: exception: {e}")
        return jsonify({"success": False, "error": f"Erreur serveur: {str(e)}"}), 500

@wiki_bp.route("/wiki/search/suggestions")
def wiki_search_suggestions():
    if "user" not in session:
        return jsonify({"suggestions": []})
    
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify({"suggestions": []})
    
    db = get_db()
    try:
        suggestions = db.execute("""
            SELECT DISTINCT title, id
            FROM wiki_articles
            WHERE title ILIKE %s
            ORDER BY title
            LIMIT 10
        """, (f"%{query}%",)).fetchall()
        result = [{"title": s['title'], "id": s['id']} for s in suggestions]
    except Exception:
        result = []
    finally:
        db.close()
    
    return jsonify({"suggestions": result})

@wiki_bp.route("/wiki/search")
def search_wiki():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    query = request.args.get("q", "").strip()
    
    if not query:
        return redirect(url_for("wiki.wiki"))
    
    query_terms = query.split()
    query_ts = ' & '.join([term.replace("'", "''") for term in query_terms])
    
    db = get_db()
    try:
        results = db.execute("""
            SELECT a.*, 
                   s.name as subcat_name, 
                   c.name as cat_name, 
                   c.icon as cat_icon,
                   ts_rank(
                       to_tsvector('french', 
                           coalesce(a.title, '') || ' ' || 
                           coalesce(a.content, '') || ' ' || 
                           coalesce(a.tags, '')
                       ),
                       to_tsquery('french', %s)
                   ) as rank
            FROM wiki_articles a
            LEFT JOIN wiki_subcategories s ON a.subcategory_id = s.id
            LEFT JOIN wiki_categories c ON s.category_id = c.id
            WHERE to_tsvector('french', 
                coalesce(a.title, '') || ' ' || 
                coalesce(a.content, '') || ' ' || 
                coalesce(a.tags, '')
            ) @@ to_tsquery('french', %s)
            ORDER BY rank DESC, a.updated_at DESC
        """, (query_ts, query_ts)).fetchall()
    except Exception:
        results = db.execute("""
            SELECT a.*, s.name as subcat_name, c.name as cat_name, c.icon as cat_icon, 0 as rank
            FROM wiki_articles a
            LEFT JOIN wiki_subcategories s ON a.subcategory_id = s.id
            LEFT JOIN wiki_categories c ON s.category_id = c.id
            WHERE a.title LIKE %s OR a.content LIKE %s OR a.tags LIKE %s
            ORDER BY a.created_at DESC
        """, (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
    
    try:
        db.execute("""
            INSERT INTO wiki_search_log (query, user_name, results_count)
            VALUES (%s, %s, %s)
        """, (query, session.get("user"), len(results)))
        db.commit()
    except Exception:
        pass
    
    db.close()
    
    return render_template("wiki_search_results_v2.html",
                         query=query,
                         results=[dict(r) for r in results],
                         user=session["user"])

@wiki_bp.route("/wiki/article/<int:id>/mark_updated", methods=["POST"])
def mark_article_updated(id):
    if "user" not in session:
        return jsonify({"success": False, "error": "Non autorisé"}), 403

    db = get_db()
    try:
        article = db.execute("""
            SELECT id, owner, created_by
            FROM wiki_articles
            WHERE id = %s
        """, (id,)).fetchone()
        if not article:
            return jsonify({"success": False, "error": "Article non trouvé"}), 404
        
        article_dict = dict(article)
        owner = (article_dict.get("owner") or "").strip().lower()
        created_by = (article_dict.get("created_by") or "").strip().lower()
        current_user = (session.get("user") or "").strip().lower()

        if session.get("role") == "admin" and current_user not in {owner, created_by}:
            return jsonify({"success": False, "error": "Validation réservée aux utilisateurs"}), 403

        db.execute("""
            DELETE FROM wiki_feedback
            WHERE article_id = %s AND feedback_type IN ('outdated', 'needs_update')
        """, (id,))

        db.execute("""
            UPDATE wiki_articles
            SET status = CASE WHEN status='obsolete' THEN 'published' ELSE status END
            WHERE id = %s
        """, (id,))
        db.commit()

        return jsonify({"success": True, "message": "Article marqué comme mis à jour"})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

@wiki_bp.route("/wiki/article/<int:id>/feedback", methods=["POST"])
def submit_wiki_feedback(id):
    if "user" not in session:
        return jsonify({"success": False, "error": "Non autorisé"}), 403
    
    data = request.get_json() or {}
    feedback_type = data.get("feedback_type")
    comment = data.get("comment", "").strip()
    
    if not feedback_type or feedback_type not in ['useful', 'not_useful', 'outdated', 'needs_update']:
        return jsonify({"success": False, "error": "Type de feedback invalide"}), 400
    
    db = get_db()
    try:
        article = db.execute("""
            SELECT id, title, owner, created_by
            FROM wiki_articles
            WHERE id = %s
        """, (id,)).fetchone()
        if not article:
            return jsonify({"success": False, "error": "Article non trouvé"}), 404
        
        db.execute("""
            INSERT INTO wiki_feedback (article_id, user_name, feedback_type, comment)
            VALUES (%s, %s, %s, %s)
        """, (id, session["user"], feedback_type, comment))
        db.commit()

        if feedback_type == 'outdated':
            db.execute("""
                UPDATE wiki_articles
                SET status='obsolete'
                WHERE id=%s
            """, (id,))
            db.commit()

        if socketio and feedback_type in ['outdated', 'needs_update']:
            article_dict = dict(article)
            target_user = (article_dict.get("owner") or article_dict.get("created_by") or "").strip()
            if target_user and target_user.lower() != session["user"].lower():
                emit_wiki_update_requested_notification(
                    socketio,
                    article_id=id,
                    title=article_dict.get("title") or "Article",
                    requested_by=session["user"],
                    target_user=target_user,
                    request_type=feedback_type
                )

        return jsonify({"success": True, "message": "Feedback enregistré"})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

@wiki_bp.route("/wiki/admin")
def wiki_admin_dashboard():
    if "user" not in session or session.get("role") not in ["admin", "superadmin"]:
        flash("Accès réservé aux administrateurs", "error")
        return redirect(url_for("wiki.wiki"))
    
    db = get_db()
    
    outdated_articles = db.execute("""
        SELECT a.*, COUNT(f.id) as feedback_count
        FROM wiki_articles a
        INNER JOIN wiki_feedback f ON a.id = f.article_id
        WHERE f.feedback_type = 'outdated'
        GROUP BY a.id
        ORDER BY feedback_count DESC
        LIMIT 20
    """).fetchall()
    
    no_result_queries = db.execute("""
        SELECT query, COUNT(*) as count, MAX(created_at) as last_seen
        FROM wiki_search_log
        WHERE results_count = 0
        GROUP BY query
        ORDER BY count DESC, last_seen DESC
        LIMIT 10
    """).fetchall()
    
    low_views_articles = db.execute("""
        SELECT * FROM wiki_articles
        WHERE views_count < 5
        ORDER BY views_count ASC, created_at DESC
        LIMIT 20
    """).fetchall()
    
    negative_feedback = db.execute("""
        SELECT a.*, COUNT(f.id) as negative_count
        FROM wiki_articles a
        INNER JOIN wiki_feedback f ON a.id = f.article_id
        WHERE f.feedback_type IN ('not_useful', 'outdated')
        GROUP BY a.id
        ORDER BY negative_count DESC
        LIMIT 20
    """).fetchall()
    
    db.close()
    
    return render_template("wiki_admin_dashboard.html",
                         outdated_articles=[dict(a) for a in outdated_articles],
                         no_result_queries=[dict(q) for q in no_result_queries],
                         low_views_articles=[dict(a) for a in low_views_articles],
                         negative_feedback=[dict(a) for a in negative_feedback],
                         user=session["user"])

@wiki_bp.route("/wiki/review_needed")
def wiki_review_needed():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    db = get_db()
    
    articles_to_review = db.execute("""
        SELECT DISTINCT a.*, 
               CASE 
                   WHEN a.updated_at < NOW() - INTERVAL '6 months' THEN 'old'
                   WHEN EXISTS (
                       SELECT 1 FROM wiki_feedback f 
                       WHERE f.article_id = a.id AND f.feedback_type = 'outdated'
                   ) THEN 'outdated'
                   ELSE 'other'
               END as review_reason
        FROM wiki_articles a
        WHERE a.updated_at < NOW() - INTERVAL '6 months'
           OR EXISTS (
               SELECT 1 FROM wiki_feedback f 
               WHERE f.article_id = a.id AND f.feedback_type = 'outdated'
           )
        ORDER BY a.updated_at ASC
    """).fetchall()
    
    db.close()
    
    return render_template("wiki_review_needed.html",
                         articles=[dict(a) for a in articles_to_review],
                         user=session["user"])

@wiki_bp.route("/wiki/article/<int:id>/mark_reviewed", methods=["POST"])
def wiki_mark_reviewed(id):
    if "user" not in session:
        return jsonify({"error": "Non authentifié"}), 401

    db = get_db()

    try:
        db.execute("""
            DELETE FROM wiki_feedback
            WHERE article_id=%s AND feedback_type='outdated'
        """, (id,))

        db.execute("""
            UPDATE wiki_articles
            SET last_reviewed_at = NOW(),
                updated_at = NOW()
            WHERE id=%s
        """, (id,))

        db.commit()
        db.close()

        return jsonify({"success": True, "message": "Article marqué comme révisé"})

    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 500
