"""
Script de démarrage amélioré avec backup automatique
Ce script crée un backup avant chaque démarrage de l'application
"""
import os
import sys
from datetime import datetime

def main():
    print("="*70)
    print("  DEMARRAGE DE DISPATCHMANAGER V1.2")
    print("="*70)
    print()
    
    # 1. Vérifier l'intégrité de la base de données
    print("Etape 1/3 : Verification de l'integrite de la base de donnees...")
    try:
        from ensure_db_integrity import ensure_database_integrity
        ensure_database_integrity()
    except Exception as e:
        print(f"ERREUR lors de la verification: {e}")
        print("L'application va quand meme demarrer...")
    
    print()
    
    # 2. Créer un backup automatique
    print("Etape 2/3 : Creation d'un backup automatique...")
    try:
        from backup_database import create_backup
        if os.path.exists("dispatch.db"):
            create_backup()
        else:
            print("Aucune base de donnees a sauvegarder (premiere execution)")
    except Exception as e:
        print(f"Impossible de creer le backup: {e}")
        print("   L'application va quand meme demarrer...")
    
    print()
    
    # 3. Démarrer l'application
    print("Etape 3/3 : Demarrage de l'application Flask...")
    print("="*70)
    print()
    
    # Importer et démarrer l'application
    try:
        from app import socketio, app
        print("OK - Application prete!")
        print("Acces: http://localhost:5000")
        print("Toutes vos donnees sont securisees et persistantes!")
        print()
        print("Appuyez sur CTRL+C pour arreter le serveur")
        print("="*70)
        print()
        
        socketio.run(app, host="0.0.0.0", port=5000, debug=True)
        
    except KeyboardInterrupt:
        print("\n")
        print("="*70)
        print("Arret de l'application...")
        print("Toutes les donnees ont ete sauvegardees automatiquement")
        print("="*70)
        sys.exit(0)
    except Exception as e:
        print(f"\nERREUR lors du demarrage: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
