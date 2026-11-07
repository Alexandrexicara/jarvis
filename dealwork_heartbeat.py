"""Heartbeat oficial do agente Jarvis no DealworkAI.

Prioriza Bearer API key (método recomendado pela documentação oficial).
Mantém HMAC como fallback compatível. Não cria outro agente nem envia propostas.
"""
import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time

import requests

BASE_URL = os.getenv("DEALWORK_BASE_URL", "https://dealwork.ai/api/v1").rstrip("/")
AGENT_ID = os.getenv("DEALWORK_AGENT_ID", "").strip()
API_KEY = os.getenv("DEALWORK_AGENT_API_KEY", "").strip()
HMAC_SECRET = os.getenv("DEALWORK_HMAC_SECRET", "").strip()
SKILL_URL = "https://dealwork.ai/skill.md"
FALLBACK_SKILL_VERSION = "1.6.5"
HEARTBEAT_INTERVAL = max(300, int(os.getenv("DEALWORK_HEARTBEAT_INTERVAL", "1200")))

_lock = threading.Lock()
_started = False
_status = {
    "configured": bool(AGENT_ID and (API_KEY or HMAC_SECRET)),
    "auth_method": "bearer" if API_KEY else ("hmac" if HMAC_SECRET else None),
    "ok": False, "skill_version": None, "last_success": None, "last_error": None,
}


def _current_skill_version():
    try:
        response = requests.get(SKILL_URL, timeout=(5, 15))
        response.raise_for_status()
        match = re.search(r"(?m)^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", response.text)
        if match:
            return match.group(1)
    except requests.RequestException as exc:
        logging.warning("Jarvis: não foi possível consultar a versão da skill Dealwork: %s", exc)
    return FALLBACK_SKILL_VERSION


def send_heartbeat():
    if not AGENT_ID or not (API_KEY or HMAC_SECRET):
        _status.update(configured=False, ok=False,
                       last_error="DEALWORK_AGENT_ID e DEALWORK_AGENT_API_KEY (ou HMAC_SECRET) são necessários.")
        return False

    version = _current_skill_version()
    payload = {"skillVersion": version}
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
        auth_method = "bearer"
    else:
        timestamp = str(int(time.time()))
        signed = f"{AGENT_ID}{timestamp}{body}".encode("utf-8")
        signature = hmac.new(HMAC_SECRET.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        headers.update({
            "X-Agent-ID": AGENT_ID,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        })
        auth_method = "hmac"

    try:
        response = requests.post(
            f"{BASE_URL}/agents/{AGENT_ID}/heartbeat",
            data=body.encode("utf-8"),
            headers=headers,
            timeout=(8, 25),
        )
        if not response.ok:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")
        _status.update(configured=True, auth_method=auth_method, ok=True,
                       skill_version=version, last_success=int(time.time()), last_error=None)
        logging.info("Jarvis Dealwork heartbeat confirmado via %s; skillVersion=%s",
                     auth_method, version)
        return True
    except (requests.RequestException, RuntimeError) as exc:
        _status.update(configured=True, auth_method=auth_method, ok=False,
                       skill_version=version, last_error=str(exc)[:550])
        logging.error("Jarvis Dealwork heartbeat falhou via %s: %s", auth_method, exc)
        return False


def heartbeat_status():
    return dict(_status)


def _heartbeat_loop():
    while True:
        send_heartbeat()
        time.sleep(HEARTBEAT_INTERVAL)


def start_heartbeat():
    global _started
    with _lock:
        if _started:
            return
        if not AGENT_ID or not (API_KEY or HMAC_SECRET):
            logging.warning("Jarvis Dealwork heartbeat não iniciado: credenciais ausentes.")
            return
        thread = threading.Thread(target=_heartbeat_loop,
                                  name="jarvis-dealwork-heartbeat", daemon=True)
        thread.start()
        _started = True


def register_heartbeat_route(app, require_access_key):
    from flask import jsonify

    @app.get("/v1/dealwork/heartbeat")
    @require_access_key
    def dealwork_heartbeat_status():
        return jsonify(heartbeat_status())
