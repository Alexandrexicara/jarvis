"""Read-only supervisor for the existing Monitor Aviator API."""
import os
import threading
import time
from datetime import datetime, timezone

import requests

API_URL = os.getenv("MONITOR_AVIATOR_API_URL", "").rstrip("/")
AGENT_TOKEN = os.getenv("MONITOR_AVIATOR_AGENT_TOKEN", "").strip()
POLL_SECONDS = max(30, min(int(os.getenv("MONITOR_AVIATOR_POLL_SECONDS", "60")), 900))

_lock = threading.Lock()
_started = False
_state = {
    "configured": bool(API_URL and AGENT_TOKEN),
    "status": "not_configured" if not (API_URL and AGENT_TOKEN) else "starting",
    "last_checked_at": None,
    "last_error": None,
    "summary": None,
}


def get_monitor_aviator_status():
    with _lock:
        return dict(_state)


def _record_state(status, summary=None, error=None):
    with _lock:
        previous = _state["status"]
        _state.update({
            "configured": True,
            "status": status,
            "last_checked_at": datetime.now(timezone.utc).isoformat(),
            "last_error": error,
            "summary": summary,
        })
    return previous


def _post_event(session, event, message, summary=None):
    try:
        session.post(
            f"{API_URL}/api/agent/events",
            headers={"Authorization": f"Bearer {AGENT_TOKEN}"},
            json={"event": event, "message": message, "details": summary or {}},
            timeout=(5, 10),
        ).raise_for_status()
    except requests.RequestException:
        # A falha no canal de auditoria não deve derrubar o supervisor.
        pass


def _supervise():
    session = requests.Session()
    headers = {"Authorization": f"Bearer {AGENT_TOKEN}", "Accept": "application/json"}
    while True:
        try:
            response = session.get(
                f"{API_URL}/api/agent/summary",
                headers=headers,
                timeout=(5, 15),
            )
            response.raise_for_status()
            summary = response.json()
            healthy = bool(summary.get("ok")) and summary.get("database") == "connected"
            if summary.get("database") == "memory-demo":
                healthy = False
            status = "online" if healthy else "degraded"
            previous = _record_state(status, summary=summary)
            if previous != status:
                if status == "online":
                    event = "supervisor_recovered" if previous == "degraded" else "supervisor_online"
                    message = "Jarvis confirmou que a API e o banco do Monitor Aviator estão acessíveis."
                else:
                    event = "supervisor_degraded"
                    message = "Jarvis detectou que a API está acessível, mas o banco não está em estado persistente saudável."
                _post_event(session, event, message, {
                    "database": summary.get("database"),
                    "totalRounds": summary.get("totalRounds"),
                    "roundsLastHour": summary.get("roundsLastHour"),
                })
        except (requests.RequestException, ValueError) as exc:
            previous = _record_state("offline", error=str(exc)[:500])
            if previous != "offline":
                _post_event(session, "supervisor_degraded", "Jarvis não conseguiu consultar a API do Monitor Aviator.", {
                    "error": str(exc)[:300],
                })
        time.sleep(POLL_SECONDS)


def start_monitor_aviator_supervisor():
    global _started
    if not API_URL or not AGENT_TOKEN:
        return False
    with _lock:
        if _started:
            return True
        _started = True
    thread = threading.Thread(target=_supervise, name="monitor-aviator-supervisor", daemon=True)
    thread.start()
    return True
