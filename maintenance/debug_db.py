#!/usr/bin/env python3
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

print('=== DEBUG: Comptage des incidents ===')

cursor.execute('SELECT id, prenom, actif FROM techniciens ORDER BY id')
techs = cursor.fetchall()
print('Techniciens:')
for t in techs:
    print(f'  ID {t[0]}: {t[1]} - ACTIF={t[2]}')

active_ids = [t[0] for t in techs if t[2]]
active_names = [t[1] for t in techs if t[2]]
print(f'Actifs: IDs={active_ids}, Noms={active_names}')

cursor.execute("SELECT COUNT(*) FROM incidents WHERE archived=0 AND is_deleted=FALSE")
print(f"\nTotal incidents non archivés: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM incidents i JOIN statuts s ON i.etat=s.nom WHERE i.archived=0 AND i.is_deleted=FALSE AND s.category='en_cours'")
en_cours_total = cursor.fetchone()[0]
print(f"En cours (tous): {en_cours_total}")

if active_ids:
    id_list = ','.join(map(str, active_ids))
    name_list = ','.join(f"'{n}'" for n in active_names)
    # ANCIENNE REQUÊTE (bug)
    cursor.execute(f"""
        SELECT COUNT(*) FROM incidents i
        JOIN statuts s ON i.etat=s.nom
        WHERE i.archived=0 AND i.is_deleted=FALSE AND s.category='en_cours'
        AND (i.collaborateur IN ({name_list})
             OR i.technicien_id IN ({id_list})
             OR i.collaborateur IS NULL OR i.collaborateur='')
    """)
    en_cours_old = cursor.fetchone()[0]
    print(f"En cours (ancienne requête): {en_cours_old}")
    
    # NOUVELLE REQUÊTE (fix)
    cursor.execute(f"""
        SELECT COUNT(*) FROM incidents i
        JOIN statuts s ON i.etat=s.nom
        WHERE i.archived=0 AND i.is_deleted=FALSE AND s.category='en_cours'
        AND (i.collaborateur IN ({name_list})
             OR i.technicien_id IN ({id_list})
             OR i.collaborateur IS NULL
             OR i.collaborateur=''
             OR i.collaborateur='Non affecté')
    """)
    en_cours_new = cursor.fetchone()[0]
    print(f"En cours (nouvelle requête): {en_cours_new}")
    print(f"DIFFÉRENCE FIXÉE: {en_cours_total - en_cours_new} (était: {en_cours_total - en_cours_old})")
else:
    print("Aucun technicien actif!")

cursor.execute("""
    SELECT i.id, i.numero, i.etat, i.collaborateur, i.technicien_id
    FROM incidents i
    JOIN statuts s ON i.etat=s.nom
    WHERE i.archived=0 AND i.is_deleted=FALSE AND s.category='en_cours'
""")
print("\nDétail des incidents en_cours:")
for row in cursor.fetchall():
    print(f"  ID {row[0]}: {row[1]} | etat={row[2]} | collab={repr(row[3])} | tech_id={row[4]}")

conn.close()
