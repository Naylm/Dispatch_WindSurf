"""
Configuration de la base de données - Support PostgreSQL avec wrapper compatible SQLite
"""
import os
import psycopg2
import psycopg2.extras
import psycopg2.extensions
from contextlib import contextmanager

# Configuration PostgreSQL depuis variables d'environnement
DB_TYPE = os.environ.get("DB_TYPE", "postgresql")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "dispatch")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "dispatch_user")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "dispatch_pass")


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
    """
    def __init__(self, conn):
        self.conn = conn
        self._cursor = None
    
    def cursor(self):
        """Retourne un nouveau cursor PostgreSQL wrappé pour DualAccessRow"""
        return DualAccessCursor(self.conn.cursor())
    
    def execute(self, query, params=None):
        """
        Exécute une requête et retourne un cursor-like object
        Convertit automatiquement ? en %s pour PostgreSQL
        """
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
        self.conn.commit()
    
    def rollback(self):
        """Rollback la transaction"""
        self.conn.rollback()
    
    def close(self):
        """Ferme la connexion"""
        if self._cursor:
            self._cursor.close()
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        self.close()


def get_db():
    """
    Connexion à PostgreSQL avec wrapper compatible SQLite
    Retourne un objet qui émule l'interface sqlite3.Connection

    Note: N'utilise PAS RealDictCursor pour être compatible avec fetchone()[0]

    ⚠️ IMPORTANT: Pensez à fermer la connexion avec db.close() ou utiliser get_db_context()
    """
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=10
    )
    # Utiliser le cursor par défaut (tuple) pour compatibilité avec [0]
    # mais on va wrapper pour supporter aussi dict-like access
    return PostgresConnection(conn)


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
