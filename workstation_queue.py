"""Fila persistente e trilha de auditoria do worker Windows."""
import hashlib
import json
import os
import secrets
import uuid

import psycopg
from psycopg.rows import dict_row

from workstation_agent.policy import CHECKS

MAX_RESULT_BYTES = 100_000
SCHEMA_READY = False


def _connect():
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL não configurada.")
    return psycopg.connect(database_url, row_factory=dict_row, connect_timeout=10)


def _init():
    global SCHEMA_READY
    if SCHEMA_READY:
        return
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jarvis_workstation_devices (
                id UUID PRIMARY KEY, label TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
                active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_seen_at TIMESTAMPTZ
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jarvis_workstation_jobs (
                id UUID PRIMARY KEY,
                device_id UUID NOT NULL REFERENCES jarvis_workstation_devices(id),
                operation TEXT NOT NULL, payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','running','completed','failed','cancelled')),
                result JSONB, attempts INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("ALTER TABLE jarvis_workstation_jobs ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0")
        conn.execute("ALTER TABLE jarvis_workstation_jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jarvis_workstation_audit (
                id BIGSERIAL PRIMARY KEY, device_id UUID, job_id UUID,
                event TEXT NOT NULL, details JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS jarvis_workstation_jobs_idx ON jarvis_workstation_jobs(device_id, status, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS jarvis_workstation_audit_idx ON jarvis_workstation_audit(created_at DESC)")
    SCHEMA_READY = True


def _audit(conn, event, device_id=None, job_id=None, details=None):
    conn.execute(
        "INSERT INTO jarvis_workstation_audit (device_id,job_id,event,details) VALUES (%s,%s,%s,%s::jsonb)",
        (device_id, job_id, event, json.dumps(details or {}, ensure_ascii=False)[:10000]),
    )


def create_device(label):
    _init()
    label = str(label or "Computador Windows").strip()[:100]
    token = secrets.token_urlsafe(36)
    device_id = str(uuid.uuid4())
    digest = hashlib.sha256(token.encode()).hexdigest()
    with _connect() as conn:
        conn.execute("INSERT INTO jarvis_workstation_devices (id,label,token_hash) VALUES (%s,%s,%s)", (device_id, label, digest))
        _audit(conn, "device_created", device_id, details={"label": label})
    return {"device_id": device_id, "label": label, "token": token}


def authenticate_device(token):
    if not token or len(token) > 200:
        return None
    _init()
    digest = hashlib.sha256(token.encode()).hexdigest()
    with _connect() as conn:
        row = conn.execute(
            "UPDATE jarvis_workstation_devices SET last_seen_at=NOW() WHERE token_hash=%s AND active=TRUE RETURNING id,label",
            (digest,),
        ).fetchone()
    return {"id": str(row["id"]), "label": row["label"]} if row else None


def revoke_device(device_id):
    _init()
    with _connect() as conn:
        row = conn.execute("UPDATE jarvis_workstation_devices SET active=FALSE WHERE id=%s RETURNING id", (device_id,)).fetchone()
        if row:
            _audit(conn, "device_revoked", device_id)
    return bool(row)


def list_devices():
    _init()
    with _connect() as conn:
        rows = conn.execute("SELECT id,label,active,created_at,last_seen_at FROM jarvis_workstation_devices ORDER BY created_at DESC").fetchall()
    return [{**dict(row), "id": str(row["id"])} for row in rows]


def enqueue_job(device_id, operation, payload):
    _init()
    allowed = {"list_files", "read_file", "write_file", "run_check"}
    if operation not in allowed:
        raise ValueError("Operação não permitida.")
    if not isinstance(payload, dict):
        raise ValueError("payload deve ser um objeto.")
    # A flag enviada pelo cliente não é autorização. A permissão de escrita
    # é imposta localmente pelo worker e nunca é concedida pelo servidor.
    if operation == "run_check" and payload.get("check") not in CHECKS:
        raise ValueError("Verificação não permitida.")
    if operation in {"read_file", "write_file"} and not isinstance(payload.get("path"), str):
        raise ValueError("Informe o caminho relativo do arquivo.")
    if operation == "write_file":
        if not isinstance(payload.get("content"), str):
            raise ValueError("Conteúdo do arquivo inválido.")
        if len(payload["content"].encode("utf-8")) > 1_000_000:
            raise ValueError("Arquivo excede o limite de 1 MB.")
        payload = {"path": payload["path"], "content": payload["content"]}
    job_id = str(uuid.uuid4())
    with _connect() as conn:
        active = conn.execute("SELECT 1 FROM jarvis_workstation_devices WHERE id=%s AND active=TRUE", (device_id,)).fetchone()
        if not active:
            raise ValueError("Dispositivo inexistente ou revogado.")
        conn.execute(
            "INSERT INTO jarvis_workstation_jobs (id,device_id,operation,payload) VALUES (%s,%s,%s,%s::jsonb)",
            (job_id, device_id, operation, json.dumps(payload, ensure_ascii=False)),
        )
        _audit(conn, "job_queued", device_id, job_id, {"operation": operation})
    return {"id": job_id, "device_id": str(device_id), "operation": operation, "status": "pending"}


def claim_job(device_id):
    _init()
    with _connect() as conn:
        # Reclaim jobs left running by a crashed/offline worker after 10 minutes.
        conn.execute("""
            UPDATE jarvis_workstation_jobs
            SET status='pending', started_at=NULL, updated_at=NOW()
            WHERE device_id=%s AND status='running'
              AND started_at < NOW() - INTERVAL '10 minutes' AND attempts < 3
        """, (device_id,))
        row = conn.execute("""
            WITH candidate AS (
                SELECT id FROM jarvis_workstation_jobs
                WHERE device_id=%s AND status='pending' AND attempts < 3
                ORDER BY created_at ASC FOR UPDATE SKIP LOCKED LIMIT 1
            )
            UPDATE jarvis_workstation_jobs
            SET status='running', started_at=NOW(), updated_at=NOW(), attempts=attempts+1
            WHERE id=(SELECT id FROM candidate) RETURNING id,operation,payload,attempts
        """, (device_id,)).fetchone()
        if row:
            _audit(conn, "job_started", device_id, row["id"], {"operation": row["operation"], "attempt": row["attempts"]})
    if not row:
        return None
    return {"id": str(row["id"]), "operation": row["operation"], "payload": row["payload"], "attempt": row["attempts"]}


def finish_job(device_id, job_id, result, failed=False):
    if not isinstance(result, dict):
        raise ValueError("Resultado inválido.")
    serialized = json.dumps(result, ensure_ascii=False)
    if len(serialized.encode("utf-8")) > MAX_RESULT_BYTES:
        raise ValueError("Resultado excede o limite de 100 KB.")
    _init()
    with _connect() as conn:
        row = conn.execute("""
            UPDATE jarvis_workstation_jobs
            SET status=%s, result=%s::jsonb, finished_at=NOW(), updated_at=NOW()
            WHERE id=%s AND device_id=%s AND status='running' RETURNING id,status,operation
        """, ("failed" if failed else "completed", serialized, job_id, device_id)).fetchone()
        if row:
            _audit(conn, "job_failed" if failed else "job_completed", device_id, row["id"], {
                "operation": row["operation"], "result_type": result.get("type"),
                "error": str(result.get("error", ""))[:1000] if failed else "",
            })
    return {"id": str(row["id"]), "status": row["status"]} if row else None


def get_job(device_id, job_id):
    _init()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id,device_id,operation,status,result,attempts,created_at,started_at,finished_at FROM jarvis_workstation_jobs WHERE id=%s AND device_id=%s",
            (job_id, device_id),
        ).fetchone()
    if not row:
        return None
    return {**dict(row), "id": str(row["id"]), "device_id": str(row["device_id"])}


def list_audit(limit=50):
    _init()
    safe_limit = max(1, min(int(limit), 200))
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id,device_id,job_id,event,details,created_at FROM jarvis_workstation_audit ORDER BY id DESC LIMIT %s",
            (safe_limit,),
        ).fetchall()
    return [{**dict(row), "device_id": str(row["device_id"]) if row["device_id"] else None,
             "job_id": str(row["job_id"]) if row["job_id"] else None} for row in rows]
