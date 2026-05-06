#!/usr/bin/env python3
import psycopg2
conn = psycopg2.connect(host='postgres', dbname='dispatch', user='dispatch_user', password='dispatch_pass123')
cur = conn.cursor()
cur.execute("SELECT id, numero, collaborateur, technicien_id, etat FROM incidents WHERE archived=0 AND is_deleted=FALSE")
print("=== INCIDENTS ===")
for row in cur.fetchall():
    print(f"ID {row[0]}: {row[1]} | collab='{row[2]}' | tech_id={row[3]} | etat={row[4]}")

cur.execute("SELECT id, prenom, actif FROM techniciens ORDER BY id")
print("\n=== TECHNICIENS ===")
for row in cur.fetchall():
    print(f"ID {row[0]}: prenom='{row[1]}' | actif={row[2]}")
conn.close()
print("\n=== ANALYSE ===")
print("Incident 2 a collaborateur='Test2' → doit matcher tech prenom='Test2'")
print("Incident 1 a collaborateur='Non affecté' → doit être dans colonne 'Non affecté'")
