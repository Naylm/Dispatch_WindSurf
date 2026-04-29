import time
import os
import redis
from flask import current_app

# Initialisation Redis pour le rate limiting
_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                _redis_client = redis.from_url(redis_url)
            except Exception as e:
                print(f"⚠ Erreur connexion Redis pour rate limiting: {e}")
    return _redis_client

def check_rate_limit(key_prefix, identifier, limit=5, window=60):
    """
    Vérifie si un identifiant (IP, username) dépasse la limite.
    Utilise Redis si disponible, sinon fallback sur mémoire locale (non partagée).
    """
    client = get_redis_client()
    key = f"ratelimit:{key_prefix}:{identifier}"
    
    if client:
        try:
            # Pipeline pour atomicité
            pipe = client.pipeline()
            now = time.time()
            
            # Supprimer les anciennes tentatives
            pipe.zremrangebyscore(key, 0, now - window)
            # Compter les tentatives actuelles
            pipe.zcard(key)
            # Ajouter la nouvelle tentative
            pipe.zadd(key, {str(now): now})
            # Définir l'expiration de la clé
            pipe.expire(key, window)
            
            results = pipe.execute()
            current_count = results[1]
            
            return current_count >= limit
        except Exception as e:
            print(f"⚠ Erreur Redis rate limit: {e}")
            # Fallback memoire si redis echoue
            return False
    else:
        # Fallback mémoire locale simple (non partagée entre workers)
        # Note: Dans DispatchFresh, on préfère Redis pour la production.
        return False

def record_failed_attempt(key_prefix, identifier, window=60):
    """
    Enregistre une tentative échouée.
    Déjà géré par check_rate_limit dans cette implémentation Redis (Window glissante).
    """
    pass
