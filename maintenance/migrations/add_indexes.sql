-- Script pour ajouter des indexes de performance à la base de données
-- Date: 2025-11-24
-- Description: Améliore les performances des requêtes fréquentes

-- Index sur la colonne collaborateur (utilisée dans WHERE très fréquemment)
CREATE INDEX IF NOT EXISTS idx_incidents_collaborateur ON incidents(collaborateur);

-- Index sur la colonne archived (filtrée sur chaque requête)
CREATE INDEX IF NOT EXISTS idx_incidents_archived ON incidents(archived);

-- Index sur la colonne etat (utilisée dans les statistiques et filtres)
CREATE INDEX IF NOT EXISTS idx_incidents_etat ON incidents(etat);

-- Index sur date_affectation (utilisée pour le tri)
CREATE INDEX IF NOT EXISTS idx_incidents_date_affectation ON incidents(date_affectation);

-- Index composé pour la requête la plus fréquente (collaborateur + archived)
CREATE INDEX IF NOT EXISTS idx_incidents_collab_archived ON incidents(collaborateur, archived);

-- Index sur prenom des techniciens (utilisé pour l'authentification)
CREATE INDEX IF NOT EXISTS idx_techniciens_prenom ON techniciens(prenom);

-- Index sur username des users (utilisé pour l'authentification)
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Afficher les indexes créés
SELECT 'Indexes créés avec succès!' as message;
