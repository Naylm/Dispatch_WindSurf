#!/usr/bin/env python3
"""Script pour vérifier et ajouter les colonnes manquantes"""

from db_config import get_db

db = get_db()
cursor = db.cursor()

# Vérifier les colonnes incidents
cursor.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name='incidents'
    ORDER BY column_name
""")
cols = [r['column_name'] for r in cursor.fetchall()]
print('Colonnes incidents:', cols)

# Vérifier si les colonnes de relances/rdv existent
needed_cols = ['relance_mail', 'relance_1', 'relance_2', 'relance_cloture', 'date_rdv']
missing = [c for c in needed_cols if c not in cols]
print('Colonnes manquantes incidents:', missing)

# Ajouter les colonnes manquantes
for col in ['relance_mail', 'relance_1', 'relance_2', 'relance_cloture']:
    if col not in cols:
        print(f'Ajout colonne {col}...')
        cursor.execute(f"ALTER TABLE incidents ADD COLUMN {col} BOOLEAN DEFAULT FALSE")
        print(f'  OK: {col} ajoutée')

if 'date_rdv' not in cols:
    print('Ajout colonne date_rdv...')
    cursor.execute("ALTER TABLE incidents ADD COLUMN date_rdv TIMESTAMP")
    print('  OK: date_rdv ajoutée')

# Vérifier les colonnes statuts
cursor.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name='statuts'
    ORDER BY column_name
""")
cols2 = [r['column_name'] for r in cursor.fetchall()]
print('Colonnes statuts:', cols2)

# Ajouter has_relances et has_rdv si manquantes
if 'has_relances' not in cols2:
    print('Ajout colonne has_relances...')
    cursor.execute("ALTER TABLE statuts ADD COLUMN has_relances BOOLEAN DEFAULT FALSE")
    print('  OK: has_relances ajoutée')

if 'has_rdv' not in cols2:
    print('Ajout colonne has_rdv...')
    cursor.execute("ALTER TABLE statuts ADD COLUMN has_rdv BOOLEAN DEFAULT FALSE")
    print('  OK: has_rdv ajoutée')

db.commit()
print('\n✅ Vérification terminée!')

