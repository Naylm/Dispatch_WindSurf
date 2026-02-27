"""
Configuration de la base de données - Support PostgreSQL avec wrapper compatible SQLite
Inclut connection pooling pour améliorer les performances multi-utilisateurs
"""
import os
import psycopg2
import psycopg2.extras
import psycopg2.extensions
import psycopg2.pool
from contextlib import contextmanager
import atexit

# Configuration PostgreSQL depuis variables d'environnement
DB_TYPE = os.environ.get("DB_TYPE", "postgresql")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "dispatch")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")

if DB_TYPE == "postgresql" and (not POSTGRES_USER or not POSTGRES_PASSWORD):
    raise RuntimeError(
        "POSTGRES_USER et POSTGRES_PASSWORD doivent etre definis pour DB_TYPE=postgresql."
    )

# Configuration du pool de connexions
# Min connections: 5 (toujours disponibles)
# Max connections: 20 (limite pour éviter saturation PostgreSQL)
POOL_MIN_CONN = int(os.environ.get("DB_POOL_MIN", "5"))
POOL_MAX_CONN = int(os.environ.get("DB_POOL_MAX", "20"))

# Pool de connexions global (thread-safe)
_connection_pool = None


class DualAccessRow:
    """
    Classe qui permet d'accéder aux données à la fois par index [0] et par clé ['column']
    Compatible avec SQLite row_factory et PostgreSQL
    """
    def __init__(self, cursor, row):
        self._data = row
        self._columns = [desc[0] for desc in cursor.description] if cursor.description else []
    
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._data[key]
        elif isinstance(key, str):
            try:
                idx = self._columns.index(key)
                return self._data[idx]
            except ValueError:
                raise KeyError(f"Column '{key}' not found")
        else:
            raise TypeError("Key must be int or str")
    
    def __iter__(self):
        return iter(self._data)
    
    def __len__(self):
        return len(self._data)
    
    def keys(self):
        return self._columns

    def values(self):
        return self._data

    def items(self):
        return zip(self._columns, self._data)

    def get(self, key, default=None):
        """Méthode get() compatible avec les dictionnaires"""
        try:
            return self[key]
        except (KeyError, IndexError):
            return default

    def __repr__(self):
        return f"DualAccessRow({dict(self.items())})"


class DualAccessCursor:
    """
    Wrapper de cursor PostgreSQL qui retourne des DualAccessRow
    """
    def __init__(self, cursor):
        self._cursor = cursor
    
    def execute(self, query, params=None):
        """Exécute une requête avec conversion automatique ? -> %s pour PostgreSQL"""
        if params:
            # Convertir les placeholders ? en %s pour PostgreSQL
            if '?' in query:
                query = query.replace('?', '%s')
            self._cursor.execute(query, params)
        else:
            self._cursor.execute(query)
        return self
    
    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return DualAccessRow(self._cursor, row)
    
    def fetchall(self):
        rows = self._cursor.fetchall()
        return [DualAccessRow(self._cursor, row) for row in rows]
    
    def fetchmany(self, size=None):
        rows = self._cursor.fetchmany(size) if size else self._cursor.fetchmany()
        return [DualAccessRow(self._cursor, row) for row in rows]
    
    def close(self):
        self._cursor.close()
    
    @property
    def description(self):
        return self._cursor.description
    
    @property
    def rowcount(self):
        return self._cursor.rowcount


