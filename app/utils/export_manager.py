"""
Gestionnaire d'exports asynchrones pour PDF et Excel
Permet de générer les exports en arrière-plan sans bloquer les autres utilisateurs
"""
import threading
import uuid
import time
import os
from datetime import datetime
from typing import Dict, Optional, Callable, Any


class ExportJob:
    """Représente une tâche d'export en cours"""
    def __init__(self, job_id: str, export_type: str, filename: str):
        self.job_id = job_id
        self.export_type = export_type  # 'pdf' ou 'excel'
        self.filename = filename
        self.status = 'pending'  # pending, processing, completed, failed
        self.progress = 0
        self.created_at = datetime.now()
        self.completed_at = None
        self.file_data = None  # Données binaires du fichier généré
        self.error_message = None
        self.thread = None

    def to_dict(self):
        """Convertit le job en dictionnaire pour JSON"""
        return {
            'job_id': self.job_id,
            'export_type': self.export_type,
            'filename': self.filename,
            'status': self.status,
            'progress': self.progress,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message
        }


class ExportManager:
    """
    Gestionnaire global des tâches d'export
    Thread-safe pour utilisation avec multiple workers Gunicorn
    """
    def __init__(self, cleanup_after_seconds=3600):
        self._jobs: Dict[str, ExportJob] = {}
        self._lock = threading.Lock()
        self._cleanup_after = cleanup_after_seconds

        # Démarrer le thread de nettoyage
        self._cleanup_thread = threading.Thread(target=self._cleanup_old_jobs, daemon=True)
        self._cleanup_thread.start()

    def create_job(self, export_type: str, filename: str) -> str:
        """
        Crée un nouveau job d'export
        Retourne l'ID du job
        """
        job_id = str(uuid.uuid4())
        job = ExportJob(job_id, export_type, filename)

        with self._lock:
            self._jobs[job_id] = job

        return job_id

    def start_job(
        self,
        job_id: str,
        export_function: Callable,
        *args,
        **kwargs
    ) -> bool:
        """
        Démarre l'exécution d'un job dans un thread séparé

        Args:
            job_id: ID du job à démarrer
            export_function: Fonction à exécuter (doit retourner bytes du fichier)
            *args, **kwargs: Arguments pour la fonction

        Returns:
            True si démarré avec succès, False sinon
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job.status != 'pending':
                return False

            job.status = 'processing'

        # Wrapper pour capturer le résultat et les erreurs
        def job_wrapper():
            try:
                # Exécuter la fonction d'export
                file_data = export_function(*args, **kwargs)

                with self._lock:
                    job.file_data = file_data
                    job.status = 'completed'
                    job.progress = 100
                    job.completed_at = datetime.now()

            except Exception as e:
                with self._lock:
                    job.status = 'failed'
                    job.error_message = str(e)
                    job.completed_at = datetime.now()
                print(f"✗ Export job {job_id} failed: {e}")

        # Démarrer le thread
        job.thread = threading.Thread(target=job_wrapper, daemon=True)
        job.thread.start()

        return True

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Récupère le statut d'un job
        Retourne None si le job n'existe pas
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return job.to_dict()

    def get_job_file(self, job_id: str) -> Optional[bytes]:
        """
        Récupère les données du fichier généré
        Retourne None si pas encore généré ou job inexistant
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status != 'completed':
                return None
            return job.file_data

    def delete_job(self, job_id: str) -> bool:
        """
        Supprime un job terminé
        Retourne True si supprimé, False sinon
        """
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
            return False

    def _cleanup_old_jobs(self):
        """
        Thread de nettoyage automatique des vieux jobs
        S'exécute en boucle toutes les 5 minutes
        """
        while True:
            time.sleep(300)  # 5 minutes

            now = datetime.now()
            jobs_to_delete = []

            with self._lock:
                for job_id, job in self._jobs.items():
                    if job.completed_at:
                        age = (now - job.completed_at).total_seconds()
                        if age > self._cleanup_after:
                            jobs_to_delete.append(job_id)

            # Supprimer les vieux jobs
            for job_id in jobs_to_delete:
                self.delete_job(job_id)
                print(f"✓ Cleaned up old export job {job_id}")

    def get_all_jobs(self) -> list:
        """Retourne la liste de tous les jobs (pour debug/admin)"""
        with self._lock:
            return [job.to_dict() for job in self._jobs.values()]


# Instance globale unique du gestionnaire d'exports
# Partagée entre tous les workers via le système de fichiers si nécessaire
export_manager = ExportManager(cleanup_after_seconds=3600)  # 1 heure de rétention
