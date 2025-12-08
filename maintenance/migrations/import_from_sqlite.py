#!/usr/bin/env python3
"""
Script pour importer les données depuis SQLite vers PostgreSQL
Usage: python import_from_sqlite.py path/to/dispatch.db
"""

import os
import sys
import sqlite3

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from db_config import get_db

def import_from_sqlite(sqlite_path):
    """Importe toutes les données depuis SQLite vers PostgreSQL"""

    if not os.path.exists(sqlite_path):
        print(f"✗ Fichier SQLite introuvable: {sqlite_path}")
        return False

    print("=" * 70)
    print("  Migration SQLite → PostgreSQL")
    print("=" * 70)
    print(f"Source: {sqlite_path}")
    print(f"Destination: PostgreSQL (dispatch)")
    print()

    # Connexion SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    # Connexion PostgreSQL
    pg_db = get_db()

    try:
        # Note: Les contraintes FK resteront actives pour garantir l'intégrité
        # Les données orphelines seront sautées automatiquement

        # Liste des tables à migrer (ordre respectant les dépendances)
        # D'abord les tables sans dépendances, puis celles qui dépendent d'autres
        tables = [
            'users',
            'priorites',
            'sites',
            'statuts',
            'sujets',
            'techniciens',
            'wiki_categories',
            'wiki_subcategories',
            'incidents',          # Doit venir après techniciens, priorites, sites, statuts, sujets
            # 'historique',       # TEMPORAIREMENT DÉSACTIVÉ - Trop de données orphelines
            'wiki_articles',      # Doit venir après wiki_subcategories
            'wiki_history',       # Doit venir après wiki_articles
            'wiki_votes'          # Doit venir après wiki_articles
        ]

        print("⚠  Note: La table 'historique' sera ignorée car elle contient")
        print("   des données orphelines qui ne correspondent plus aux incidents actuels.")

        total_rows = 0

        for table in tables:
            print(f"📊 Migration table: {table}...", end=' ')

            try:
                # Vérifier si la table existe dans SQLite
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
                if sqlite_cursor.fetchone()[0] == 0:
                    print("⊘ (n'existe pas dans SQLite)")
                    continue

                # Compter les lignes
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = sqlite_cursor.fetchone()[0]

                if count == 0:
                    print("⊘ (vide)")
                    continue

                # Récupérer toutes les données
                sqlite_cursor.execute(f"SELECT * FROM {table}")
                rows = sqlite_cursor.fetchall()

                if not rows:
                    print("⊘ (vide)")
                    continue

                # Récupérer les noms de colonnes
                columns = [description[0] for description in sqlite_cursor.description]

                # Vider la table PostgreSQL
                pg_db.execute(f"DELETE FROM {table}")

                # Insérer les données
                inserted = 0
                skipped = 0
                for row in rows:
                    # Pour historique, vérifier que l'incident existe dans PostgreSQL
                    if table == 'historique' and 'incident_id' in columns:
                        incident_id = row[columns.index('incident_id')]
                        check = pg_db.execute(
                            "SELECT COUNT(*) FROM incidents WHERE id = %s", (incident_id,)
                        ).fetchone()
                        if check and check[0] == 0:
                            skipped += 1
                            continue

                    # Pour wiki_articles, vérifier que la subcategory existe
                    if table == 'wiki_articles' and 'subcategory_id' in columns:
                        subcategory_id = row[columns.index('subcategory_id')]
                        if subcategory_id:  # Peut être NULL
                            check = pg_db.execute(
                                "SELECT COUNT(*) FROM wiki_subcategories WHERE id = %s", (subcategory_id,)
                            ).fetchone()
                            if check and check[0] == 0:
                                skipped += 1
                                continue

                    # Pour wiki_history et wiki_votes, vérifier que l'article existe
                    if table in ['wiki_history', 'wiki_votes'] and 'article_id' in columns:
                        article_id = row[columns.index('article_id')]
                        check = pg_db.execute(
                            "SELECT COUNT(*) FROM wiki_articles WHERE id = %s", (article_id,)
                        ).fetchone()
                        if check and check[0] == 0:
                            skipped += 1
                            continue

                    placeholders = ', '.join(['%s'] * len(columns))
                    cols = ', '.join(columns)
                    query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"

                    # Convertir Row en tuple
                    values = tuple(row[col] for col in columns)

                    # Savepoint pour rollback partiel si erreur
                    try:
                        pg_db.execute(f"SAVEPOINT sp_{inserted + skipped}")
                        pg_db.execute(query, values)
                        pg_db.execute(f"RELEASE SAVEPOINT sp_{inserted + skipped}")
                        inserted += 1
                    except Exception as e:
                        pg_db.execute(f"ROLLBACK TO SAVEPOINT sp_{inserted + skipped}")
                        skipped += 1
                        continue

                # Commit après chaque table
                try:
                    pg_db.commit()
                except Exception as e:
                    print(f"\n   ⚠ Erreur commit: {e}")
                    pg_db.rollback()
                    raise
                total_rows += inserted
                if skipped > 0:
                    print(f"✓ {inserted} lignes (⊘ {skipped} ignorées)")
                else:
                    print(f"✓ {inserted} lignes")

            except Exception as e:
                print(f"✗ Erreur: {e}")
                pg_db.rollback()
                continue


        # Réinitialiser les séquences PostgreSQL
        print()
        print("🔄 Réinitialisation des séquences...")

        for table in tables:
            try:
                # Trouver la colonne id
                result = pg_db.execute(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    AND column_name = 'id'
                """).fetchone()

                if result:
                    # Réinitialiser la séquence
                    pg_db.execute(f"""
                        SELECT setval(
                            pg_get_serial_sequence('{table}', 'id'),
                            COALESCE((SELECT MAX(id) FROM {table}), 1),
                            true
                        )
                    """)
                    pg_db.commit()
            except Exception as e:
                print(f"   ⚠ Séquence {table}: {e}")

        print()
        print("=" * 70)
        print(f"✅ Migration terminée avec succès!")
        print(f"   Total: {total_rows} lignes migrées")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n✗ Erreur globale: {e}")
        pg_db.rollback()
        return False

    finally:
        sqlite_conn.close()
        pg_db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_from_sqlite.py <chemin_vers_sqlite.db>")
        print()
        print("Exemple:")
        print("  python import_from_sqlite.py temporaire/dispatch.db")
        sys.exit(1)

    sqlite_path = sys.argv[1]
    success = import_from_sqlite(sqlite_path)

    sys.exit(0 if success else 1)
