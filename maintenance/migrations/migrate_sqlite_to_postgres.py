"""
Script de migration SQLite → PostgreSQL
Copie toutes les données de dispatch.db vers PostgreSQL
"""
import sqlite3
import psycopg2
import psycopg2.extras
import os
from datetime import datetime

# Configuration PostgreSQL
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "dispatch")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "dispatch_user")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "dispatch_pass")

# Chemin SQLite - Chercher d'abord dans /app/data, puis dans le dossier du script
SQLITE_DB_DATA = "/app/data/dispatch.db"
SQLITE_DB_SCRIPT = os.path.join(os.path.dirname(__file__), "dispatch.db")
SQLITE_DB = SQLITE_DB_DATA if os.path.exists(SQLITE_DB_DATA) else SQLITE_DB_SCRIPT

def migrate():
    """Migre toutes les données de SQLite vers PostgreSQL"""
    
    print("="*60)
    print("MIGRATION SQLite → PostgreSQL")
    print("="*60)
    
    if not os.path.exists(SQLITE_DB):
        print(f"❌ Fichier SQLite introuvable: {SQLITE_DB}")
        return False
    
    # Connexion SQLite
    print(f"\n📂 Connexion à SQLite: {SQLITE_DB}")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    # Connexion PostgreSQL avec autocommit
    print(f"🐘 Connexion à PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    try:
        pg_conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        pg_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        pg_cur = pg_conn.cursor()
    except Exception as e:
        print(f"❌ Erreur connexion PostgreSQL: {e}")
        print("💡 Assurez-vous que le conteneur PostgreSQL est démarré:")
        print("   docker compose up -d postgres")
        return False
    
    # Tables à migrer (dans l'ordre des dépendances)
    tables = [
        'users',
        'techniciens',
        'sujets',
        'priorites',
        'sites',
        'statuts',
        'incidents',
        'historique',
        'wiki_categories',
        'wiki_subcategories',
        'wiki_articles',
        'wiki_history',
        'wiki_votes',
        'wiki_images'
    ]
    
    migrated_counts = {}
    
    # Récupérer les IDs d'incidents existants pour filtrer l'historique
    existing_incident_ids = set()

    for table in tables:
        print(f"\n📊 Migration de la table '{table}'...")

        # Vérifier si la table existe dans SQLite
        sqlite_cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not sqlite_cur.fetchone():
            print(f"   ⚠️  Table '{table}' introuvable dans SQLite, ignorée")
            continue

        # Récupérer toutes les données
        sqlite_cur.execute(f"SELECT * FROM {table}")
        rows = sqlite_cur.fetchall()

        if not rows:
            print(f"   ✓ Table '{table}' vide, rien à migrer")
            migrated_counts[table] = 0
            continue

        # Récupérer les noms de colonnes
        columns = [description[0] for description in sqlite_cur.description]

        # Si on migre les incidents, enregistrer les IDs
        if table == 'incidents':
            id_idx = columns.index('id')
            existing_incident_ids = {row[id_idx] for row in rows}
            print(f"   📝 {len(existing_incident_ids)} IDs d'incidents enregistrés: {sorted(list(existing_incident_ids))[:10]}...")

        # Préparer la requête d'insertion PostgreSQL
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns)
        insert_query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"

        # Debug pour historique
        if table == 'historique':
            print(f"   📋 Filtrage basé sur {len(existing_incident_ids)} IDs valides")

        # Insérer les données ligne par ligne (autocommit activé)
        count = 0
        errors = 0
        skipped = 0
        for i, row in enumerate(rows):
            # Filtrer les entrées d'historique avec incident_id invalide
            if table == 'historique' and 'incident_id' in columns:
                incident_id_idx = columns.index('incident_id')
                if row[incident_id_idx] not in existing_incident_ids:
                    skipped += 1
                    if skipped <= 3:
                        print(f"   ⏭️  Skip ligne {i+1}: incident_id={row[incident_id_idx]} invalide")
                    continue

            try:
                pg_cur.execute(insert_query, tuple(row))
                count += 1
            except Exception as e:
                errors += 1
                if errors <= 3:  # Afficher seulement les 3 premières erreurs
                    error_msg = str(e).split('\n')[0]  # Première ligne seulement
                    print(f"   ⚠️  Erreur ligne {i+1}: {error_msg[:100]}")
                elif errors == 4:
                    print(f"   ⚠️  ... (+{len(rows) - i - 1} autres erreurs potentielles)")

        migrated_counts[table] = count
        if skipped > 0:
            print(f"   ⏭️  {skipped} ligne(s) ignorée(s) (références invalides)")
        if errors > 0:
            print(f"   ✓ {count} ligne(s) migrée(s) ({errors} erreur(s))")
        else:
            print(f"   ✓ {count} ligne(s) migrée(s)")
    
    # Réinitialiser les séquences PostgreSQL
    print("\n🔄 Réinitialisation des séquences...")
    for table in tables:
        try:
            pg_cur.execute(f"""
                SELECT setval(pg_get_serial_sequence('{table}', 'id'),
                       COALESCE((SELECT MAX(id) FROM {table}), 1),
                       true)
            """)
        except Exception as e:
            # Certaines tables n'ont pas de colonne id
            pass
    
    # Fermeture des connexions
    sqlite_cur.close()
    sqlite_conn.close()
    pg_cur.close()
    pg_conn.close()
    
    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ DE LA MIGRATION")
    print("="*60)
    total = sum(migrated_counts.values())
    print(f"\n✅ Total: {total} lignes migrées")
    for table, count in migrated_counts.items():
        print(f"   - {table}: {count}")
    
    print("\n🎉 Migration terminée avec succès!")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        success = migrate()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
