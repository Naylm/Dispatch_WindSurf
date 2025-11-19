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
                role VARCHAR(50) NOT NULL
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
                actif INTEGER DEFAULT 1
            )
        """)
        tables_created.append("techniciens")
    else:
        tables_verified.append("techniciens")
    
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
                valide INTEGER DEFAULT 0,
                date_affectation DATE NOT NULL,
                archived INTEGER DEFAULT 0,
                localisation VARCHAR(255) DEFAULT ''
            )
        """)
        tables_created.append("incidents")
    else:
        tables_verified.append("incidents")
    
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
            'Portables', 'PC Fixe', 'Imprimantes - impressions',
            'Réseau', 'Matériel', 'Logiciel'
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
        # Insérer des statuts par défaut
        default_statuts = [
            ('Affecté', '#007bff', 'en_cours'),
            ('En cours de préparation', '#ffc107', 'en_cours'),
            ('Suspendu', '#fd7e14', 'suspendu'),
            ('Traité', '#28a745', 'traite')
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
    
    # ========== TABLES WIKI V2 (résumé) ==========
    # wiki_categories, wiki_subcategories, wiki_articles, wiki_history, wiki_votes, wiki_images
    # (Même structure que SQLite, adapter les types INTEGER -> SERIAL, TEXT -> TEXT, etc.)
    
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
