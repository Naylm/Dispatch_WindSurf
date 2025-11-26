#!/usr/bin/env python3
"""
Script pour appliquer les index et optimisations SQL pour améliorer les performances.
Ajoute également les colonnes nécessaires pour la gestion des versions (optimistic locking).
"""

import sys
import os

# Ajouter le répertoire parent au path pour importer db_config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from db_config import get_db


def apply_stability_indexes():
    """Applique tous les index et optimisations pour la stabilité."""

    print("=" * 70)
    print("APPLICATION DES INDEX ET OPTIMISATIONS SQL")
    print("=" * 70)

    db = get_db()

    try:
        # ==================== AJOUT DES COLONNES DE VERSIONING ====================
        print("\n[1/4] Ajout des colonnes de versioning...")

        try:
            # Vérifier si les colonnes existent déjà
            result = db.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='incidents' AND column_name IN ('updated_at', 'version')
            """).fetchall()

            existing_columns = [row['column_name'] for row in result]

            if 'updated_at' not in existing_columns:
                db.execute("""
                    ALTER TABLE incidents
                    ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                """)
                print("   ✅ Colonne 'updated_at' ajoutée")
            else:
                print("   ℹ️  Colonne 'updated_at' existe déjà")

            if 'version' not in existing_columns:
                db.execute("""
                    ALTER TABLE incidents
                    ADD COLUMN version INTEGER DEFAULT 1
                """)
                print("   ✅ Colonne 'version' ajoutée")
            else:
                print("   ℹ️  Colonne 'version' existe déjà")

            db.commit()
        except Exception as e:
            print(f"   ⚠️  Erreur lors de l'ajout des colonnes: {e}")

        # ==================== CRÉATION DU TRIGGER ====================
        print("\n[2/4] Création du trigger de mise à jour automatique...")

        try:
            # Supprimer l'ancien trigger s'il existe
            db.execute("DROP TRIGGER IF EXISTS incidents_update_trigger ON incidents")

            # Supprimer l'ancienne fonction s'elle existe
            db.execute("DROP FUNCTION IF EXISTS update_incidents_timestamp()")

            # Créer la fonction trigger
            db.execute("""
                CREATE OR REPLACE FUNCTION update_incidents_timestamp()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    NEW.version = OLD.version + 1;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

            # Créer le trigger
            db.execute("""
                CREATE TRIGGER incidents_update_trigger
                BEFORE UPDATE ON incidents
                FOR EACH ROW
                EXECUTE FUNCTION update_incidents_timestamp();
            """)

            db.commit()
            print("   ✅ Trigger 'incidents_update_trigger' créé")
        except Exception as e:
            print(f"   ⚠️  Erreur lors de la création du trigger: {e}")

        # ==================== CRÉATION DES INDEX ====================
        print("\n[3/4] Création des index pour optimiser les performances...")

        indexes = [
            # Index simples sur colonnes fréquemment interrogées
            ("idx_incidents_collaborateur", "incidents", "collaborateur"),
            ("idx_incidents_archived", "incidents", "archived"),
            ("idx_incidents_etat", "incidents", "etat"),
            ("idx_incidents_date_affectation", "incidents", "date_affectation"),
            ("idx_incidents_site", "incidents", "site"),
            ("idx_incidents_sujet", "incidents", "sujet"),
            ("idx_incidents_urgence", "incidents", "urgence"),
            ("idx_historique_incident_id", "historique", "incident_id"),

            # Index composites pour requêtes complexes
            ("idx_incidents_collab_archived", "incidents", "collaborateur, archived"),
            ("idx_incidents_archived_etat", "incidents", "archived, etat"),
            ("idx_incidents_site_archived", "incidents", "site, archived"),
        ]

        created_count = 0
        existing_count = 0

        for index_name, table_name, columns in indexes:
            try:
                # Vérifier si l'index existe déjà
                check_query = """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes
                        WHERE indexname = %s
                    ) as index_exists
                """
                result = db.execute(check_query, (index_name,)).fetchone()

                if result and result['index_exists']:
                    print(f"   ℹ️  Index '{index_name}' existe déjà")
                    existing_count += 1
                else:
                    # Créer l'index
                    create_query = f"""
                        CREATE INDEX IF NOT EXISTS {index_name}
                        ON {table_name}({columns})
                    """
                    db.execute(create_query)
                    db.commit()
                    print(f"   ✅ Index '{index_name}' créé sur {table_name}({columns})")
                    created_count += 1
            except Exception as e:
                print(f"   ⚠️  Erreur lors de la création de l'index '{index_name}': {e}")

        print(f"\n   📊 Résumé: {created_count} index créés, {existing_count} déjà existants")

        # ==================== ANALYSE DES TABLES ====================
        print("\n[4/4] Analyse des tables pour optimiser les statistiques...")

        tables_to_analyze = ['incidents', 'historique', 'techniciens', 'statuts', 'priorites', 'sites', 'sujets']

        for table in tables_to_analyze:
            try:
                db.execute(f"ANALYZE {table}")
                print(f"   ✅ Table '{table}' analysée")
            except Exception as e:
                print(f"   ⚠️  Erreur lors de l'analyse de '{table}': {e}")

        db.commit()

        # ==================== VÉRIFICATION FINALE ====================
        print("\n" + "=" * 70)
        print("VÉRIFICATION FINALE")
        print("=" * 70)

        # Compter les index sur la table incidents
        index_count = db.execute("""
            SELECT COUNT(*) as count
            FROM pg_indexes
            WHERE tablename = 'incidents'
        """).fetchone()

        print(f"\n✅ Total d'index sur 'incidents': {index_count['count']}")

        # Afficher les statistiques de la table
        incident_count = db.execute("SELECT COUNT(*) as count FROM incidents").fetchone()
        print(f"✅ Nombre total d'incidents: {incident_count['count']}")

        # Afficher les colonnes de la table incidents
        columns = db.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'incidents'
            ORDER BY ordinal_position
        """).fetchall()

        print(f"\n📋 Colonnes de la table 'incidents':")
        for col in columns:
            print(f"   - {col['column_name']} ({col['data_type']})")

        print("\n" + "=" * 70)
        print("✅ OPTIMISATIONS APPLIQUÉES AVEC SUCCÈS!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Erreur critique: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

    return True


if __name__ == "__main__":
    print("\n🚀 Démarrage de l'application des optimisations SQL...\n")

    success = apply_stability_indexes()

    if success:
        print("\n✅ Script terminé avec succès!")
        sys.exit(0)
    else:
        print("\n❌ Le script a rencontré des erreurs.")
        sys.exit(1)
