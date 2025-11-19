"""
Script de sauvegarde automatique de la base de données
Ce script crée des backups réguliers de la base de données pour éviter toute perte de données
"""
import sqlite3
import shutil
import os
from datetime import datetime
import zipfile

DB_PATH = "dispatch.db"
BACKUP_DIR = "backups"
MAX_BACKUPS = 10  # Nombre maximum de backups à conserver

def create_backup():
    """Crée une sauvegarde de la base de données"""
    
    if not os.path.exists(DB_PATH):
        print("Aucune base de donnees a sauvegarder")
        return False
    
    # Créer le dossier de backup s'il n'existe pas
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"Dossier de backup cree: {BACKUP_DIR}")
    
    # Générer le nom du fichier de backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"dispatch_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        # Méthode 1: Backup via SQLite (meilleure pratique)
        print(f"Creation du backup: {backup_filename}")
        
        source = sqlite3.connect(DB_PATH)
        dest = sqlite3.connect(backup_path)
        
        with dest:
            source.backup(dest)
        
        source.close()
        dest.close()
        
        # Compresser le backup pour gagner de l'espace
        zip_path = backup_path + ".zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(backup_path, os.path.basename(backup_path))
        
        # Supprimer le fichier non compressé
        os.remove(backup_path)
        
        file_size = os.path.getsize(zip_path) / 1024
        print(f"Backup cree avec succes: {zip_path} ({file_size:.2f} KB)")
        
        # Nettoyer les vieux backups
        cleanup_old_backups()
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de la creation du backup: {e}")
        return False

def cleanup_old_backups():
    """Supprime les anciens backups pour ne garder que les plus récents"""
    
    if not os.path.exists(BACKUP_DIR):
        return
    
    # Lister tous les fichiers de backup
    backups = []
    for filename in os.listdir(BACKUP_DIR):
        if filename.startswith("dispatch_backup_") and filename.endswith(".zip"):
            filepath = os.path.join(BACKUP_DIR, filename)
            backups.append((filepath, os.path.getmtime(filepath)))
    
    # Trier par date (plus récent en premier)
    backups.sort(key=lambda x: x[1], reverse=True)
    
    # Supprimer les backups excédentaires
    if len(backups) > MAX_BACKUPS:
        print(f"Nettoyage des anciens backups (max: {MAX_BACKUPS})")
        for filepath, _ in backups[MAX_BACKUPS:]:
            try:
                os.remove(filepath)
                print(f"   Supprime: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"   Impossible de supprimer {filepath}: {e}")

def restore_backup(backup_file):
    """Restaure une sauvegarde de la base de données"""
    
    backup_path = os.path.join(BACKUP_DIR, backup_file)
    
    if not os.path.exists(backup_path):
        print(f"Fichier de backup introuvable: {backup_path}")
        return False
    
    try:
        # Créer un backup de la base actuelle avant restauration
        if os.path.exists(DB_PATH):
            safety_backup = f"dispatch_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(DB_PATH, safety_backup)
            print(f"Backup de securite cree: {safety_backup}")
        
        # Décompresser le backup
        temp_db = "temp_restore.db"
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            zipf.extractall(BACKUP_DIR)
            # Trouver le fichier .db dans le zip
            for name in zipf.namelist():
                if name.endswith('.db'):
                    extracted_path = os.path.join(BACKUP_DIR, name)
                    shutil.move(extracted_path, temp_db)
                    break
        
        # Remplacer la base actuelle
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        
        shutil.move(temp_db, DB_PATH)
        
        print(f"Base de donnees restauree depuis: {backup_file}")
        return True
        
    except Exception as e:
        print(f"Erreur lors de la restauration: {e}")
        return False

def list_backups():
    """Liste tous les backups disponibles"""
    
    if not os.path.exists(BACKUP_DIR):
        print("Aucun backup disponible")
        return []
    
    backups = []
    for filename in os.listdir(BACKUP_DIR):
        if filename.startswith("dispatch_backup_") and filename.endswith(".zip"):
            filepath = os.path.join(BACKUP_DIR, filename)
            size = os.path.getsize(filepath) / 1024
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            backups.append({
                'filename': filename,
                'size_kb': size,
                'date': mtime
            })
    
    # Trier par date (plus récent en premier)
    backups.sort(key=lambda x: x['date'], reverse=True)
    
    if backups:
        print(f"\n{len(backups)} backup(s) disponible(s):")
        print("="*70)
        for i, backup in enumerate(backups, 1):
            print(f"{i}. {backup['filename']}")
            print(f"   Date: {backup['date'].strftime('%d/%m/%Y %H:%M:%S')}")
            print(f"   Taille: {backup['size_kb']:.2f} KB")
            print("-"*70)
    else:
        print("Aucun backup disponible")
    
    return backups

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            create_backup()
        elif command == "list":
            list_backups()
        elif command == "restore" and len(sys.argv) > 2:
            restore_backup(sys.argv[2])
        else:
            print("Usage:")
            print("  python backup_database.py create        - Créer un backup")
            print("  python backup_database.py list          - Lister les backups")
            print("  python backup_database.py restore <file> - Restaurer un backup")
    else:
        # Par défaut, créer un backup
        create_backup()
