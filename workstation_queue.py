"""Fila isolada do worker Windows; não altera a fila de IA nem a integração Dealwork."""
import hashlib
import json
import secrets
import uuid

import psycopg
from psycopg.rows import dict_row

from workstation_agent.policy import CHECKS

DATABASE_URL = __import__("os").getenv("DATABASE_URL", "")


def _connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não configurada.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)


def _init():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jarvis_workstation_devices (
                id UUID PRIMARY KEY,
                label TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_seen_at TIMESTAMPTZ
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jarvis_workstation_jobs (
                id UUID PRIMARY KEY,
                device_id UUID NOT NULL REFERENCES jarvis_workstation_devices(id),
                operation TEXT NOT NULL,
                payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','running','completed','failed','cancelled')),
                result JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                started_at TIMESTAMPTZ,
                finished_at TIMESTAMPTZ
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS jarvis_workstation_jobs_idx ON jarvis_workstation_jobs(device_id, status, created_at)")


def create_device(label):
    _init()
    label = str(label or "Computador Windows").strip()[:100]
    token = secrets.token_urlsafe(36)
    device_id = str(uuid.uuid4())
    digest = hashlib.sha256(token.encode()).hexdigest()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO jarvis_workstation_devices (id,label,token_hash) VALUES (%s,%s,%s)",
            (device_id, label, digest),
        )
    return {"device_id": device_id, "label": label, "token": token}


def authenticate_device(token):
    if not token or len(token) > 200:
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    _init()
    with _connect() as conn:
        row = conn.execute(
            "UPDATE jarvis_workstation_devices SET last_seen_at=NOW() WHERE token_hash=%s AND active=TRUE RETURNING id,label",
            (digest,),
        ).fetchone()
    return dict(row) if row else None


def revoke_device(device_id):
    _init()
    with _connect() as conn:
        row = conn.execute(
            "UPDATE jarvis_workstation_devices SET active=FALSE WHERE id=%s RETURNING id",
            (device_id,),
        ).fetchone()
    return bool(row)


def list_devices():
    _init()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id,label,active,created_at,last_seen_at FROM jarvis_workstation_devices ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def enqueue_job(device_id, operation, payload):
    _init()
    allowed = {"list_files", "read_file", "write_file", "run_check"}
    if operation not in allowed:
        raise ValueError("Operação não permitida.")
    if not isinstance(payload, dict):
        raise ValueError("payload deve ser um objeto.")
    if operation == "run_check" and payload.get("check") not in CHECKS:
        raise ValueError("Verificação não permitida.")
    if operation in {"read_file", "write_file"} and not isinstance(payload.get("path"), str):
        raise ValueError("Informe o caminho relativo do arquivo.")
    if operation == "write_file" and not isinstance(payload.get("content"), str):
        raise ValueError("Conteúdo do arquivo inválido.")
    job_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO jarvis_workstation_jobs (id,device_id,operation,payload) VALUES (%s,%s,%s,%s::jsonb)",
            (job_id, device_id, operation, json.dumps(payload, ensure_ascii=False)),
        )
    return {"id": job_id, "device_id": device_id, "operation": operation, "status": "pending"}


def claim_job(device_id):
    _init()
    with _connect() as conn:
        row = conn.execute("""
            WITH candidate AS (
                SELECT id FROM jarvis_workstation_jobs
                WHERE device_id=%s AND status='pending'
                ORDER BY created_at ASC
                FOR UPDATE SKIP LOCKED LIMIT 1
            )
            UPDATE jarvis_workstation_jobs
            SET status='running', started_at=NOW()
            WHERE id=(SELECT id FROM candidate)
            RETURNING id,operation,payload
        """, (device_id,)).fetchone()
    return dict(row) if row else None


def finish_job(device_id, job_id, result, failed=False):
    _init()
    if not isinstance(result, dict):
        raise ValueError("Resultado inválido.")
    with _connect() as conn:
        row = conn.execute("""
            UPDATE jarvis_workstation_jobs
            SET status=%s, result=%s::jsonb, finished_at=NOW()
            WHERE id=%s AND device_id=%s AND status='running'
            RETURNING id,status
        """, ("failed" if failed else "completed", json.dumps(result, ensure_ascii=False)[:100000], job_id, device_id)).fetchone()
    return dict(row) if row else None


def get_job(device_id, job_id):
    _init()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id,device_id,operation,status,result,created_at,started_at,finished_at FROM jarvis_workstation_jobs WHERE id=%s AND device_id=%s",
            (job_id, device_id),
        ).fetchone()
    return dict(row) if row else None
