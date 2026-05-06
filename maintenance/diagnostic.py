#!/usr/bin/env python3
"""Diagnostic complet des incidents"""
import psycopg2
import os

conn = psycopg2.connect(
    host='postgres',
    port=5432,
    database='dispatch',
    user=os.environ['POSTGRES_USER'],
    password=os.environ['POSTGRES_PASSWORD']
)
cursor = conn.cursor()

print('='*60)
print('DIAGNOSTIC COMPLET')
print('='*60)

# 1. Tous les incidents
cursor.execute('SELECT COUNT(*) FROM incidents')
print(f'\n1. Total incidents en DB: {cursor.fetchone()[0]}')

cursor.execute('SELECT COUNT(*) FROM incidents WHERE archived=0 AND is_deleted=FALSE')
print(f'   Non archivés/non supprimés: {cursor.fetchone()[0]}')

cursor.execute('SELECT COUNT(*) FROM incidents WHERE archived=1')
print(f'   Archivés: {cursor.fetchone()[0]}')

cursor.execute('SELECT COUNT(*) FROM incidents WHERE is_deleted=TRUE')
print(f'   Supprimés: {cursor.fetchone()[0]}')

# 2. Statuts et catégories
cursor.execute('SELECT nom, category FROM statuts ORDER BY nom')
print(f'\n2. Statuts disponibles:')
for row in cursor.fetchall():
    print(f'   - {row[0]}: {row[1]}')

# 3. Incidents par statut
print(f'\n3. Incidents par statut (non archivés):')
cursor.execute("""
    SELECT i.etat, COUNT(*) 
    FROM incidents i 
    WHERE i.archived=0 AND i.is_deleted=FALSE 
    GROUP BY i.etat
""")
for row in cursor.fetchall():
    print(f'   - {row[0]}: {row[1]}')

# 4. Tous les techniciens
cursor.execute('SELECT id, prenom, username, actif FROM techniciens ORDER BY id')
print(f'\n4. Techniciens:')
for t in cursor.fetchall():
    print(f'   ID {t[0]}: {t[1]} ({t[2]}) - actif={t[3]}')

# 5. Détail de TOUS les incidents non archivés
print(f'\n5. DÉTAIL DES INCIDENTS NON ARCHIVÉS:')
cursor.execute("""
    SELECT i.id, i.numero, i.etat, i.collaborateur, i.technicien_id, i.archived, i.is_deleted
    FROM incidents i
    WHERE i.archived=0 AND i.is_deleted=FALSE
    ORDER BY i.id
""")
incidents = cursor.fetchall()
if incidents:
    for inc in incidents:
        print(f'   ID {inc[0]}: {inc[1]}')
        print(f'      etat={inc[2]}')
        print(f'      collaborateur={repr(inc[3])}')
        print(f'      technicien_id={inc[4]}')
        print(f'      archived={inc[5]}, is_deleted={inc[6]}')
else:
    print('   AUCUN INCIDENT!')

# 6. Simulation requête admin
print(f'\n6. SIMULATION REQUÊTE ADMIN:')
cursor.execute('SELECT id, prenom FROM techniciens WHERE actif=1')
techs = cursor.fetchall()
active_ids = [t[0] for t in techs]
active_names = [t[1] for t in techs]
print(f'   Techniciens actifs: {active_names}')
print(f'   IDs actifs: {active_ids}')

if active_names:
    id_list = ','.join(map(str, active_ids))
    name_list = ','.join(f"'{n}'" for n in active_names)
    query = f"""
        SELECT id, numero, etat, collaborateur, technicien_id
        FROM incidents
        WHERE archived=0 AND is_deleted=FALSE
        AND (collaborateur IN ({name_list})
             OR technicien_id IN ({id_list})
             OR collaborateur IS NULL
             OR collaborateur = ''
             OR collaborateur = 'Non affecté')
        ORDER BY id ASC
    """
    print(f'\n   SQL générée:')
    print(f'   {query}')
    cursor.execute(query)
    result = cursor.fetchall()
    print(f'\n   Résultat: {len(result)} incident(s)')
    for inc in result:
        print(f'      ID {inc[0]}: {inc[1]} - {inc[2]}')
else:
    print('   Aucun technicien actif!')
    cursor.execute("SELECT id, numero, etat FROM incidents WHERE archived=0 AND is_deleted=FALSE")
    result = cursor.fetchall()
    print(f'   Tous les incidents: {len(result)}')

# 7. Vérifier s'il y a des contraintes FK
cursor.execute("""
    SELECT tc.constraint_name, kcu.column_name, ccu.table_name AS foreign_table, ccu.column_name AS foreign_column
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
    WHERE tc.table_name = 'incidents' AND tc.constraint_type = 'FOREIGN KEY'
""")
print(f'\n7. Contraintes Foreign Key sur incidents:')
fks = cursor.fetchall()
if fks:
    for fk in fks:
        print(f'   {fk[0]}: {fk[1]} -> {fk[2]}.{fk[3]}')
else:
    print('   Aucune FK trouvée')

conn.close()
print('\n' + '='*60)
print('FIN DU DIAGNOSTIC')
print('='*60)
