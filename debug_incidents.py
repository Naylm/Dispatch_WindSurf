#!/usr/bin/env python3
"""
Script de debug pour trouver les incidents "fantômes"
(incidents comptés mais pas affichés)
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def get_db():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'dispatch'),
        user=os.getenv('DB_USER', 'dispatch'),
        password=os.getenv('DB_PASSWORD', 'dispatch')
    )
    return conn

def debug_incidents():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 80)
    print("DEBUG: Recherche des incidents 'fantômes'")
    print("=" * 80)
    
    # 1. Lister tous les techniciens actifs
    cursor.execute("SELECT id, prenom, username, actif FROM techniciens ORDER BY id")
    techs = cursor.fetchall()
    print("\n1. TOUS LES TECHNICIENS:")
    for t in techs:
        status = "ACTIF" if t['actif'] else "INACTIF"
        print(f"   ID {t['id']:3d}: {t['prenom']:15s} ({t['username']}) - {status}")
    
    active_tech_ids = [t['id'] for t in techs if t['actif']]
    active_tech_names = [t['prenom'] for t in techs if t['actif']]
    
    print(f"\n   Techniciens actifs: {active_tech_ids}")
    print(f"   Noms actifs: {active_tech_names}")
    
    # 2. Lister tous les incidents non archivés/non supprimés
    cursor.execute("""
        SELECT i.id, i.numero, i.etat, i.collaborateur, i.technicien_id, i.archived, i.is_deleted
        FROM incidents i
        WHERE i.archived = 0 AND i.is_deleted = FALSE
        ORDER BY i.id
    """)
    all_incidents = cursor.fetchall()
    
    print(f"\n2. TOUS LES INCIDENTS NON ARCHIVÉS ({len(all_incidents)} total):")
    print(f"   {'ID':>5} | {'Numero':>10} | {'Etat':>20} | {'Collaborateur':>15} | {'Tech ID':>8}")
    print("   " + "-" * 75)
    for inc in all_incidents:
        print(f"   {inc['id']:>5} | {inc['numero']:>10} | {inc['etat']:>20} | {str(inc['collaborateur']):>15} | {str(inc['technicien_id']):>8}")
    
    # 3. Incidents avec statut 'en_cours'
    cursor.execute("""
        SELECT i.id, i.numero, i.etat, i.collaborateur, i.technicien_id
        FROM incidents i
        JOIN statuts s ON i.etat = s.nom
        WHERE i.archived = 0 AND i.is_deleted = FALSE
        AND s.category = 'en_cours'
        ORDER BY i.id
    """)
    en_cours_incidents = cursor.fetchall()
    
    print(f"\n3. INCIDENTS 'EN COURS' ({len(en_cours_incidents)} total):")
    print(f"   {'ID':>5} | {'Numero':>10} | {'Etat':>20} | {'Collaborateur':>15} | {'Tech ID':>8}")
    print("   " + "-" * 75)
    for inc in en_cours_incidents:
        tech_id = inc['technicien_id']
        collaborateur = inc['collaborateur']
        
        # Déterminer si visible
        visible = False
        if tech_id in active_tech_ids:
            visible = True
        if collaborateur in active_tech_names:
            visible = True
        if not collaborateur and not tech_id:
            visible = True
            
        status = "VISIBLE" if visible else "INVISIBLE !"
        print(f"   {inc['id']:>5} | {inc['numero']:>10} | {inc['etat']:>20} | {str(collaborateur):>15} | {str(tech_id):>8} | {status}")
    
    # 4. Incidents qui seraient affichés (selon notre requête)
    if active_tech_names:
        placeholders_names = ','.join(['%s'] * len(active_tech_names))
        placeholders_ids = ','.join(['%s'] * len(active_tech_ids))
        query = f"""
            SELECT i.id, i.numero, i.etat, i.collaborateur, i.technicien_id
            FROM incidents i
            JOIN statuts s ON i.etat = s.nom
            WHERE i.archived=0 AND i.is_deleted=FALSE
            AND s.category = 'en_cours'
            AND (i.collaborateur IN ({placeholders_names})
                 OR i.technicien_id IN ({placeholders_ids})
                 OR i.collaborateur IS NULL OR i.collaborateur = '')
            ORDER BY i.id
        """
        params = tuple(active_tech_names + active_tech_ids)
        cursor.execute(query, params)
    else:
        cursor.execute("""
            SELECT i.id, i.numero, i.etat, i.collaborateur, i.technicien_id
            FROM incidents i
            JOIN statuts s ON i.etat = s.nom
            WHERE i.archived=0 AND i.is_deleted=FALSE
            AND s.category = 'en_cours'
            ORDER BY i.id
        """)
    
    visible_en_cours = cursor.fetchall()
    
    print(f"\n4. INCIDENTS 'EN COURS' VISIBLES ({len(visible_en_cours)}):")
    for inc in visible_en_cours:
        print(f"   ID {inc['id']}: {inc['numero']} - {inc['etat']}")
    
    # 5. Les incidents "fantômes" (en_cours mais pas visibles)
    print(f"\n5. INCIDENTS 'FANTÔMES' (en_cours mais pas visibles):")
    ghost_found = False
    for inc in en_cours_incidents:
        if inc['id'] not in [v['id'] for v in visible_en_cours]:
            ghost_found = True
            print(f"   ID {inc['id']}: {inc['numero']} - {inc['etat']}")
            print(f"      -> collaborateur: '{inc['collaborateur']}'")
            print(f"      -> technicien_id: {inc['technicien_id']}")
            
            # Vérifier si le technicien existe et est actif
            if inc['technicien_id']:
                cursor.execute("SELECT prenom, actif FROM techniciens WHERE id=%s", (inc['technicien_id'],))
                tech = cursor.fetchone()
                if tech:
                    status = "ACTIF" if tech['actif'] else "INACTIF"
                    print(f"      -> Technicien ID {inc['technicien_id']}: {tech['prenom']} ({status})")
                else:
                    print(f"      -> Technicien ID {inc['technicien_id']}: N'EXISTE PAS!")
    
    if not ghost_found:
        print("   Aucun incident fantôme trouvé.")
    
    print("\n" + "=" * 80)
    print(f"COMPTEUR: {len(en_cours_incidents)} en_cours total")
    print(f"AFFICHÉS:  {len(visible_en_cours)} en_cours visibles")
    print(f"DIFFÉRENCE: {len(en_cours_incidents) - len(visible_en_cours)}")
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    debug_incidents()
