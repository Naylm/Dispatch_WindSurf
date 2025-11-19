"""
Script pour vider toutes les catégories du Wiki
ATTENTION : Ce script supprime TOUTES les catégories, sous-catégories et articles du Wiki !
Utilisez-le uniquement si vous voulez repartir à zéro.
"""
import sqlite3
import os

DB_PATH = "dispatch.db"

def clear_wiki_categories():
    """Supprime toutes les catégories, sous-catégories et articles du Wiki"""
    
    if not os.path.exists(DB_PATH):
        print("❌ Base de données introuvable")
        return False
    
    print("⚠️  ATTENTION : Ce script va supprimer TOUTES les données du Wiki !")
    print("   - Toutes les catégories")
    print("   - Toutes les sous-catégories")
    print("   - Tous les articles")
    print("   - Tous les votes (likes/dislikes)")
    print("   - Tout l'historique des articles")
    print()
    
    # Demander confirmation
    confirmation = input("Êtes-vous sûr de vouloir continuer ? (tapez OUI en majuscules) : ")
    
    if confirmation != "OUI":
        print("❌ Opération annulée")
        return False
    
    print()
    print("🗑️  Suppression en cours...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Supprimer dans l'ordre pour respecter les contraintes de clés étrangères
        cursor.execute("DELETE FROM wiki_votes")
        votes_deleted = cursor.rowcount
        
        cursor.execute("DELETE FROM wiki_history")
        history_deleted = cursor.rowcount
        
        cursor.execute("DELETE FROM wiki_articles")
        articles_deleted = cursor.rowcount
        
        cursor.execute("DELETE FROM wiki_subcategories")
        subcats_deleted = cursor.rowcount
        
        cursor.execute("DELETE FROM wiki_categories")
        cats_deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print("✅ Suppression terminée avec succès !")
        print()
        print(f"   📊 Statistiques :")
        print(f"   • {cats_deleted} catégorie(s) supprimée(s)")
        print(f"   • {subcats_deleted} sous-catégorie(s) supprimée(s)")
        print(f"   • {articles_deleted} article(s) supprimé(s)")
        print(f"   • {history_deleted} entrée(s) d'historique supprimée(s)")
        print(f"   • {votes_deleted} vote(s) supprimé(s)")
        print()
        print("📚 Le Wiki est maintenant vide et prêt pour vos propres catégories !")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la suppression : {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*70)
    print("  🗑️  SUPPRESSION DES CATÉGORIES DU WIKI")
    print("="*70)
    print()
    
    clear_wiki_categories()
    
    print()
    print("="*70)
