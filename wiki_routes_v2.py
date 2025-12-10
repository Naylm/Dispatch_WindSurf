"""
Routes pour le module Wiki V2.0 - Base de connaissances professionnelle
Fonctionnalités : Catégories, sous-catégories, articles, likes, historique, upload images
"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory, current_app
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime, timezone
import pytz
from db_config import get_db

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

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}  # SVG retiré pour sécurité (risque XSS)
UPLOAD_FOLDER = 'static/uploads/wiki'
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
def wiki_home(app):
    @app.route("/wiki")
    def wiki():
        if "user" not in session:
            return redirect(url_for("login"))
        
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
                WHERE category_id = ? 
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
                    WHERE subcategory_id = ? 
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
def wiki_categories_routes(app):
    @app.route("/wiki/category/create", methods=["POST"])
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
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, icon, description, color, position, session["user"]))
            db.commit()
            db.close()
            
            # Si c'est une requête AJAX, retourner JSON
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
            if is_ajax:
                return jsonify({"success": True, "message": "Catégorie créée avec succès!"})
            
            flash("Catégorie créée avec succès!", "success")
            return redirect(url_for("wiki"))
        except Exception as e:
            current_app.logger.exception(f"wiki_category_create: exception: {e}")
            return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500
    
    @app.route("/wiki/category/<int:id>/edit", methods=["POST"])
    def edit_wiki_category(id):
        if "user" not in session:
            return jsonify({"error": "Non autorisé"}), 403
        
        name = request.form.get("name", "").strip()
        icon = request.form.get("icon", "📁").strip()
        description = request.form.get("description", "").strip()
        color = request.form.get("color", "#4f46e5").strip()
        
        db = get_db()
        db.execute("""
            UPDATE wiki_categories 
            SET name=?, icon=?, description=?, color=?
            WHERE id=?
        """, (name, icon, description, color, id))
        db.commit()
        db.close()
        
        return jsonify({"success": True})
    
    @app.route("/wiki/category/<int:id>/delete", methods=["POST"])
    def delete_wiki_category(id):
        from flask_wtf.csrf import CSRFError
        
        try:
            current_app.logger.info(f"delete_wiki_category: POST on category_id={id}, form={dict(request.form)}, headers={dict(request.headers)}")
            
            if "user" not in session:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"success": False, "error": "Non autorisé"}), 403
                return redirect(url_for("login"))
            
            db = get_db()
            
            try:
                # Vérifier que la catégorie existe
                category = db.execute("SELECT id FROM wiki_categories WHERE id=?", (id,)).fetchone()
                if not category:
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return jsonify({"success": False, "error": "Catégorie non trouvée"}), 404
                    flash("Catégorie non trouvée", "error")
                    return redirect(url_for("wiki"))
                
                # Supprimer la catégorie
                db.execute("DELETE FROM wiki_categories WHERE id=?", (id,))
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
                return redirect(url_for("wiki"))
                
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
            return redirect(url_for("wiki"))
        except Exception as e:
            current_app.logger.exception(f"delete_wiki_category: exception for category {id}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "Erreur interne"}), 500
            flash("Erreur lors de la suppression", "error")
            return redirect(url_for("wiki"))

# ========== GESTION DES SOUS-CATÉGORIES ==========
def wiki_subcategories_routes(app):
    @app.route("/wiki/subcategory/create", methods=["POST"])
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
                "SELECT MAX(position) as max FROM wiki_subcategories WHERE category_id=?", 
                (category_id,)
            ).fetchone()
            position = (max_pos['max'] or 0) + 1
            
            db.execute("""
                INSERT INTO wiki_subcategories (name, category_id, icon, description, position, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, category_id, icon, description, position, session["user"]))
            db.commit()
            db.close()
            
            # Si c'est une requête AJAX, retourner JSON
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
            if is_ajax:
                return jsonify({"success": True, "message": "Sous-catégorie créée avec succès!"})
            
            flash("Sous-catégorie créée avec succès!", "success")
            return redirect(url_for("wiki"))
        except Exception as e:
            current_app.logger.exception(f"wiki_subcategory_create: exception: {e}")
            return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500
    
    @app.route("/wiki/subcategory/<int:id>/edit", methods=["POST"])
    def edit_wiki_subcategory(id):
        if "user" not in session:
            return jsonify({"error": "Non autorisé"}), 403
        
        name = request.form.get("name", "").strip()
        icon = request.form.get("icon", "📄").strip()
        description = request.form.get("description", "").strip()
        
        db = get_db()
        db.execute("""
            UPDATE wiki_subcategories 
            SET name=?, icon=?, description=?
            WHERE id=?
        """, (name, icon, description, id))
        db.commit()
        db.close()
        
        return jsonify({"success": True})
    
    @app.route("/wiki/subcategory/<int:id>/delete", methods=["POST"])
    def delete_wiki_subcategory(id):
        from flask_wtf.csrf import CSRFError
        
        try:
            current_app.logger.info(f"delete_wiki_subcategory: POST on subcategory_id={id}, form={dict(request.form)}, headers={dict(request.headers)}")
            
            if "user" not in session:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"success": False, "error": "Non autorisé"}), 403
                return redirect(url_for("login"))
            
            db = get_db()
            
            try:
                # Vérifier que la sous-catégorie existe
                subcategory = db.execute("SELECT id FROM wiki_subcategories WHERE id=?", (id,)).fetchone()
                if not subcategory:
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return jsonify({"success": False, "error": "Sous-catégorie non trouvée"}), 404
                    flash("Sous-catégorie non trouvée", "error")
                    return redirect(url_for("wiki"))
                
                # Supprimer la sous-catégorie (les articles seront orphelins ou supprimés selon cascade)
                db.execute("DELETE FROM wiki_subcategories WHERE id=?", (id,))
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
                return redirect(url_for("wiki"))
                
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
            return redirect(url_for("wiki"))
        except Exception as e:
            current_app.logger.exception(f"delete_wiki_subcategory: exception for subcategory {id}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "Erreur interne"}), 500
            flash("Erreur lors de la suppression", "error")
            return redirect(url_for("wiki"))

# ========== GESTION DES ARTICLES ==========
def wiki_articles_routes(app):
    @app.route("/wiki/article/create", methods=["GET", "POST"])
    def create_wiki_article():
        if "user" not in session:
            return redirect(url_for("login"))
        
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
        current_app.logger.info(f"wiki_article_create: form keys = {list(request.form.keys())}")
        
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
        
        current_app.logger.info(f"wiki_article_create: title='{title[:50] if title else 'EMPTY'}', subcategory_id={subcategory_id} (from '{subcategory_id_str}'), content_length={len(content)}")
        
        # Validation
        if not title or not subcategory_id:
            current_app.logger.warning(
                f"wiki_article_create: invalid data "
                f"title='{title}', subcategory_id={subcategory_id} (original: '{subcategory_id_str}')"
            )
            flash("Titre et sous-catégorie sont obligatoires.", "error")
            return redirect(request.referrer or url_for("wiki"))
        
        if not content or len(content.strip()) < 10:
            flash("Le contenu est obligatoire et doit contenir au moins 10 caractères.", "error")
            return redirect(request.referrer or url_for("wiki"))
        
        # Validation des tags (format: séparés par virgules)
        if tags:
            tag_list = [t.strip() for t in tags.split(',') if t.strip()]
            if len(tag_list) > 10:
                flash("Maximum 10 tags autorisés.", "error")
                return redirect(request.referrer or url_for("wiki"))
        
        # Récupérer le statut (par défaut: draft)
        status = request.form.get("status", "draft")
        if status not in ['draft', 'published', 'archived']:
            status = 'draft'
        
        owner = request.form.get("owner", session["user"])
        summary = request.form.get("summary", "").strip()
        
        db = get_db()
        try:
            current_app.logger.info(f"wiki_article_create: Attempting INSERT with title='{title[:30]}', subcategory_id={subcategory_id}")
            
            result = db.execute(
                """
                INSERT INTO wiki_articles 
                (title, content, subcategory_id, icon, created_by, tags, status, owner, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (title, content, subcategory_id, icon, session["user"], tags, status, owner, summary)
            )
            
            row = result.fetchone()
            article_id = row["id"]
            current_app.logger.info(f"wiki_article_create: INSERT successful, article_id={article_id}")
            
            db.commit()
            current_app.logger.info(f"wiki_article_create: COMMIT successful")
            current_app.logger.info(f"wiki_article_create: OK article_id={article_id}")
            
        except Exception as e:
            db.rollback()
            current_app.logger.exception("wiki_article_create: ERROR")
            flash(f"Erreur lors de la création de l'article: {str(e)}", "error")
            return redirect(request.referrer or url_for("wiki"))
        finally:
            db.close()
        
        # Redirection vers la page de l'article
        flash("Article créé avec succès!", "success")
        return redirect(url_for("view_wiki_article", id=article_id))
    
    @app.route("/wiki/article/<int:id>")
    def view_wiki_article(id):
        if "user" not in session:
            return redirect(url_for("login"))
        
        current_app.logger.info(f"view_wiki_article: START for article_id={id}")
        
        db = get_db()
        try:
            # Récupérer l'article d'abord (sans JOIN pour simplifier)
            current_app.logger.info(f"view_wiki_article: Fetching article {id}")
            article = db.execute("SELECT * FROM wiki_articles WHERE id = ?", (id,)).fetchone()
            
            if not article:
                current_app.logger.warning(f"view_wiki_article: Article {id} not found")
                flash("Article non trouvé", "error")
                return redirect(url_for("wiki"))
            
            # Convertir en dict immédiatement pour éviter les problèmes avec DualAccessRow
            article_dict = dict(article)
            
            # Convertir les dates en timezone Europe/Paris
            if article_dict.get('created_at'):
                try:
                    article_dict['created_at'] = to_paris(article_dict['created_at'])
                except Exception as date_error:
                    current_app.logger.warning(f"view_wiki_article: Could not convert created_at: {date_error}")
            
            if article_dict.get('updated_at'):
                try:
                    article_dict['updated_at'] = to_paris(article_dict['updated_at'])
                except Exception as date_error:
                    current_app.logger.warning(f"view_wiki_article: Could not convert updated_at: {date_error}")
            
            current_app.logger.info(f"view_wiki_article: Article found: {article_dict.get('title', 'NO TITLE')[:50]}")
            
            # Récupérer les infos de catégorie et sous-catégorie si subcategory_id existe
            subcat_name = None
            cat_name = None
            cat_icon = None
            cat_id = None
            
            if article_dict.get('subcategory_id'):
                try:
                    subcat = db.execute("""
                        SELECT s.*, c.name as cat_name, c.icon as cat_icon, c.id as cat_id
                        FROM wiki_subcategories s
                        LEFT JOIN wiki_categories c ON s.category_id = c.id
                        WHERE s.id = ?
                    """, (article_dict['subcategory_id'],)).fetchone()
                    
                    if subcat:
                        subcat_dict = dict(subcat)
                        subcat_name = subcat_dict.get('name')
                        cat_name = subcat_dict.get('cat_name')
                        cat_icon = subcat_dict.get('cat_icon')
                        cat_id = subcat_dict.get('cat_id')
                except Exception as subcat_error:
                    current_app.logger.warning(f"view_wiki_article: Could not fetch subcategory info: {subcat_error}")
            
            # Incrémenter le compteur de vues
            try:
                db.execute("UPDATE wiki_articles SET views_count = views_count + 1 WHERE id=?", (id,))
                db.commit()
            except Exception as views_error:
                current_app.logger.warning(f"view_wiki_article: Could not update views_count: {views_error}")
                db.rollback()
            
            # Récupérer le vote de l'utilisateur (si la table existe)
            user_vote_dict = None
            try:
                user_vote = db.execute("""
                    SELECT vote_type FROM wiki_votes 
                    WHERE article_id=? AND user_name=?
                """, (id, session["user"])).fetchone()
                if user_vote:
                    user_vote_dict = dict(user_vote)
            except Exception as vote_error:
                current_app.logger.warning(f"view_wiki_article: Could not fetch user vote: {vote_error}")
            
            # Récupérer l'historique (si la table existe)
            history_list = []
            try:
                history = db.execute("""
                    SELECT * FROM wiki_history 
                    WHERE article_id=? 
                    ORDER BY modified_at DESC 
                    LIMIT 10
                """, (id,)).fetchall()
                if history:
                    history_list = []
                    for h in history:
                        hist_dict = dict(h)
                        # Convertir modified_at en timezone Europe/Paris
                        if hist_dict.get('modified_at'):
                            try:
                                hist_dict['modified_at'] = to_paris(hist_dict['modified_at'])
                            except Exception as date_error:
                                current_app.logger.warning(f"view_wiki_article: Could not convert modified_at: {date_error}")
                        history_list.append(hist_dict)
            except Exception as hist_error:
                current_app.logger.warning(f"view_wiki_article: Could not fetch history: {hist_error}")
            
            # Ajouter les infos supplémentaires au dictionnaire article
            article_dict['subcat_name'] = subcat_name
            article_dict['cat_name'] = cat_name
            article_dict['cat_icon'] = cat_icon
            article_dict['cat_id'] = cat_id
            
            current_app.logger.info(f"view_wiki_article: Rendering template for article {id}")
            
            return render_template("wiki_article_view_v2.html",
                                 article=article_dict,
                                 user_vote=user_vote_dict,
                                 history=history_list,
                                 user=session["user"],
                                 role=session["role"])
                                 
        except Exception as e:
            current_app.logger.exception(f"view_wiki_article: EXCEPTION for article {id}: {e}")
            flash(f"Erreur lors de l'affichage de l'article: {str(e)}", "error")
            return redirect(url_for("wiki"))
        finally:
            db.close()
    
    @app.route("/wiki/article/<int:id>/edit", methods=["GET", "POST"])
    def edit_wiki_article(id):
        if "user" not in session:
            return redirect(url_for("login"))
        
        db = get_db()
        article = db.execute("SELECT * FROM wiki_articles WHERE id=?", (id,)).fetchone()
        
        if not article:
            flash("Article non trouvé", "error")
            return redirect(url_for("wiki"))
        
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
        
        # Validation
        if not title:
            flash("Le titre est obligatoire.", "error")
            return redirect(request.referrer or url_for("wiki"))
        
        if not content or len(content.strip()) < 10:
            flash("Le contenu est obligatoire et doit contenir au moins 10 caractères.", "error")
            return redirect(request.referrer or url_for("wiki"))
        
        # Validation des tags
        if tags:
            tag_list = [t.strip() for t in tags.split(',') if t.strip()]
            if len(tag_list) > 10:
                flash("Maximum 10 tags autorisés.", "error")
                return redirect(request.referrer or url_for("wiki"))
        
        # Récupérer les métadonnées
        status = request.form.get("status", article.get('status', 'draft'))
        if status not in ['draft', 'published', 'archived']:
            status = article.get('status', 'draft')
        
        owner = request.form.get("owner", article.get('owner', session["user"]))
        summary = request.form.get("summary", article.get('summary', '')).strip()
        
        # Sauvegarder dans l'historique
        db.execute("""
            INSERT INTO wiki_history (article_id, title, content, modified_by, change_description)
            VALUES (?, ?, ?, ?, ?)
        """, (id, article['title'], article['content'], session["user"], change_description or "Modification"))
        
        # Mettre à jour l'article
        db.execute("""
            UPDATE wiki_articles 
            SET title=?, content=?, subcategory_id=?, icon=?, tags=?,
                status=?, owner=?, summary=?,
                updated_at=CURRENT_TIMESTAMP, last_modified_by=?
            WHERE id=?
        """, (title, content, subcategory_id, icon, tags, status, owner, summary, session["user"], id))
        
        db.commit()
        db.close()
        
        flash("Article mis à jour avec succès!", "success")
        return redirect(url_for("view_wiki_article", id=id))
    
    @app.route("/wiki/article/<int:id>/delete", methods=["POST"])
    def delete_wiki_article(id):
        from flask_wtf.csrf import CSRFError
        
        try:
            current_app.logger.info(f"delete_wiki_article: POST on article_id={id}, form={dict(request.form)}, headers={dict(request.headers)}")
            
            if "user" not in session:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"success": False, "error": "Non autorisé"}), 403
                return redirect(url_for("login"))
            
            db = get_db()
            
            try:
                # Vérifier que l'article existe
                article = db.execute("SELECT id FROM wiki_articles WHERE id=?", (id,)).fetchone()
                if not article:
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return jsonify({"success": False, "error": "Article non trouvé"}), 404
                    flash("Article non trouvé", "error")
                    return redirect(url_for("wiki"))
                
                # Supprimer l'article
                db.execute("DELETE FROM wiki_articles WHERE id=?", (id,))
                db.commit()
                db.close()
                
                # Réponse selon le type de requête
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({
                        "success": True,
                        "status": "ok",
                        "redirect_url": url_for("wiki")
                    }), 200
                
                flash("Article supprimé", "success")
                return redirect(url_for("wiki"))
                
            except Exception as db_error:
                db.rollback()
                db.close()
                current_app.logger.exception(f"delete_wiki_article: Database error for article {id}")
                raise
                
        except CSRFError as e:
            current_app.logger.warning(f"delete_wiki_article CSRF error: {e.description}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "CSRF token invalide"}), 400
            flash("Erreur CSRF", "error")
            return redirect(url_for("wiki"))
        except Exception as e:
            current_app.logger.exception(f"delete_wiki_article: exception for article {id}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "Erreur interne"}), 500
            flash("Erreur lors de la suppression", "error")
            return redirect(url_for("wiki"))
    
    @app.route("/wiki/article/<int:id>/move", methods=["POST"])
    def move_wiki_article(id):
        """Déplacer un article vers une autre sous-catégorie"""
        if "user" not in session:
            return jsonify({"error": "Non autorisé"}), 403
        
        new_subcategory_id = request.form.get("new_subcategory_id")
        
        db = get_db()
        db.execute("UPDATE wiki_articles SET subcategory_id=? WHERE id=?", 
                  (new_subcategory_id, id))
        db.commit()
        db.close()
        
        flash("Article déplacé avec succès!", "success")
        return redirect(url_for("view_wiki_article", id=id))

# ========== SYSTÈME DE VOTES ==========
def wiki_votes_routes(app):
    @app.route("/wiki/article/<int:id>/vote", methods=["POST"])
    def vote_wiki_article(id):
        from flask_wtf.csrf import CSRFError

        try:
            current_app.logger.info(f"vote_wiki_article: Received vote for article {id}")
            current_app.logger.info(f"vote_wiki_article: Headers: {dict(request.headers)}")
            current_app.logger.info(f"vote_wiki_article: is_json: {request.is_json}")

            if "user" not in session:
                current_app.logger.warning(f"vote_wiki_article: User not in session")
                return jsonify({
                    "success": False,
                    "error": "Non autorisé"
                }), 403

            # Récupération du sens du vote (like/dislike)
            vote_type = None
            if request.is_json:
                vote_type = request.json.get("vote_type") or request.json.get("direction")
            else:
                vote_type = request.form.get("vote_type") or request.form.get("direction")

            current_app.logger.info(f"vote_wiki_article: User {session['user']} voting {vote_type}")
            
            if vote_type not in ['like', 'dislike', 'up', 'down']:
                return jsonify({
                    "success": False,
                    "error": "Type de vote invalide. Utilisez 'like'/'dislike' ou 'up'/'down'"
                }), 400
            
            # Normaliser: up -> like, down -> dislike
            if vote_type == 'up':
                vote_type = 'like'
            elif vote_type == 'down':
                vote_type = 'dislike'
            
            db = get_db()
            
            try:
                # Vérifier si l'utilisateur a déjà voté
                existing_vote = db.execute("""
                    SELECT vote_type FROM wiki_votes 
                    WHERE article_id=? AND user_name=?
                """, (id, session["user"])).fetchone()
                
                if existing_vote:
                    existing_vote_dict = dict(existing_vote)
                    old_vote = existing_vote_dict.get('vote_type')
                    db.execute("DELETE FROM wiki_votes WHERE article_id=? AND user_name=?", 
                              (id, session["user"]))
                    
                    # Décrémenter le compteur
                    if old_vote == 'like':
                        db.execute("UPDATE wiki_articles SET likes_count = likes_count - 1 WHERE id=?", (id,))
                    else:
                        db.execute("UPDATE wiki_articles SET dislikes_count = dislikes_count - 1 WHERE id=?", (id,))
                    
                    # Si même vote, on le supprime juste
                    if old_vote == vote_type:
                        db.commit()
                        article = db.execute("SELECT likes_count, dislikes_count FROM wiki_articles WHERE id=?", (id,)).fetchone()

                        current_app.logger.info(f"vote_wiki_article (remove): article={article}")

                        # Récupérer directement les valeurs
                        if article:
                            current_app.logger.info(f"vote_wiki_article (remove): article.keys()={list(article.keys())}")
                            likes_count = article['likes_count']
                            dislikes_count = article['dislikes_count']
                        else:
                            current_app.logger.warning(f"vote_wiki_article (remove): Article {id} not found!")
                            likes_count = 0
                            dislikes_count = 0

                        db.close()

                        current_app.logger.info(f"vote_wiki_article (remove): FINAL likes={likes_count}, dislikes={dislikes_count}")

                        return jsonify({
                            "success": True,
                            "status": "ok",
                            "likes": likes_count,
                            "dislikes": dislikes_count,
                            "user_vote": None
                        }), 200
                
                # Ajouter le nouveau vote
                db.execute("""
                    INSERT INTO wiki_votes (article_id, user_name, vote_type)
                    VALUES (?, ?, ?)
                """, (id, session["user"], vote_type))
                
                # Incrémenter le compteur
                if vote_type == 'like':
                    db.execute("UPDATE wiki_articles SET likes_count = likes_count + 1 WHERE id=?", (id,))
                else:
                    db.execute("UPDATE wiki_articles SET dislikes_count = dislikes_count + 1 WHERE id=?", (id,))
                
                db.commit()
                
                article = db.execute("SELECT likes_count, dislikes_count FROM wiki_articles WHERE id=?", (id,)).fetchone()

                current_app.logger.info(f"vote_wiki_article: article={article}")

                # Récupérer directement les valeurs pour éviter tout problème de clés
                if article:
                    current_app.logger.info(f"vote_wiki_article: article.keys()={list(article.keys())}")
                    likes_count = article['likes_count']
                    dislikes_count = article['dislikes_count']
                else:
                    current_app.logger.warning(f"vote_wiki_article: Article {id} not found after vote!")
                    likes_count = 0
                    dislikes_count = 0

                db.close()

                current_app.logger.info(f"vote_wiki_article: FINAL likes={likes_count}, dislikes={dislikes_count}, user_vote={vote_type}")

                return jsonify({
                    "success": True,
                    "status": "ok",
                    "likes": likes_count,
                    "dislikes": dislikes_count,
                    "user_vote": vote_type
                }), 200
                
            except Exception as db_error:
                db.rollback()
                db.close()
                current_app.logger.exception(f"vote_wiki_article: Database error for article {id}")
                raise
                
        except CSRFError as e:
            current_app.logger.error(f"vote_wiki_article CSRF error: {e.description}")
            current_app.logger.error(f"vote_wiki_article CSRF headers: X-CSRFToken={request.headers.get('X-CSRFToken')}, X-CSRF-Token={request.headers.get('X-CSRF-Token')}")
            return jsonify({
                "success": False,
                "error": f"CSRF token invalide ou manquant: {e.description}"
            }), 400
        except Exception as e:
            current_app.logger.exception(f"vote_wiki_article: exception for article {id}")
            return jsonify({
                "success": False,
                "error": "Erreur interne lors du vote"
            }), 500

# ========== UPLOAD D'IMAGES ==========
def wiki_upload_routes(app):
    @app.route("/wiki/upload", methods=["POST"])
    def upload_wiki_image():
        try:
            if "user" not in session:
                return jsonify({"error": "Non autorisé"}), 403
            
            if 'file' not in request.files:
                return jsonify({"error": "Aucun fichier"}), 400
            
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({"error": "Aucun fichier sélectionné"}), 400
            
            if not allowed_file(file.filename):
                return jsonify({"error": "Type de fichier non autorisé"}), 400

            # Vérifier la taille du fichier
            file.seek(0, 2)  # Aller à la fin
            file_size = file.tell()
            file.seek(0)  # Revenir au début

            if file_size > MAX_FILE_SIZE:
                return jsonify({"error": f"Fichier trop volumineux (max {MAX_FILE_SIZE // (1024*1024)}MB)"}), 400

            # Valider le contenu du fichier (magic bytes)
            if not validate_image_content(file.stream):
                return jsonify({"error": "Le contenu du fichier ne correspond pas à une image valide"}), 400

            # Créer le dossier si nécessaire
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            # Générer un nom de fichier sécurisé et unique avec UUID
            original_filename = secure_filename(file.filename)
            file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'jpg'
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(filepath)
            
            # Sauvegarder dans la base de données
            db = get_db()
            db.execute("""
                INSERT INTO wiki_images (filename, original_filename, filepath, uploaded_by, file_size)
                VALUES (?, ?, ?, ?, ?)
            """, (unique_filename, original_filename, filepath, session["user"], file_size))
            db.commit()
            db.close()
            
            # Retourner l'URL de l'image
            image_url = url_for('static', filename=f'uploads/wiki/{unique_filename}')
            
            # Toujours renvoyer du JSON, même en cas d'erreur
            return jsonify({
                "success": True,
                "status": "ok",
                "url": image_url,
                "filename": unique_filename
            }), 200
        
        except Exception as e:
            current_app.logger.exception(f"wiki_upload_image: exception: {e}")
            # Toujours renvoyer du JSON, jamais de HTML
            return jsonify({
                "success": False,
                "status": "error",
                "error": f"Erreur serveur: {str(e)}"
            }), 500

# ========== RECHERCHE ==========
def wiki_search_routes(app):
    @app.route("/wiki/search/suggestions")
    def wiki_search_suggestions():
        if "user" not in session:
            return jsonify({"suggestions": []})
        
        query = request.args.get("q", "").strip()
        if len(query) < 2:
            return jsonify({"suggestions": []})
        
        db = get_db()
        
        # Rechercher des titres d'articles similaires
        try:
            # Utiliser ILIKE pour suggestions rapides (insensible à la casse)
            suggestions = db.execute("""
                SELECT DISTINCT title, id
                FROM wiki_articles
                WHERE title ILIKE %s
                ORDER BY title
                LIMIT 10
            """, (f"%{query}%",)).fetchall()
            
            result = [{"title": s['title'], "id": s['id']} for s in suggestions]
        except Exception as e:
            current_app.logger.warning(f"Erreur suggestions: {e}")
            result = []
        finally:
            db.close()
        
        return jsonify({"suggestions": result})
    
    @app.route("/wiki/search")
    def search_wiki():
        if "user" not in session:
            return redirect(url_for("login"))
        
        query = request.args.get("q", "").strip()
        
        if not query:
            return redirect(url_for("wiki"))
        
        # Préparer la requête pour PostgreSQL full-text search
        # Échapper les caractères spéciaux et convertir en format tsquery
        # Remplacer les espaces par & (AND) pour recherche stricte
        query_terms = query.split()
        query_ts = ' & '.join([term.replace("'", "''") for term in query_terms])
        
        db = get_db()
        
        # Recherche full-text avec ranking
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
        except Exception as e:
            # Fallback vers LIKE si erreur avec full-text
            current_app.logger.warning(f"Erreur recherche full-text, fallback LIKE: {e}")
            results = db.execute("""
                SELECT a.*, s.name as subcat_name, c.name as cat_name, c.icon as cat_icon, 0 as rank
                FROM wiki_articles a
                LEFT JOIN wiki_subcategories s ON a.subcategory_id = s.id
                LEFT JOIN wiki_categories c ON s.category_id = c.id
                WHERE a.title LIKE %s OR a.content LIKE %s OR a.tags LIKE %s
                ORDER BY a.created_at DESC
            """, (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
        
        # Logger la recherche (surtout si 0 résultat)
        results_count = len(results)
        try:
            db.execute("""
                INSERT INTO wiki_search_log (query, user_name, results_count)
                VALUES (%s, %s, %s)
            """, (query, session.get("user"), results_count))
            db.commit()
        except Exception as log_error:
            current_app.logger.warning(f"Erreur logging recherche: {log_error}")
        
        db.close()
        
        return render_template("wiki_search_results_v2.html",
                             query=query,
                             results=[dict(r) for r in results],
                             user=session["user"])

# ========== FEEDBACK ==========
def wiki_feedback_routes(app):
    @app.route("/wiki/article/<int:id>/feedback", methods=["POST"])
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
            # Vérifier que l'article existe
            article = db.execute("SELECT id FROM wiki_articles WHERE id = %s", (id,)).fetchone()
            if not article:
                return jsonify({"success": False, "error": "Article non trouvé"}), 404
            
            # Insérer le feedback
            db.execute("""
                INSERT INTO wiki_feedback (article_id, user_name, feedback_type, comment)
                VALUES (%s, %s, %s, %s)
            """, (id, session["user"], feedback_type, comment))
            db.commit()
            
            return jsonify({"success": True, "message": "Feedback enregistré"})
        except Exception as e:
            db.rollback()
            current_app.logger.exception(f"Erreur submit_wiki_feedback: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            db.close()

# ========== ADMIN DASHBOARD ==========
def wiki_admin_routes(app):
    @app.route("/wiki/admin")
    def wiki_admin_dashboard():
        if "user" not in session or session.get("role") != "admin":
            flash("Accès réservé aux administrateurs", "error")
            return redirect(url_for("wiki"))
        
        db = get_db()
        
        # Articles signalés obsolètes
        outdated_articles = db.execute("""
            SELECT a.*, COUNT(f.id) as feedback_count
            FROM wiki_articles a
            INNER JOIN wiki_feedback f ON a.id = f.article_id
            WHERE f.feedback_type = 'outdated'
            GROUP BY a.id
            ORDER BY feedback_count DESC
            LIMIT 20
        """).fetchall()
        
        # Requêtes sans résultat (top 10)
        no_result_queries = db.execute("""
            SELECT query, COUNT(*) as count, MAX(created_at) as last_seen
            FROM wiki_search_log
            WHERE results_count = 0
            GROUP BY query
            ORDER BY count DESC, last_seen DESC
            LIMIT 10
        """).fetchall()
        
        # Articles peu consultés (< 5 vues)
        low_views_articles = db.execute("""
            SELECT * FROM wiki_articles
            WHERE views_count < 5
            ORDER BY views_count ASC, created_at DESC
            LIMIT 20
        """).fetchall()
        
        # Articles avec feedback négatif
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

# ========== REVIEW SYSTEM ==========
def wiki_review_routes(app):
    @app.route("/wiki/review_needed")
    def wiki_review_needed():
        if "user" not in session:
            return redirect(url_for("login"))
        
        db = get_db()
        
        # Articles à revoir (> 6 mois sans mise à jour OU signalés obsolètes)
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

def register_wiki_routes(app):
    """Enregistrer toutes les routes Wiki V2"""
    wiki_home(app)
    wiki_categories_routes(app)
    wiki_subcategories_routes(app)
    wiki_articles_routes(app)
    wiki_votes_routes(app)
    wiki_upload_routes(app)
    wiki_search_routes(app)
    wiki_feedback_routes(app)
    wiki_admin_routes(app)
    wiki_review_routes(app)
