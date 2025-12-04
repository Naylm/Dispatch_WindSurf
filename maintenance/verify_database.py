#!/usr/bin/env python3
"""
Script de vérification complète du schéma PostgreSQL
Vérifie que toutes les tables et colonnes requises existent
"""

import sys
from db_config import get_db

# Définition complète du schéma attendu
EXPECTED_SCHEMA = {
    'users': [
        'id', 'username', 'password', 'role', 'force_password_reset'
    ],
    'techniciens': [
        'id', 'prenom', 'password', 'role', 'actif', 'force_password_reset'
    ],
    'incidents': [
        'id', 'numero', 'site', 'sujet', 'urgence', 'collaborateur',
        'etat', 'notes', 'note_dispatch', 'valide', 'date_affectation',
        'archived', 'localisation'
    ],
    'historique': [
        'id', 'incident_id', 'champ', 'ancienne_valeur', 'nouvelle_valeur',
        'modifie_par', 'date_modification'
    ],
    'sujets': [
        'id', 'nom'
    ],
    'priorites': [
        'id', 'nom', 'couleur', 'niveau'
    ],
    'sites': [
        'id', 'nom', 'couleur'
    ],
    'statuts': [
        'id', 'nom', 'couleur', 'category'
    ],
    'wiki_categories': [
        'id', 'name', 'icon', 'description', 'color', 'position',
        'created_at', 'created_by'
    ],
    'wiki_subcategories': [
        'id', 'name', 'category_id', 'icon', 'description', 'position',
        'created_at', 'created_by'
    ],
    'wiki_articles': [
        'id', 'title', 'content', 'subcategory_id', 'icon', 'created_at',
        'updated_at', 'created_by', 'last_modified_by', 'views_count',
        'likes_count', 'dislikes_count', 'is_featured', 'tags'
    ],
    'wiki_history': [
        'id', 'article_id', 'title', 'content', 'modified_by',
        'modified_at', 'change_description'
    ],
    'wiki_votes': [
        'id', 'article_id', 'user_name', 'vote_type', 'voted_at'
    ],
    'wiki_images': [
        'id', 'filename', 'original_filename', 'filepath', 'uploaded_by',
        'uploaded_at', 'article_id', 'file_size', 'mime_type'
    ]
}

def verify_schema():
    """Vérifie que toutes les tables et colonnes existent"""
    
    print("\n" + "="*70)
    print("VÉRIFICATION DU SCHÉMA POSTGRESQL - DISPATCH MANAGER")
    print("="*70 + "\n")
    
    db = get_db()
    cursor = db.cursor()
    
    all_ok = True
    missing_tables = []
    missing_columns = {}
    extra_columns = {}
    
    # Vérifier chaque table
    for table_name, expected_columns in EXPECTED_SCHEMA.items():
        print(f"📋 Vérification de la table '{table_name}'...")
        
        # Vérifier si la table existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (table_name,))
        
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print(f"   ❌ Table '{table_name}' MANQUANTE")
            missing_tables.append(table_name)
            all_ok = False
            continue
        
        # Récupérer les colonnes existantes
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        
        actual_columns = [row[0] for row in cursor.fetchall()]
        
        # Vérifier les colonnes manquantes
        missing_cols = set(expected_columns) - set(actual_columns)
        if missing_cols:
            print(f"   ⚠️  Colonnes manquantes: {', '.join(sorted(missing_cols))}")
            missing_columns[table_name] = list(missing_cols)
            all_ok = False
        
        # Colonnes supplémentaires (pas forcément un problème)
        extra_cols = set(actual_columns) - set(expected_columns)
        if extra_cols:
            print(f"   ℹ️  Colonnes supplémentaires: {', '.join(sorted(extra_cols))}")
            extra_columns[table_name] = list(extra_cols)
        
        if not missing_cols and not extra_cols:
            print(f"   ✅ Table '{table_name}' OK ({len(actual_columns)} colonnes)")
        elif not missing_cols:
            print(f"   ✅ Table '{table_name}' OK (toutes les colonnes requises présentes)")
    
    cursor.close()
    db.close()
    
    # Résumé
    print("\n" + "="*70)
    print("RÉSUMÉ DE LA VÉRIFICATION")
    print("="*70 + "\n")
    
    if all_ok:
        print("✅ LE SCHÉMA EST COMPLET ET VALIDE !")
        print(f"\n   - {len(EXPECTED_SCHEMA)} tables vérifiées")
        print(f"   - Toutes les colonnes requises sont présentes")
        return True
    else:
        print("❌ DES PROBLÈMES ONT ÉTÉ DÉTECTÉS :\n")
        
        if missing_tables:
            print(f"📋 Tables manquantes ({len(missing_tables)}):")
            for table in missing_tables:
                print(f"   - {table}")
            print()
        
        if missing_columns:
            print(f"⚠️  Colonnes manquantes dans {len(missing_columns)} table(s):")
            for table, cols in missing_columns.items():
                print(f"   - {table}: {', '.join(sorted(cols))}")
            print()
        
        print("💡 Solution:")
        print("   1. Assurez-vous que le conteneur PostgreSQL est démarré")
        print("   2. L'application corrigera automatiquement le schéma au démarrage")
        print("   3. Ou exécutez manuellement: python ensure_db_integrity.py")
        
        return False

if __name__ == "__main__":
    try:
        success = verify_schema()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERREUR lors de la vérification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
