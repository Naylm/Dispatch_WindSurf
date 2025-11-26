#!/usr/bin/env python3
"""
Tests automatisés pour valider les améliorations de stabilité.
Teste les transactions, la gestion d'erreurs, les conflits de version, etc.
"""

import sys
import os
import time
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from db_config import get_db
from utils_stability import (
    db_transaction,
    ConflictError,
    check_version_conflict,
    add_historique_entry
)


class StabilityTests:
    """Suite de tests pour la stabilité de l'application."""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.db = None

    def setup(self):
        """Initialisation avant les tests."""
        print("\n🔧 Setup des tests...")
        self.db = get_db()

    def teardown(self):
        """Nettoyage après les tests."""
        print("\n🧹 Nettoyage...")
        if self.db:
            self.db.close()

    def assert_true(self, condition, message):
        """Assertion simple."""
        if condition:
            print(f"   ✅ {message}")
            self.tests_passed += 1
            return True
        else:
            print(f"   ❌ {message}")
            self.tests_failed += 1
            return False

    def test_database_columns(self):
        """Test 1 : Vérifier que les colonnes de versioning existent."""
        print("\n[Test 1] Vérification des colonnes de versioning...")

        try:
            columns = self.db.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='incidents' AND column_name IN ('updated_at', 'version')
            """).fetchall()

            column_names = [col['column_name'] for col in columns]

            self.assert_true(
                'version' in column_names,
                "Colonne 'version' existe dans la table incidents"
            )
            self.assert_true(
                'updated_at' in column_names,
                "Colonne 'updated_at' existe dans la table incidents"
            )

            return True
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            self.tests_failed += 1
            return False

    def test_indexes(self):
        """Test 2 : Vérifier que les index sont créés."""
        print("\n[Test 2] Vérification des index...")

        try:
            indexes = self.db.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'incidents'
                AND indexname LIKE 'idx_%'
            """).fetchall()

            index_names = [idx['indexname'] for idx in indexes]

            expected_indexes = [
                'idx_incidents_collaborateur',
                'idx_incidents_archived',
                'idx_incidents_etat'
            ]

            for expected_idx in expected_indexes:
                self.assert_true(
                    expected_idx in index_names,
                    f"Index '{expected_idx}' existe"
                )

            return True
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            self.tests_failed += 1
            return False

    def test_trigger(self):
        """Test 3 : Vérifier que le trigger fonctionne."""
        print("\n[Test 3] Vérification du trigger de mise à jour...")

        try:
            # Créer un incident de test
            self.db.execute("""
                INSERT INTO incidents (
                    numero, site, sujet, urgence, collaborateur,
                    etat, date_affectation, archived, version
                ) VALUES (
                    'TEST_TRIGGER', 'HD', 'PC Fixe', 'Moyenne', 'Hugo',
                    'Affecté', '2025-01-01', 0, 1
                )
            """)
            self.db.commit()

            # Récupérer l'ID
            incident = self.db.execute("""
                SELECT id, version, updated_at FROM incidents WHERE numero='TEST_TRIGGER'
            """).fetchone()

            initial_version = incident['version']
            initial_updated_at = incident['updated_at']

            # Attendre 1 seconde pour voir la différence de timestamp
            time.sleep(1)

            # Mettre à jour l'incident
            self.db.execute("""
                UPDATE incidents SET etat='Traité' WHERE id=?
            """, (incident['id'],))
            self.db.commit()

            # Vérifier que la version et updated_at ont été mis à jour
            updated_incident = self.db.execute("""
                SELECT version, updated_at FROM incidents WHERE id=?
            """, (incident['id'],)).fetchone()

            version_incremented = updated_incident['version'] == initial_version + 1
            timestamp_updated = updated_incident['updated_at'] != initial_updated_at

            self.assert_true(
                version_incremented,
                f"Version incrémentée automatiquement ({initial_version} → {updated_incident['version']})"
            )
            self.assert_true(
                timestamp_updated,
                "Timestamp 'updated_at' mis à jour automatiquement"
            )

            # Nettoyage
            self.db.execute("DELETE FROM incidents WHERE numero='TEST_TRIGGER'")
            self.db.commit()

            return version_incremented and timestamp_updated
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            self.tests_failed += 1
            # Nettoyage en cas d'erreur
            try:
                self.db.execute("DELETE FROM incidents WHERE numero='TEST_TRIGGER'")
                self.db.commit()
            except:
                pass
            return False

    def test_transaction_rollback(self):
        """Test 4 : Vérifier que les transactions rollback correctement."""
        print("\n[Test 4] Vérification du rollback des transactions...")

        try:
            # Compter les incidents avant
            count_before = self.db.execute("SELECT COUNT(*) as count FROM incidents").fetchone()['count']

            # Essayer une transaction qui échoue
            try:
                with db_transaction() as db:
                    db.execute("""
                        INSERT INTO incidents (
                            numero, site, sujet, urgence, collaborateur,
                            etat, date_affectation, archived
                        ) VALUES (
                            'TEST_ROLLBACK', 'HD', 'PC Fixe', 'Moyenne', 'Hugo',
                            'Affecté', '2025-01-01', 0
                        )
                    """)
                    # Forcer une erreur en insérant une contrainte invalide
                    db.execute("INSERT INTO incidents (id) VALUES (NULL)")  # Devrait échouer

            except Exception:
                pass  # L'erreur est attendue

            # Compter les incidents après
            count_after = self.db.execute("SELECT COUNT(*) as count FROM incidents").fetchone()['count']

            rollback_worked = count_before == count_after

            self.assert_true(
                rollback_worked,
                f"Transaction rollback correctement (count avant: {count_before}, après: {count_after})"
            )

            # Vérifier que l'incident de test n'existe pas
            test_incident = self.db.execute("""
                SELECT * FROM incidents WHERE numero='TEST_ROLLBACK'
            """).fetchone()

            self.assert_true(
                test_incident is None,
                "Incident de test n'existe pas (rollback confirmé)"
            )

            return rollback_worked
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            self.tests_failed += 1
            return False

    def test_transaction_commit(self):
        """Test 5 : Vérifier que les transactions commit correctement."""
        print("\n[Test 5] Vérification du commit des transactions...")

        try:
            # Créer un incident avec transaction
            with db_transaction() as db:
                db.execute("""
                    INSERT INTO incidents (
                        numero, site, sujet, urgence, collaborateur,
                        etat, date_affectation, archived
                    ) VALUES (
                        'TEST_COMMIT', 'HD', 'PC Fixe', 'Moyenne', 'Hugo',
                        'Affecté', '2025-01-01', 0
                    )
                """)

            # Vérifier que l'incident existe
            test_incident = self.db.execute("""
                SELECT * FROM incidents WHERE numero='TEST_COMMIT'
            """).fetchone()

            commit_worked = test_incident is not None

            self.assert_true(
                commit_worked,
                "Transaction commit correctement (incident créé)"
            )

            # Nettoyage
            self.db.execute("DELETE FROM incidents WHERE numero='TEST_COMMIT'")
            self.db.commit()

            return commit_worked
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            self.tests_failed += 1
            # Nettoyage en cas d'erreur
            try:
                self.db.execute("DELETE FROM incidents WHERE numero='TEST_COMMIT'")
                self.db.commit()
            except:
                pass
            return False

    def test_version_conflict_detection(self):
        """Test 6 : Vérifier la détection des conflits de version."""
        print("\n[Test 6] Vérification de la détection des conflits de version...")

        try:
            # Créer un incident de test
            with db_transaction() as db:
                db.execute("""
                    INSERT INTO incidents (
                        numero, site, sujet, urgence, collaborateur,
                        etat, date_affectation, archived, version
                    ) VALUES (
                        'TEST_CONFLICT', 'HD', 'PC Fixe', 'Moyenne', 'Hugo',
                        'Affecté', '2025-01-01', 0, 5
                    )
                """)

            # Récupérer l'ID
            incident = self.db.execute("""
                SELECT id FROM incidents WHERE numero='TEST_CONFLICT'
            """).fetchone()

            incident_id = incident['id']

            # Tester avec une mauvaise version (devrait lever ConflictError)
            conflict_detected = False
            try:
                check_version_conflict(self.db, 'incidents', incident_id, expected_version=3)
            except ConflictError:
                conflict_detected = True

            self.assert_true(
                conflict_detected,
                "Conflit de version détecté correctement (version 3 vs 5)"
            )

            # Tester avec la bonne version (ne devrait pas lever d'erreur)
            no_conflict = False
            try:
                check_version_conflict(self.db, 'incidents', incident_id, expected_version=5)
                no_conflict = True
            except ConflictError:
                pass

            self.assert_true(
                no_conflict,
                "Pas de conflit avec la bonne version (version 5 == 5)"
            )

            # Nettoyage
            self.db.execute("DELETE FROM incidents WHERE numero='TEST_CONFLICT'")
            self.db.commit()

            return conflict_detected and no_conflict
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            self.tests_failed += 1
            # Nettoyage en cas d'erreur
            try:
                self.db.execute("DELETE FROM incidents WHERE numero='TEST_CONFLICT'")
                self.db.commit()
            except:
                pass
            return False

    def test_historique_creation(self):
        """Test 7 : Vérifier la création automatique de l'historique."""
        print("\n[Test 7] Vérification de la création de l'historique...")

        try:
            # Créer un incident de test
            with db_transaction() as db:
                db.execute("""
                    INSERT INTO incidents (
                        numero, site, sujet, urgence, collaborateur,
                        etat, date_affectation, archived
                    ) VALUES (
                        'TEST_HISTORIQUE', 'HD', 'PC Fixe', 'Moyenne', 'Hugo',
                        'Affecté', '2025-01-01', 0
                    )
                """)

            # Récupérer l'ID
            incident = self.db.execute("""
                SELECT id FROM incidents WHERE numero='TEST_HISTORIQUE'
            """).fetchone()

            incident_id = incident['id']

            # Ajouter une entrée dans l'historique
            with db_transaction() as db:
                add_historique_entry(
                    db, incident_id, "etat",
                    "Affecté", "Traité", "TestUser"
                )

            # Vérifier que l'entrée existe
            historique = self.db.execute("""
                SELECT * FROM historique WHERE incident_id=? AND champ='etat'
            """, (incident_id,)).fetchone()

            historique_created = historique is not None

            self.assert_true(
                historique_created,
                "Entrée historique créée correctement"
            )

            if historique_created:
                self.assert_true(
                    historique['ancienne_valeur'] == "Affecté",
                    "Ancienne valeur correcte dans l'historique"
                )
                self.assert_true(
                    historique['nouvelle_valeur'] == "Traité",
                    "Nouvelle valeur correcte dans l'historique"
                )
                self.assert_true(
                    historique['modifie_par'] == "TestUser",
                    "Utilisateur correct dans l'historique"
                )

            # Nettoyage
            self.db.execute("DELETE FROM historique WHERE incident_id=?", (incident_id,))
            self.db.execute("DELETE FROM incidents WHERE numero='TEST_HISTORIQUE'")
            self.db.commit()

            return historique_created
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            self.tests_failed += 1
            # Nettoyage en cas d'erreur
            try:
                self.db.execute("DELETE FROM incidents WHERE numero='TEST_HISTORIQUE'")
                self.db.commit()
            except:
                pass
            return False

    def test_query_performance(self):
        """Test 8 : Vérifier les performances des requêtes avec index."""
        print("\n[Test 8] Vérification des performances des requêtes...")

        try:
            # Requête sans filtre (devrait utiliser l'index sur archived)
            start = time.time()
            self.db.execute("SELECT * FROM incidents WHERE archived=0 LIMIT 100").fetchall()
            elapsed = time.time() - start

            fast_query = elapsed < 0.5  # Moins de 500ms

            self.assert_true(
                fast_query,
                f"Requête sur 'archived' rapide ({elapsed:.3f}s < 0.5s)"
            )

            # Requête sur collaborateur (devrait utiliser l'index)
            start = time.time()
            self.db.execute("SELECT * FROM incidents WHERE collaborateur='Hugo' LIMIT 100").fetchall()
            elapsed = time.time() - start

            fast_collab_query = elapsed < 0.5

            self.assert_true(
                fast_collab_query,
                f"Requête sur 'collaborateur' rapide ({elapsed:.3f}s < 0.5s)"
            )

            return fast_query and fast_collab_query
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            self.tests_failed += 1
            return False

    def run_all_tests(self):
        """Exécute tous les tests."""
        print("\n" + "=" * 70)
        print("🚀 LANCEMENT DES TESTS DE STABILITÉ")
        print("=" * 70)

        self.setup()

        # Liste des tests à exécuter
        tests = [
            self.test_database_columns,
            self.test_indexes,
            self.test_trigger,
            self.test_transaction_rollback,
            self.test_transaction_commit,
            self.test_version_conflict_detection,
            self.test_historique_creation,
            self.test_query_performance
        ]

        # Exécuter chaque test
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"\n❌ Erreur inattendue dans {test.__name__}: {e}")
                self.tests_failed += 1

        self.teardown()

        # Résumé
        print("\n" + "=" * 70)
        print("📊 RÉSUMÉ DES TESTS")
        print("=" * 70)
        print(f"✅ Tests réussis: {self.tests_passed}")
        print(f"❌ Tests échoués: {self.tests_failed}")
        print(f"📈 Taux de réussite: {(self.tests_passed / (self.tests_passed + self.tests_failed) * 100):.1f}%")
        print("=" * 70)

        return self.tests_failed == 0


if __name__ == "__main__":
    tester = StabilityTests()
    success = tester.run_all_tests()

    if success:
        print("\n✅ Tous les tests sont passés avec succès!")
        sys.exit(0)
    else:
        print("\n❌ Certains tests ont échoué. Consultez les logs ci-dessus.")
        sys.exit(1)
