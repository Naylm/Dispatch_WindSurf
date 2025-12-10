"""
Script de vérification et garantie de l'intégrité de la base de données PostgreSQL
Ce script s'assure que toutes les tables nécessaires existent et sont correctement structurées
"""
import os
from werkzeug.security import generate_password_hash
from db_config import get_db

def ensure_database_integrity():
    """Garantit que toutes les tables nécessaires existent avec la bonne structure"""
    
    print("Verification de l'integrite de la base de donnees PostgreSQL...")
    
    conn = get_db()
    cursor = conn.cursor()
    
    tables_created = []
    tables_verified = []
    
    # ========== TABLE: users ==========
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'users'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                force_password_reset INTEGER DEFAULT 0
            )
        """)
        # Créer un admin par défaut (mot de passe: admin)
        admin_hash = generate_password_hash('admin')
        cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES (%s, %s, %s)
        """, ('admin', admin_hash, 'admin'))
        tables_created.append("users")
    else:
        tables_verified.append("users")
        # Migration: s'assurer que la colonne force_password_reset existe
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='users' AND column_name='force_password_reset'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN force_password_reset INTEGER DEFAULT 0")
            print("   - Colonne force_password_reset ajoutee a la table users")
    
    # ========== TABLE: techniciens ==========
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'techniciens'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE techniciens (
                id SERIAL PRIMARY KEY,
                prenom VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255),
                role VARCHAR(50) DEFAULT 'technicien',
                actif INTEGER DEFAULT 1,
                force_password_reset INTEGER DEFAULT 0,
                ordre INTEGER DEFAULT 0
            )
        """)
        tables_created.append("techniciens")
    else:
        tables_verified.append("techniciens")
        # Migration: s'assurer que la colonne force_password_reset existe
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='techniciens' AND column_name='force_password_reset'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE techniciens ADD COLUMN force_password_reset INTEGER DEFAULT 0")
            print("   - Colonne force_password_reset ajoutee a la table techniciens")
        
        # Migration: s'assurer que la colonne ordre existe
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='techniciens' AND column_name='ordre'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE techniciens ADD COLUMN ordre INTEGER DEFAULT 0")
            print("   - Colonne ordre ajoutee a la table techniciens")
            # Initialiser l'ordre pour les techniciens existants basé sur leur id
            cursor.execute("""
                UPDATE techniciens 
                SET ordre = id 
                WHERE ordre = 0 OR ordre IS NULL
            """)
            print("   - Ordre initialise pour les techniciens existants")
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='techniciens' AND column_name='force_password_reset'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE techniciens ADD COLUMN force_password_reset INTEGER DEFAULT 0")
            print("   - Colonne force_password_reset ajoutee a la table techniciens")
    
    # ========== TABLE: incidents ==========
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'incidents'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE incidents (
                id SERIAL PRIMARY KEY,
                numero VARCHAR(255) NOT NULL,
                site VARCHAR(255) NOT NULL,
                sujet VARCHAR(255) NOT NULL,
                urgence VARCHAR(255) NOT NULL,
                collaborateur VARCHAR(255) NOT NULL,
                etat VARCHAR(255) DEFAULT 'Affecté',
                notes TEXT,
                note_dispatch TEXT,
                valide INTEGER DEFAULT 0,
                date_affectation DATE NOT NULL,
                archived INTEGER DEFAULT 0,
                localisation VARCHAR(255) DEFAULT ''
            )
        """)
        tables_created.append("incidents")
    else:
        tables_verified.append("incidents")
        # Migration: s'assurer que la colonne note_dispatch existe
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='incidents' AND column_name='note_dispatch'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE incidents ADD COLUMN note_dispatch TEXT")
            print("   - Colonne note_dispatch ajoutee a la table incidents")
    
    # ========== TABLE: historique ==========
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'historique'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE historique (
                id SERIAL PRIMARY KEY,
                incident_id INTEGER NOT NULL,
                champ VARCHAR(255) NOT NULL,
                ancienne_valeur TEXT,
                nouvelle_valeur TEXT,
                modifie_par VARCHAR(255) NOT NULL,
                date_modification VARCHAR(255) NOT NULL,
                FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE
            )
        """)
        tables_created.append("historique")
    else:
        tables_verified.append("historique")
    
    # ========== TABLE: sujets ==========
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'sujets'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE sujets (
                id SERIAL PRIMARY KEY,
                nom VARCHAR(255) UNIQUE NOT NULL
            )
        """)
        # Insérer des sujets par défaut
        default_sujets = [
            'Portables',
            'PC Fixe',
            'Imprimantes - impressions',
            'Réseau',
            'Matériel',
            'Logiciel',
            'Téléphonie',
            'Messagerie',
            'Applications métiers',
            'Sécurité',
            'Accès / Droits',
            'Autre'
        ]
        for sujet in default_sujets:
            cursor.execute("INSERT INTO sujets (nom) VALUES (%s)", (sujet,))
        tables_created.append("sujets")
    else:
        tables_verified.append("sujets")
    
    # ========== TABLE: priorites ==========
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'priorites'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE priorites (
                id SERIAL PRIMARY KEY,
                nom VARCHAR(255) UNIQUE NOT NULL,
                couleur VARCHAR(50) NOT NULL,
                niveau INTEGER NOT NULL
            )
        """)
        # Insérer des priorités par défaut
        default_priorites = [
            ('Basse', '#28a745', 1),
            ('Moyenne', '#ffc107', 2),
            ('Haute', '#fd7e14', 3),
            ('Critique', '#dc3545', 4)
        ]
        for nom, couleur, niveau in default_priorites:
            cursor.execute("INSERT INTO priorites (nom, couleur, niveau) VALUES (%s, %s, %s)", 
                         (nom, couleur, niveau))
        tables_created.append("priorites")
    else:
        tables_verified.append("priorites")
    
    # ========== TABLE: sites ==========
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'sites'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE sites (
                id SERIAL PRIMARY KEY,
                nom VARCHAR(255) UNIQUE NOT NULL,
                couleur VARCHAR(50) NOT NULL
            )
        """)
        # Insérer des sites par défaut
        default_sites = [
            ('HD', '#007bff'),
            ('HGRL', '#6f42c1'),
            ('SJ', '#e83e8c'),
            ('Periph', '#17a2b8')
        ]
        for nom, couleur in default_sites:
            cursor.execute("INSERT INTO sites (nom, couleur) VALUES (%s, %s)", (nom, couleur))
        tables_created.append("sites")
    else:
        tables_verified.append("sites")
    
    # ========== TABLE: statuts ==========
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'statuts'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE statuts (
                id SERIAL PRIMARY KEY,
                nom VARCHAR(255) UNIQUE NOT NULL,
                couleur VARCHAR(50) NOT NULL,
                category VARCHAR(50) NOT NULL DEFAULT 'en_cours'
            )
        """)
        # Insérer des statuts par défaut avec catégories
        default_statuts = [
            # EN COURS (bleus/verts clairs)
            ('Affecté', '#007bff', 'en_cours'),
            ('En cours de préparation', '#0dcaf0', 'en_cours'),
            ('En intervention', '#20c997', 'en_cours'),

            # SUSPENDU (oranges)
            ('Suspendu', '#fd7e14', 'suspendu'),
            ('Intervention programmée', '#ffc107', 'suspendu'),

            # TRANSFERE (violets)
            ('Transféré', '#6f42c1', 'transfere'),
            ('En réservation', '#d63384', 'transfere'),

            # TRAITE (verts)
            ('Traité', '#28a745', 'traite'),
            ('Clôturé', '#198754', 'traite')
        ]
        for nom, couleur, category in default_statuts:
            cursor.execute(
                "INSERT INTO statuts (nom, couleur, category) VALUES (%s, %s, %s)",
                (nom, couleur, category)
            )
        tables_created.append("statuts")
    else:
        tables_verified.append("statuts")
        # Migration: s'assurer que la colonne category existe
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='statuts' AND column_name='category'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE statuts ADD COLUMN category VARCHAR(50)")
            cursor.execute("UPDATE statuts SET category='suspendu' WHERE nom='Suspendu'")
            cursor.execute("UPDATE statuts SET category='traite' WHERE nom='Traité'")
            cursor.execute("UPDATE statuts SET category='en_cours' WHERE category IS NULL OR category=''")
    
    # ========== TABLES WIKI V2 ==========
    
    # Table: wiki_categories
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'wiki_categories'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE wiki_categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                icon VARCHAR(50) DEFAULT '📁',
                description TEXT,
                color VARCHAR(50) DEFAULT '#4f46e5',
                position INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(255)
            )
        """)
        tables_created.append("wiki_categories")
    else:
        tables_verified.append("wiki_categories")
    
    # Table: wiki_subcategories
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'wiki_subcategories'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE wiki_subcategories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category_id INTEGER NOT NULL,
                icon VARCHAR(50) DEFAULT '📄',
                description TEXT,
                position INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(255),
                FOREIGN KEY (category_id) REFERENCES wiki_categories(id) ON DELETE CASCADE
            )
        """)
        tables_created.append("wiki_subcategories")
    else:
        tables_verified.append("wiki_subcategories")
    
    # Table: wiki_articles
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'wiki_articles'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE wiki_articles (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT,
                subcategory_id INTEGER,
                icon VARCHAR(50) DEFAULT '📝',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(255) NOT NULL,
                last_modified_by VARCHAR(255),
                views_count INTEGER DEFAULT 0,
                likes_count INTEGER DEFAULT 0,
                dislikes_count INTEGER DEFAULT 0,
                is_featured INTEGER DEFAULT 0,
                tags TEXT,
                FOREIGN KEY (subcategory_id) REFERENCES wiki_subcategories(id) ON DELETE SET NULL
            )
        """)
        tables_created.append("wiki_articles")
    else:
        tables_verified.append("wiki_articles")
    
    # Migration: ajouter colonnes métadonnées à wiki_articles si elles n'existent pas
    metadata_columns = [
        ('status', "VARCHAR(20) DEFAULT 'published'"),
        ('owner', 'VARCHAR(255)'),
        ('summary', 'TEXT'),
        ('last_reviewed_at', 'TIMESTAMP'),
        ('expires_at', 'TIMESTAMP')
    ]
    
    for col_name, col_def in metadata_columns:
        cursor.execute(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='wiki_articles' AND column_name='{col_name}'
        """)
        if not cursor.fetchone():
            try:
                cursor.execute(f"ALTER TABLE wiki_articles ADD COLUMN {col_name} {col_def}")
                print(f"   - Colonne {col_name} ajoutee a wiki_articles")
            except Exception as e:
                print(f"   - Erreur lors de l'ajout de {col_name}: {e}")
    
    # Table: wiki_history
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'wiki_history'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE wiki_history (
                id SERIAL PRIMARY KEY,
                article_id INTEGER NOT NULL,
                title VARCHAR(255),
                content TEXT,
                modified_by VARCHAR(255) NOT NULL,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                change_description TEXT,
                FOREIGN KEY (article_id) REFERENCES wiki_articles(id) ON DELETE CASCADE
            )
        """)
        tables_created.append("wiki_history")
    else:
        tables_verified.append("wiki_history")
    
    # Table: wiki_votes
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'wiki_votes'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE wiki_votes (
                id SERIAL PRIMARY KEY,
                article_id INTEGER NOT NULL,
                user_name VARCHAR(255) NOT NULL,
                vote_type VARCHAR(20) CHECK(vote_type IN ('like', 'dislike')),
                voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(article_id, user_name),
                FOREIGN KEY (article_id) REFERENCES wiki_articles(id) ON DELETE CASCADE
            )
        """)
        tables_created.append("wiki_votes")
    else:
        tables_verified.append("wiki_votes")
    
    # Table: wiki_images
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'wiki_images'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE wiki_images (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255),
                filepath VARCHAR(500) NOT NULL,
                uploaded_by VARCHAR(255) NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                article_id INTEGER,
                file_size INTEGER,
                mime_type VARCHAR(100),
                FOREIGN KEY (article_id) REFERENCES wiki_articles(id) ON DELETE SET NULL
            )
        """)
        tables_created.append("wiki_images")
    else:
        tables_verified.append("wiki_images")
    
    # Table: wiki_tags
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'wiki_tags'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE wiki_tags (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                color VARCHAR(20) DEFAULT '#4f46e5',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        tables_created.append("wiki_tags")
    else:
        tables_verified.append("wiki_tags")
    
    # Table: wiki_article_tags (table de liaison)
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'wiki_article_tags'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE wiki_article_tags (
                article_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (article_id, tag_id),
                FOREIGN KEY (article_id) REFERENCES wiki_articles(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES wiki_tags(id) ON DELETE CASCADE
            )
        """)
        tables_created.append("wiki_article_tags")
        
        # Migration: migrer les tags existants depuis le champ TEXT vers la structure normalisée
        print("   - Migration des tags existants...")
        cursor.execute("SELECT id, tags FROM wiki_articles WHERE tags IS NOT NULL AND tags != ''")
        articles_with_tags = cursor.fetchall()
        
        tag_count = 0
        for article in articles_with_tags:
            tags_str = article['tags'] or ''
            if tags_str:
                # Séparer les tags par virgule
                tag_names = [t.strip() for t in tags_str.split(',') if t.strip()]
                for tag_name in tag_names:
                    # Créer le tag s'il n'existe pas
                    cursor.execute("""
                        INSERT INTO wiki_tags (name) 
                        VALUES (%s)
                        ON CONFLICT (name) DO NOTHING
                    """, (tag_name,))
                    
                    # Récupérer l'ID du tag
                    cursor.execute("SELECT id FROM wiki_tags WHERE name = %s", (tag_name,))
                    tag_row = cursor.fetchone()
                    if tag_row:
                        tag_id = tag_row['id']
                        # Lier l'article au tag
                        cursor.execute("""
                            INSERT INTO wiki_article_tags (article_id, tag_id)
                            VALUES (%s, %s)
                            ON CONFLICT (article_id, tag_id) DO NOTHING
                        """, (article['id'], tag_id))
                        tag_count += 1
        
        if tag_count > 0:
            print(f"   - {tag_count} tag(s) migre(s) depuis les articles existants")
    else:
        tables_verified.append("wiki_article_tags")
    
    # Table: wiki_feedback
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'wiki_feedback'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE wiki_feedback (
                id SERIAL PRIMARY KEY,
                article_id INTEGER NOT NULL,
                user_name VARCHAR(255) NOT NULL,
                feedback_type VARCHAR(20) NOT NULL CHECK(feedback_type IN ('useful', 'not_useful', 'outdated', 'needs_update')),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES wiki_articles(id) ON DELETE CASCADE
            )
        """)
        tables_created.append("wiki_feedback")
    else:
        tables_verified.append("wiki_feedback")
    
    # Table: wiki_search_log
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'wiki_search_log'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE wiki_search_log (
                id SERIAL PRIMARY KEY,
                query VARCHAR(500) NOT NULL,
                user_name VARCHAR(255),
                results_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        tables_created.append("wiki_search_log")
    else:
        tables_verified.append("wiki_search_log")
    
    # Index full-text pour recherche PostgreSQL
    cursor.execute("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'wiki_articles' AND indexname = 'wiki_articles_search_idx'
    """)
    if not cursor.fetchone():
        try:
            cursor.execute("""
                CREATE INDEX wiki_articles_search_idx ON wiki_articles 
                USING GIN (to_tsvector('french', 
                    coalesce(title, '') || ' ' || 
                    coalesce(content, '') || ' ' || 
                    coalesce(tags, '')
                ))
            """)
            print("   - Index full-text GIN cree pour wiki_articles")
        except Exception as e:
            print(f"   - Erreur lors de la creation de l'index full-text: {e}")
    else:
        print("   - Index full-text deja existant")
    
    # Commit toutes les modifications
    conn.commit()
    cursor.close()
    conn.close()
    
    # Afficher le résumé
    print("\n" + "="*60)
    print("RESUME DE LA VERIFICATION DE LA BASE DE DONNEES")
    print("="*60)
    
    if tables_created:
        print(f"\n{len(tables_created)} table(s) creee(s):")
        for table in tables_created:
            print(f"   - {table}")
    
    if tables_verified:
        print(f"\n{len(tables_verified)} table(s) verifiee(s) (deja existantes):")
        for table in tables_verified:
            print(f"   - {table}")
    
    print(f"\nIntegrite de la base: OK")
    print(f"Type: PostgreSQL")
    print("\nLa base de donnees est prete!")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        ensure_database_integrity()
        print("Verification terminee avec succes!")
    except Exception as e:
        print(f"ERREUR lors de la verification: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
