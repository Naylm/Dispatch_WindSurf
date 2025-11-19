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

# Chemin SQLite
SQLITE_DB = os.path.join(os.path.dirname(__file__), "dispatch.db")

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
    
    # Connexion PostgreSQL
    print(f"🐘 Connexion à PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    try:
        pg_conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
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
        
        # Préparer la requête d'insertion PostgreSQL
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns)
        insert_query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
        
        # Insérer les données
        count = 0
        for row in rows:
            try:
                pg_cur.execute(insert_query, tuple(row))
                count += 1
            except Exception as e:
                print(f"   ⚠️  Erreur ligne {count+1}: {e}")
                # Continuer malgré les erreurs (ex: doublons)
        
        pg_conn.commit()
        migrated_counts[table] = count
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
    
    pg_conn.commit()
    
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
