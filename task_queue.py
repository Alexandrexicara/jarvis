import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
import requests

DATABASE_URL = os.getenv("DATABASE_URL", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
WORKER_THREADS = max(1, min(int(os.getenv("JARVIS_WORKER_THREADS", "2")), 8))
POLL_SECONDS = max(1, int(os.getenv("JARVIS_TASK_POLL_SECONDS", "3")))

_init_lock = threading.Lock()
_initialized = False
_workers_started = False
_worker_lock = threading.Lock()


def _connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não configurada. Configure um PostgreSQL no Render.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)


def init_db():
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        with _connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jarvis_tasks (
                    id UUID PRIMARY KEY,
                    title TEXT NOT NULL,
                    messages JSONB NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','running','completed','failed','cancelled')),
                    result JSONB,
                    error TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    started_at TIMESTAMPTZ,
                    finished_at TIMESTAMPTZ,
                    attempts INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS jarvis_tasks_status_created_idx ON jarvis_tasks(status, created_at)")
        _initialized = True


def enqueue_tasks(items):
    init_db()
    created = []
    with _connect() as conn:
        for item in items:
            task_id = str(uuid.uuid4())
            title = str(item.get("title") or item.get("name") or "Tarefa Jarvis")[:180]
            messages = item.get("messages")
            if not messages:
                prompt = item.get("prompt") or item.get("task") or item.get("description")
                if not prompt:
                    raise ValueError("Cada tarefa precisa de 'prompt' ou 'messages'.")
                messages = [{"role": "user", "content": str(prompt)}]
            if not isinstance(messages, list) or not messages:
                raise ValueError("messages deve ser uma lista não vazia.")
            conn.execute(
                "INSERT INTO jarvis_tasks (id, title, messages) VALUES (%s, %s, %s::jsonb)",
                (task_id, title, json.dumps(messages, ensure_ascii=False))
            )
            created.append({"id": task_id, "title": title, "status": "pending"})
    return created


def get_tasks(limit=100, status=None):
    init_db()
    limit = max(1, min(int(limit), 1000))
    with _connect() as conn:
        if status:
            rows = conn.execute(
                "SELECT id, title, status, result, error, created_at, started_at, finished_at, attempts FROM jarvis_tasks WHERE status=%s ORDER BY created_at DESC LIMIT %s",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, status, result, error, created_at, started_at, finished_at, attempts FROM jarvis_tasks ORDER BY created_at DESC LIMIT %s",
                (limit,)
            ).fetchall()
    return [dict(row) for row in rows]


def get_task(task_id):
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, title, status, result, error, created_at, started_at, finished_at, attempts FROM jarvis_tasks WHERE id=%s",
            (task_id,)
        ).fetchone()
    return dict(row) if row else None


def cancel_task(task_id):
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "UPDATE jarvis_tasks SET status='cancelled', finished_at=NOW() WHERE id=%s AND status='pending' RETURNING id",
            (task_id,)
        ).fetchone()
    return bool(row)


def _claim_task():
    with _connect() as conn:
        row = conn.execute("""
            WITH next_task AS (
                SELECT id FROM jarvis_tasks
                WHERE status='pending'
                ORDER BY created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE jarvis_tasks
            SET status='running', started_at=NOW(), attempts=attempts+1, error=NULL
            WHERE id=(SELECT id FROM next_task)
            RETURNING id, title, messages
        """).fetchone()
    return dict(row) if row else None


def _run_task(task):
    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY não configurada no Render.")
    response = requests.post(
        f"{NVIDIA_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": NVIDIA_MODEL,
            "messages": task["messages"],
            "temperature": 0.2,
            "max_tokens": 1200,
            "stream": False
        },
        timeout=120
    )
    if not response.ok:
        raise RuntimeError(f"NVIDIA HTTP {response.status_code}: {response.text[:1500]}")
    return response.json()


def _worker_loop():
    while True:
        try:
            task = _claim_task()
            if not task:
                time.sleep(POLL_SECONDS)
                continue
            try:
                result = _run_task(task)
                with _connect() as conn:
                    conn.execute(
                        "UPDATE jarvis_tasks SET status='completed', result=%s::jsonb, finished_at=NOW() WHERE id=%s AND status='running'",
                        (json.dumps(result, ensure_ascii=False), task["id"])
                    )
            except Exception as exc:
                with _connect() as conn:
                    conn.execute(
                        "UPDATE jarvis_tasks SET status='failed', error=%s, finished_at=NOW() WHERE id=%s AND status='running'",
                        (str(exc)[:4000], task["id"])
                    )
        except Exception:
            time.sleep(max(POLL_SECONDS, 5))


def start_workers():
    global _workers_started
    if not DATABASE_URL:
        return False
    with _worker_lock:
        if _workers_started:
            return True
        init_db()
        for index in range(WORKER_THREADS):
            thread = threading.Thread(target=_worker_loop, name=f"jarvis-task-worker-{index+1}", daemon=True)
            thread.start()
        _workers_started = True
    return True


def task_stats():
    init_db()
    with _connect() as conn:
        rows = conn.execute("SELECT status, COUNT(*) AS total FROM jarvis_tasks GROUP BY status").fetchall()
    stats = {key: 0 for key in ("pending", "running", "completed", "failed", "cancelled")}
    for row in rows:
        stats[row["status"]] = row["total"]
    stats["total"] = sum(stats.values())
    return stats
