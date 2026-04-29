import hashlib
import json
from dataclasses import dataclass
from typing import Any, Optional

from flask import Request


class ConcurrencyConflictError(Exception):
    def __init__(self, message: str, current_version: Optional[int] = None):
        super().__init__(message)
        self.current_version = current_version


class IdempotencyError(Exception):
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class IdempotencyToken:
    row_id: int
    scope: str
    key: str


@dataclass
class IdempotencyReplay:
    status_code: int
    body: dict[str, Any]


def parse_expected_version(request: Request, payload: Any = None) -> Optional[int]:
    raw = None
    if payload and isinstance(payload, dict):
        raw = payload.get("expected_version")

    if raw is None:
        raw = request.headers.get("X-Incident-Version")
    if raw is None:
        raw = request.form.get("expected_version")

    if raw in (None, ""):
        return None

    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        raise ValueError("Version attendue invalide")

    if parsed <= 0:
        raise ValueError("Version attendue invalide")
    return parsed


def get_idempotency_key(request: Request, payload: Any = None) -> Optional[str]:
    key = request.headers.get("X-Idempotency-Key")
    if not key and payload and isinstance(payload, dict):
        key = payload.get("idempotency_key")
    if not key:
        key = request.form.get("idempotency_key")

    if not key:
        return None

    normalized = str(key).strip()
    if not normalized:
        return None
    if len(normalized) > 128:
        raise IdempotencyError("Clé d'idempotence trop longue", status_code=400)
    return normalized


def ensure_idempotency_tables(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS request_idempotency (
            id SERIAL PRIMARY KEY,
            scope VARCHAR(120) NOT NULL,
            key VARCHAR(128) NOT NULL,
            actor VARCHAR(255),
            incident_id INTEGER,
            request_hash VARCHAR(64) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'processing',
            response_code INTEGER,
            response_body JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(scope, key)
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_request_idempotency_scope_created ON request_idempotency(scope, created_at DESC)"
    )


def _hash_payload(payload: Any) -> str:
    serialized = json.dumps(payload or {}, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def begin_idempotent_request(db, *, scope: str, key: Optional[str], actor: str, payload: Any, incident_id: Optional[int] = None):
    if not key:
        return None

    request_hash = _hash_payload(payload)
    inserted = db.execute(
        """
        INSERT INTO request_idempotency (scope, key, actor, incident_id, request_hash, status)
        VALUES (%s, %s, %s, %s, %s, 'processing')
        ON CONFLICT (scope, key) DO NOTHING
        RETURNING id
        """,
        (scope, key, actor, incident_id, request_hash),
    ).fetchone()

    if inserted:
        return IdempotencyToken(row_id=inserted["id"], scope=scope, key=key)

    existing = db.execute(
        """
        SELECT id, request_hash, status, response_code, response_body
        FROM request_idempotency
        WHERE scope=%s AND key=%s
        """,
        (scope, key),
    ).fetchone()

    if not existing:
        raise IdempotencyError("Impossible de vérifier l'idempotence")

    if existing["request_hash"] != request_hash:
        raise IdempotencyError("Clé d'idempotence déjà utilisée avec un payload différent", status_code=409)

    if existing["status"] == "completed" and existing.get("response_body") is not None:
        return IdempotencyReplay(
            status_code=existing.get("response_code") or 200,
            body=existing["response_body"],
        )

    raise IdempotencyError("Une requête identique est déjà en cours, réessayez dans un instant", status_code=409)


def complete_idempotent_request(db, token: Optional[IdempotencyToken], *, status_code: int, body: dict[str, Any]) -> None:
    if not token:
        return
    db.execute(
        """
        UPDATE request_idempotency
        SET status='completed', response_code=%s, response_body=%s, updated_at=CURRENT_TIMESTAMP
        WHERE id=%s
        """,
        (status_code, json.dumps(body), token.row_id),
    )


def release_idempotent_request(db, token: Optional[IdempotencyToken]) -> None:
    if not token:
        return
    db.execute("DELETE FROM request_idempotency WHERE id=%s AND status='processing'", (token.row_id,))


def optimistic_incident_update(db, *, incident_id: int, expected_version: int, set_clause: str, params: tuple[Any, ...]):
    result = db.execute(
        f"UPDATE incidents SET {set_clause} WHERE id=%s AND version=%s RETURNING version",
        (*params, incident_id, expected_version),
    ).fetchone()
    if result:
        return result["version"]

    current = db.execute("SELECT version FROM incidents WHERE id=%s", (incident_id,)).fetchone()
    if not current:
        raise ConcurrencyConflictError("Incident introuvable")
    raise ConcurrencyConflictError(
        "Ce ticket a été modifié par un autre technicien",
        current_version=current["version"],
    )
