"""Worker Windows: conexão de saída HTTPS; sem shell remoto ou execução arbitrária."""
import json
import os
import time
from pathlib import Path

import requests

from workstation_agent.policy import (
    PolicyError, read_project_file, run_approved_check,
    write_project_file, workspace_root,
)

SERVER = os.getenv("JARVIS_SERVER_URL", "").rstrip("/")
TOKEN = os.getenv("JARVIS_DEVICE_TOKEN", "").strip()
WORKSPACE = os.getenv("JARVIS_WORKSPACE", "").strip()
POLL_SECONDS = max(3, min(int(os.getenv("JARVIS_POLL_SECONDS", "5")), 60))
VERIFY_TLS = os.getenv("JARVIS_VERIFY_TLS", "true").lower() == "true"


def _headers():
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def _list_files(root, limit=300):
    base = workspace_root(root)
    found = []
    ignored = {".git", ".venv", "venv", "__pycache__", "node_modules", ".env", "secrets"}
    for current, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = [d for d in dirs if d.lower() not in ignored and not (Path(current) / d).is_symlink()]
        for name in files:
            path = Path(current) / name
            rel = path.relative_to(base).as_posix()
            try:
                # Same path policy blocks environment files, keys and protected folders.
                from workstation_agent.policy import resolve_workspace_path
                resolve_workspace_path(base, rel)
                found.append(rel)
            except PolicyError:
                continue
            if len(found) >= limit:
                return found
    return found


def _execute(job):
    operation = job.get("operation")
    payload = job.get("payload") or {}
    if operation == "list_files":
        return {"files": _list_files(WORKSPACE)}
    if operation == "read_file":
        return {"path": payload["path"], "content": read_project_file(WORKSPACE, payload["path"])}
    if operation == "write_file":
        path = write_project_file(WORKSPACE, payload["path"], payload["content"])
        return {"written": True, "path": path}
    if operation == "run_check":
        return run_approved_check(WORKSPACE, payload["check"])
    raise PolicyError("Operação desconhecida; bloqueada por segurança.")


def main():
    if not SERVER.startswith("https://"):
        raise SystemExit("JARVIS_SERVER_URL precisa começar com https://")
    if not TOKEN:
        raise SystemExit("JARVIS_DEVICE_TOKEN não configurado.")
    if not WORKSPACE:
        raise SystemExit("JARVIS_WORKSPACE não configurado.")
    workspace_root(WORKSPACE)
    session = requests.Session()
    while True:
        try:
            response = session.get(
                f"{SERVER}/v1/workstation/poll",
                headers=_headers(), timeout=(10, 30), verify=VERIFY_TLS,
            )
            response.raise_for_status()
            job = response.json().get("job")
            if not job:
                time.sleep(POLL_SECONDS)
                continue
            try:
                result = _execute(job)
                failed = False
            except Exception as exc:
                result = {"error": str(exc)[:2000], "type": type(exc).__name__}
                failed = True
            posted = session.post(
                f"{SERVER}/v1/workstation/jobs/{job['id']}/result",
                headers=_headers(),
                json={"result": result, "failed": failed},
                timeout=(10, 30), verify=VERIFY_TLS,
            )
            posted.raise_for_status()
        except requests.RequestException as exc:
            print(f"Conexão Jarvis indisponível: {exc}")
            time.sleep(max(POLL_SECONDS, 10))


if __name__ == "__main__":
    main()
