#!/usr/bin/env python3
"""
Script pour appliquer les index de performance sur la base de données PostgreSQL
Usage: python apply_performance_indexes.py
"""

import os
import sys

# Ajouter le répertoire parent au path pour importer db_config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from db_config import get_db

def apply_indexes():
    """Applique tous les index de performance"""

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file = os.path.join(script_dir, 'add_performance_indexes.sql')

    if not os.path.exists(sql_file):
        print(f"✗ Fichier SQL introuvable: {sql_file}")
        return False

    print("📊 Application des index de performance...")
    print(f"   Fichier: {sql_file}")

    # Lire le fichier SQL
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Séparer les commandes SQL (ignorer les commentaires)
    commands = []
    current_command = []

    for line in sql_content.split('\n'):
        # Ignorer les lignes de commentaires
        if line.strip().startswith('--') or not line.strip():
            continue

        current_command.append(line)

        # Une commande se termine par un point-virgule
        if line.strip().endswith(';'):
            commands.append('\n'.join(current_command))
            current_command = []

    # Connexion à la base de données
    db = get_db()

    try:
        success_count = 0
        error_count = 0

        for i, command in enumerate(commands, 1):
            command = command.strip()
            if not command:
                continue

            try:
                # Extraire le nom de l'index pour affichage
                if 'CREATE' in command and 'INDEX' in command:
                    parts = command.split()
                    idx_name = None
                    for j, part in enumerate(parts):
                        if part.upper() == 'INDEX' and j + 1 < len(parts):
                            # Skip IF NOT EXISTS
                            offset = 2 if parts[j+1].upper() == 'IF' else 1
                            if j + offset < len(parts):
                                idx_name = parts[j + offset]
                                break

                    if idx_name:
                        print(f"   [{i}/{len(commands)}] Création index: {idx_name}...", end=' ')
                    else:
                        print(f"   [{i}/{len(commands)}] Exécution commande...", end=' ')
                elif 'ANALYZE' in command:
                    table_name = command.split()[1].rstrip(';')
                    print(f"   [{i}/{len(commands)}] Analyse table: {table_name}...", end=' ')
                else:
                    print(f"   [{i}/{len(commands)}] Exécution...", end=' ')

                db.execute(command)
                db.commit()
                print("✓")
                success_count += 1

            except Exception as e:
                print(f"✗")
                print(f"      Erreur: {e}")
                error_count += 1
                # Continuer même en cas d'erreur (index peut déjà exister)

        print(f"\n✅ Migration terminée:")
        print(f"   - Succès: {success_count}")
        print(f"   - Erreurs: {error_count} (normal si index déjà existants)")

        # Afficher les statistiques des index créés
        print(f"\n📈 Statistiques des index:")
        result = db.execute("""
            SELECT
                schemaname,
                tablename,
                COUNT(*) as index_count
            FROM pg_indexes
            WHERE tablename IN ('incidents', 'wiki_articles', 'techniciens', 'historique', 'wiki_categories', 'wiki_subcategories', 'wiki_votes')
            GROUP BY schemaname, tablename
            ORDER BY tablename
        """).fetchall()

        for row in result:
            print(f"   - {row['tablename']}: {row['index_count']} index")

        return True

    except Exception as e:
        print(f"\n✗ Erreur lors de l'application des index: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  Migration: Index de Performance")
    print("=" * 60)
    print()

    success = apply_indexes()

    print()
    print("=" * 60)

    sys.exit(0 if success else 1)
