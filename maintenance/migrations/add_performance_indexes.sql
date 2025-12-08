-- =====================================================
-- Migration: Ajout d'index pour améliorer les performances
-- Date: 2025-12-07
-- Description: Index critiques pour optimiser les requêtes fréquentes
-- =====================================================

-- Note: Les index existants ne seront pas recréés grâce à IF NOT EXISTS

-- =====================================================
-- INDEX SUR LA TABLE INCIDENTS
-- =====================================================

-- Index sur numero (recherches fréquentes par numéro de ticket)
CREATE INDEX IF NOT EXISTS idx_incidents_numero ON incidents(numero);

-- Index sur urgence (filtres par priorité)
CREATE INDEX IF NOT EXISTS idx_incidents_urgence ON incidents(urgence);

-- Index sur site (filtres par site)
CREATE INDEX IF NOT EXISTS idx_incidents_site ON incidents(site);

-- Index sur sujet (filtres par sujet)
CREATE INDEX IF NOT EXISTS idx_incidents_sujet ON incidents(sujet);

-- Index sur created_at (tris par date de création)
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at DESC);

-- Index composite pour la requête principale de la page d'accueil
-- Couvre: WHERE archived=0 ORDER BY id ASC
CREATE INDEX IF NOT EXISTS idx_incidents_archived_id ON incidents(archived, id);

-- Index composite pour les vues technicien
-- Couvre: WHERE collaborateur=X AND archived=0 ORDER BY id ASC
CREATE INDEX IF NOT EXISTS idx_incidents_collab_archived_id ON incidents(collaborateur, archived, id);

-- Index composite pour les statistiques
-- Couvre: JOIN avec statuts WHERE archived=0
CREATE INDEX IF NOT EXISTS idx_incidents_archived_etat ON incidents(archived, etat);

-- Index pour les filtres par date d'affectation
CREATE INDEX IF NOT EXISTS idx_incidents_date_affectation ON incidents(date_affectation DESC);

-- =====================================================
-- INDEX SUR LA TABLE WIKI_ARTICLES
-- =====================================================

-- Index sur subcategory_id (navigation par catégorie)
CREATE INDEX IF NOT EXISTS idx_wiki_articles_subcategory ON wiki_articles(subcategory_id);

-- Index sur created_by (recherches par auteur)
CREATE INDEX IF NOT EXISTS idx_wiki_articles_author ON wiki_articles(created_by);

-- Index sur created_at (tri par date)
CREATE INDEX IF NOT EXISTS idx_wiki_articles_created ON wiki_articles(created_at DESC);

-- Index sur updated_at (tri par dernière modification)
CREATE INDEX IF NOT EXISTS idx_wiki_articles_updated ON wiki_articles(updated_at DESC);

-- Index fulltext pour la recherche dans le titre et le contenu
-- Note: Utilise le support fulltext de PostgreSQL
CREATE INDEX IF NOT EXISTS idx_wiki_articles_search_title ON wiki_articles USING gin(to_tsvector('french', title));
CREATE INDEX IF NOT EXISTS idx_wiki_articles_search_content ON wiki_articles USING gin(to_tsvector('french', content));

-- =====================================================
-- INDEX SUR LA TABLE WIKI_CATEGORIES
-- =====================================================

-- Index sur parent_id (navigation hiérarchique)
CREATE INDEX IF NOT EXISTS idx_wiki_categories_parent ON wiki_categories(parent_id);

-- Index sur position (tri)
CREATE INDEX IF NOT EXISTS idx_wiki_categories_position ON wiki_categories(position);

-- =====================================================
-- INDEX SUR LA TABLE WIKI_SUBCATEGORIES
-- =====================================================

-- Index sur category_id (navigation)
CREATE INDEX IF NOT EXISTS idx_wiki_subcategories_category ON wiki_subcategories(category_id);

-- Index sur position (tri)
CREATE INDEX IF NOT EXISTS idx_wiki_subcategories_position ON wiki_subcategories(position);

-- =====================================================
-- INDEX SUR LA TABLE WIKI_VOTES
-- =====================================================

-- Index composite pour éviter les votes multiples
-- Couvre: WHERE article_id=X AND user_id=Y
CREATE UNIQUE INDEX IF NOT EXISTS idx_wiki_votes_article_user ON wiki_votes(article_id, user_id);

-- =====================================================
-- INDEX SUR LA TABLE HISTORIQUE
-- =====================================================

-- Index sur incident_id (consultation historique d'un incident)
CREATE INDEX IF NOT EXISTS idx_historique_incident ON historique(incident_id);

-- Index sur created_at (tri chronologique)
CREATE INDEX IF NOT EXISTS idx_historique_created ON historique(created_at DESC);

-- Index composite pour recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_historique_incident_date ON historique(incident_id, created_at DESC);

-- =====================================================
-- INDEX SUR LA TABLE TECHNICIENS
-- =====================================================

-- Index sur actif (filtres techniciens actifs)
CREATE INDEX IF NOT EXISTS idx_techniciens_actif ON techniciens(actif);

-- Index sur prenom (recherches par nom)
CREATE INDEX IF NOT EXISTS idx_techniciens_prenom ON techniciens(prenom);

-- =====================================================
-- ANALYSE ET OPTIMISATION
-- =====================================================

-- Analyser les tables pour mettre à jour les statistiques du planificateur
ANALYZE incidents;
ANALYZE wiki_articles;
ANALYZE wiki_categories;
ANALYZE wiki_subcategories;
ANALYZE wiki_votes;
ANALYZE historique;
ANALYZE techniciens;
ANALYZE statuts;
ANALYZE priorites;
ANALYZE sites;
ANALYZE sujets;

-- =====================================================
-- VERIFICATION DES INDEX
-- =====================================================

-- Afficher tous les index créés sur la table incidents
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('incidents', 'wiki_articles', 'techniciens', 'historique')
ORDER BY tablename, indexname;