class PostgresConnection:
    """
    Wrapper de connexion PostgreSQL qui émule l'interface SQLite
    pour minimiser les changements dans le code existant

    Gère automatiquement la restitution de la connexion au pool
    """
    def __init__(self, conn, pool=None):
        self.conn = conn
        self._cursor = None
        self._pool = pool  # Référence au pool pour restitution
        self._closed = False

    def cursor(self):
        """Retourne un nouveau cursor PostgreSQL wrappé pour DualAccessRow"""
        if self._closed:
            raise psycopg2.InterfaceError("Connection already closed")
        return DualAccessCursor(self.conn.cursor())

    def execute(self, query, params=None):
        """
        Exécute une requête et retourne un cursor-like object
        Convertit automatiquement ? en %s pour PostgreSQL
        """
        if self._closed:
            raise psycopg2.InterfaceError("Connection already closed")

        # Convertir ? en %s pour PostgreSQL
        pg_query = query.replace('?', '%s')

        if self._cursor:
            self._cursor.close()

        self._cursor = self.conn.cursor()

        if params:
            self._cursor.execute(pg_query, params)
        else:
            self._cursor.execute(pg_query)

        # Wrapper le cursor pour supporter DualAccessRow
        return DualAccessCursor(self._cursor)

    def commit(self):
        """Commit la transaction"""
        if self._closed:
            raise psycopg2.InterfaceError("Connection already closed")
        self.conn.commit()

    def rollback(self):
        """Rollback la transaction"""
        if self._closed:
            return  # Silently ignore rollback on closed connection
        try:
            self.conn.rollback()
        except psycopg2.InterfaceError:
            pass  # Connexion déjà fermée

    def close(self):
        """
        Ferme la connexion et la restitue au pool
        Si pas de pool (mode legacy), ferme réellement la connexion
        """
        if self._closed:
            return  # Déjà fermée, ne rien faire

        # Fermer le cursor interne si existant
        if self._cursor:
            try:
                self._cursor.close()
            except:
                pass
            self._cursor = None

        # Restituer la connexion au pool ou fermer réellement
        if self._pool is not None:
            try:
                # Restituer au pool au lieu de fermer
                self._pool.putconn(self.conn)
            except psycopg2.pool.PoolError as e:
                # Si erreur de restitution, fermer réellement
                print(f"⚠ Erreur restitution connexion au pool: {e}")
                try:
                    self.conn.close()
                except:
                    pass
        else:
            # Pas de pool, fermer réellement (mode legacy)
            try:
                self.conn.close()
            except:
                pass

        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        self.close()
        return False  # Ne pas supprimer l'exception


def _init_connection_pool():
    """
    Initialise le pool de connexions PostgreSQL de manière thread-safe
    Appelé automatiquement lors de la première utilisation
    """
    global _connection_pool

    if _connection_pool is None:
        try:
            _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                POOL_MIN_CONN,
                POOL_MAX_CONN,
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                connect_timeout=10
            )
            print(f"✓ Connection pool initialisé: {POOL_MIN_CONN}-{POOL_MAX_CONN} connexions")
        except psycopg2.Error as e:
            print(f"✗ Erreur initialisation pool de connexions: {e}")
            raise

    return _connection_pool


def _close_connection_pool():
    """
    Ferme proprement le pool de connexions
    Appelé automatiquement à l'arrêt de l'application
    """
    global _connection_pool

    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None
        print("✓ Connection pool fermé proprement")


# Enregistrer la fermeture du pool à l'arrêt de l'application
atexit.register(_close_connection_pool)


from flask import g

def get_db():
    """
    Récupère une connexion depuis le pool PostgreSQL avec wrapper compatible SQLite.
    Optimisé pour utiliser flask.g pendant le cycle de vie d'une requête, évitant
    tout épuisement du pool de connexions (Auto-close à l'instar d'une context manager).
    """
    try:
        from flask import current_app, has_app_context
        can_use_g = has_app_context()
    except Exception:
        can_use_g = False

    if can_use_g:
        if '_database' not in g:
            pool = _init_connection_pool()
            try:
                conn = pool.getconn()
                if conn is None:
                    raise Exception("Pool de connexions épuisé - toutes les connexions sont utilisées")
                g._database = PostgresConnection(conn, pool)
            except psycopg2.pool.PoolError as e:
                print(f"✗ Erreur récupération connexion depuis pool (g): {e}")
                raise
        return g._database
    else:
        # Fallback pour scripts background ou usage orphelin hors contexte
        pool = _init_connection_pool()
        try:
            conn = pool.getconn()
            if conn is None:
                raise Exception("Pool de connexions épuisé - fallback")
            return PostgresConnection(conn, pool)
        except psycopg2.pool.PoolError as e:
            print(f"✗ Erreur récupération connexion depuis pool (fallback): {e}")
            raise

def close_db_connection(e=None):
    """
    Teardown context function pour fermer la connexion stockée dans g.
    À utiliser avec app.teardown_appcontext
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager pour gérer automatiquement la fermeture de la connexion DB

    Usage:
        with get_db_context() as db:
            result = db.execute("SELECT * FROM table").fetchall()
            db.commit()
        # Connexion fermée automatiquement

    En cas d'exception, rollback automatique
    """
    db = get_db()
    try:
        yield db
        # Si pas d'exception, on pourrait commit ici si nécessaire
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
