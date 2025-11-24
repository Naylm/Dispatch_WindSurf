"""
Routes pour le module Wiki V2.0 - Base de connaissances professionnelle
Fonctionnalités : Catégories, sous-catégories, articles, likes, historique, upload images
"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from db_config import get_db

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
        if "user" not in session:
            return jsonify({"error": "Non autorisé"}), 403
        
        name = request.form.get("name", "").strip()
        icon = request.form.get("icon", "📁").strip()
        description = request.form.get("description", "").strip()
        color = request.form.get("color", "#4f46e5").strip()
        
        if not name:
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
        
        flash("Catégorie créée avec succès!", "success")
        return redirect(url_for("wiki"))
    
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
        if "user" not in session:
            return jsonify({"error": "Non autorisé"}), 403
        
        db = get_db()
        db.execute("DELETE FROM wiki_categories WHERE id=?", (id,))
        db.commit()
        db.close()
        
        flash("Catégorie supprimée", "success")
        return redirect(url_for("wiki"))

# ========== GESTION DES SOUS-CATÉGORIES ==========
def wiki_subcategories_routes(app):
    @app.route("/wiki/subcategory/create", methods=["POST"])
    def create_wiki_subcategory():
        if "user" not in session:
            return jsonify({"error": "Non autorisé"}), 403
        
        name = request.form.get("name", "").strip()
        category_id = request.form.get("category_id")
        icon = request.form.get("icon", "📄").strip()
        description = request.form.get("description", "").strip()
        
        if not name or not category_id:
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
        
        flash("Sous-catégorie créée avec succès!", "success")
        return redirect(url_for("wiki"))
    
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
        if "user" not in session:
            return jsonify({"error": "Non autorisé"}), 403
        
        db = get_db()
        # Supprimer la sous-catégorie (les articles seront orphelins ou supprimés selon cascade)
        db.execute("DELETE FROM wiki_subcategories WHERE id=?", (id,))
        db.commit()
        db.close()
        
        flash("Sous-catégorie supprimée", "success")
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
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "")
        subcategory_id = request.form.get("subcategory_id")
        icon = request.form.get("icon", "📝").strip()
        tags = request.form.get("tags", "").strip()
        
        if not title:
            flash("Le titre est requis", "error")
            return redirect(url_for("create_wiki_article"))
        
        db = get_db()
        cursor = db.execute("""
            INSERT INTO wiki_articles 
            (title, content, subcategory_id, icon, created_by, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, content, subcategory_id, icon, session["user"], tags))
        
        article_id = cursor.lastrowid
        db.commit()
        db.close()
        
        flash("Article créé avec succès!", "success")
        return redirect(url_for("view_wiki_article", id=article_id))
    
    @app.route("/wiki/article/<int:id>")
    def view_wiki_article(id):
        if "user" not in session:
            return redirect(url_for("login"))
        
        db = get_db()
        
        # Incrémenter le compteur de vues
        db.execute("UPDATE wiki_articles SET views_count = views_count + 1 WHERE id=?", (id,))
        db.commit()
        
        # Récupérer l'article
        article = db.execute("""
            SELECT a.*, s.name as subcat_name, c.name as cat_name, c.icon as cat_icon, c.id as cat_id
            FROM wiki_articles a
            LEFT JOIN wiki_subcategories s ON a.subcategory_id = s.id
            LEFT JOIN wiki_categories c ON s.category_id = c.id
            WHERE a.id = ?
        """, (id,)).fetchone()
        
        if not article:
            flash("Article non trouvé", "error")
            return redirect(url_for("wiki"))
        
        # Récupérer le vote de l'utilisateur
        user_vote = db.execute("""
            SELECT vote_type FROM wiki_votes 
            WHERE article_id=? AND user_name=?
        """, (id, session["user"])).fetchone()
        
        # Récupérer l'historique
        history = db.execute("""
            SELECT * FROM wiki_history 
            WHERE article_id=? 
            ORDER BY modified_at DESC 
            LIMIT 10
        """, (id,)).fetchall()
        
        db.close()
        
        return render_template("wiki_article_view_v2.html",
                             article=dict(article),
                             user_vote=dict(user_vote) if user_vote else None,
                             history=[dict(h) for h in history],
                             user=session["user"],
                             role=session["role"])
    
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
        
        # Sauvegarder dans l'historique
        db.execute("""
            INSERT INTO wiki_history (article_id, title, content, modified_by, change_description)
            VALUES (?, ?, ?, ?, ?)
        """, (id, article['title'], article['content'], session["user"], change_description or "Modification"))
        
        # Mettre à jour l'article
        db.execute("""
            UPDATE wiki_articles 
            SET title=?, content=?, subcategory_id=?, icon=?, tags=?,
                updated_at=CURRENT_TIMESTAMP, last_modified_by=?
            WHERE id=?
        """, (title, content, subcategory_id, icon, tags, session["user"], id))
        
        db.commit()
        db.close()
        
        flash("Article mis à jour avec succès!", "success")
        return redirect(url_for("view_wiki_article", id=id))
    
    @app.route("/wiki/article/<int:id>/delete", methods=["POST"])
    def delete_wiki_article(id):
        if "user" not in session:
            return jsonify({"error": "Non autorisé"}), 403
        
        db = get_db()
        # Tout le monde peut supprimer (système collaboratif)
        
        db.execute("DELETE FROM wiki_articles WHERE id=?", (id,))
        db.commit()
        db.close()
        
        flash("Article supprimé", "success")
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
        if "user" not in session:
            return jsonify({"error": "Non autorisé"}), 403
        
        vote_type = request.json.get("vote_type")  # 'like' ou 'dislike'
        
        if vote_type not in ['like', 'dislike']:
            return jsonify({"error": "Type de vote invalide"}), 400
        
        db = get_db()
        
        # Vérifier si l'utilisateur a déjà voté
        existing_vote = db.execute("""
            SELECT vote_type FROM wiki_votes 
            WHERE article_id=? AND user_name=?
        """, (id, session["user"])).fetchone()
        
        if existing_vote:
            # Retirer l'ancien vote
            old_vote = existing_vote['vote_type']
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
                db.close()
                return jsonify({"success": True, "likes": article['likes_count'], "dislikes": article['dislikes_count'], "user_vote": None})
        
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
        db.close()
        
        return jsonify({"success": True, "likes": article['likes_count'], "dislikes": article['dislikes_count'], "user_vote": vote_type})

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
            
            return jsonify({"success": True, "url": image_url, "filename": unique_filename})
        
        except Exception as e:
            return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500

# ========== RECHERCHE ==========
def wiki_search_routes(app):
    @app.route("/wiki/search")
    def search_wiki():
        if "user" not in session:
            return redirect(url_for("login"))
        
        query = request.args.get("q", "").strip()
        
        if not query:
            return redirect(url_for("wiki"))
        
        db = get_db()
        results = db.execute("""
            SELECT a.*, s.name as subcat_name, c.name as cat_name, c.icon as cat_icon
            FROM wiki_articles a
            LEFT JOIN wiki_subcategories s ON a.subcategory_id = s.id
            LEFT JOIN wiki_categories c ON s.category_id = c.id
            WHERE a.title LIKE ? OR a.content LIKE ? OR a.tags LIKE ?
            ORDER BY a.created_at DESC
        """, (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
        
        db.close()
        
        return render_template("wiki_search_results_v2.html",
                             query=query,
                             results=[dict(r) for r in results],
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
