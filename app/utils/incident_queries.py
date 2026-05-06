"""
Utilitaires pour construire les requêtes SQL des incidents
avec filtrage correct par techniciens actifs
"""

def get_incidents_query_for_admin(active_tech_names, active_tech_ids):
    """
    Construit la requête SQL pour récupérer les incidents visibles par un admin.
    Inclut les incidents assignés via collaborateur OU technicien_id.
    """
    if not active_tech_names:
        return "SELECT * FROM incidents WHERE archived=0 AND is_deleted=FALSE ORDER BY id ASC", ()
    
    name_placeholders = ','.join(['%s'] * len(active_tech_names))
    id_placeholders = ','.join(['%s'] * len(active_tech_ids))
    
    query = f"""
        SELECT * FROM incidents
        WHERE archived=0 AND is_deleted=FALSE
        AND (collaborateur IN ({name_placeholders})
             OR technicien_id IN ({id_placeholders})
             OR collaborateur IS NULL
             OR collaborateur = ''
             OR collaborateur = 'Non affecté')
        ORDER BY id ASC
    """
    params = tuple(active_tech_names + active_tech_ids)
    return query, params


def get_stats_query_for_admin(active_tech_names, active_tech_ids):
    """
    Construit la requête SQL pour récupérer les statistiques des incidents visibles par un admin.
    Inclut les incidents assignés via collaborateur OU technicien_id.
    """
    if not active_tech_names:
        return """
            SELECT s.category, COUNT(*) as count
            FROM incidents i
            JOIN statuts s ON i.etat = s.nom
            WHERE i.archived=0 AND i.is_deleted=FALSE
            GROUP BY s.category
        """, ()
    
    name_placeholders = ','.join(['%s'] * len(active_tech_names))
    id_placeholders = ','.join(['%s'] * len(active_tech_ids))
    
    query = f"""
        SELECT s.category, COUNT(*) as count
        FROM incidents i
        JOIN statuts s ON i.etat = s.nom
        WHERE i.archived=0 AND i.is_deleted=FALSE
        AND (i.collaborateur IN ({name_placeholders})
             OR i.technicien_id IN ({id_placeholders})
             OR i.collaborateur IS NULL
             OR i.collaborateur = ''
             OR i.collaborateur = 'Non affecté')
        GROUP BY s.category
    """
    params = tuple(active_tech_names + active_tech_ids)
    return query, params
