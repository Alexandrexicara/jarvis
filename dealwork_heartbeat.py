"""Heartbeat oficial do agente Jarvis no DealworkAI.

Tenta Bearer primeiro e, em caso de rejeição de autenticação, tenta HMAC.
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
API_KEY = (os.getenv("DEALWORK_API_KEY") or os.getenv("DEALWORK_AGENT_API_KEY", "")).strip()
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


def _headers(auth_method, body):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if auth_method == "bearer":
        headers["Authorization"] = f"Bearer {API_KEY}"
    else:
        timestamp = str(int(time.time()))
        signed = f"{AGENT_ID}{timestamp}{body}".encode("utf-8")
        signature = hmac.new(HMAC_SECRET.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        headers.update({
            "X-Agent-ID": AGENT_ID,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        })
    return headers


def send_heartbeat():
    if not AGENT_ID or not (API_KEY or HMAC_SECRET):
        _status.update(configured=False, ok=False,
                       last_error="DEALWORK_AGENT_ID e DEALWORK_AGENT_API_KEY (ou HMAC_SECRET) são necessários.")
        return False

    version = _current_skill_version()
    body = json.dumps({"skillVersion": version}, ensure_ascii=False, separators=(",", ":"))
    methods = (["bearer", "hmac"] if API_KEY and HMAC_SECRET else
               (["bearer"] if API_KEY else ["hmac"]))
    errors = []

    for auth_method in methods:
        try:
            response = requests.post(
                f"{BASE_URL}/agents/{AGENT_ID}/heartbeat",
                data=body.encode("utf-8"),
                headers=_headers(auth_method, body),
                timeout=(8, 25),
            )
            if response.ok:
                _status.update(configured=True, auth_method=auth_method, ok=True,
                               skill_version=version, last_success=int(time.time()), last_error=None)
                logging.info("Jarvis Dealwork heartbeat confirmado via %s; skillVersion=%s",
                             auth_method, version)
                return True

            error = f"HTTP {response.status_code}: {response.text[:350]}"
            errors.append(f"{auth_method}: {error}")
            # Só tenta o segundo método quando a autenticação foi rejeitada.
            if response.status_code not in (401, 403):
                break
        except requests.RequestException as exc:
            errors.append(f"{auth_method}: {exc}")
            break

    message = " | ".join(errors)
    _status.update(configured=True, auth_method=methods[-1], ok=False,
                   skill_version=version, last_error=message[:550])
    logging.error("Jarvis Dealwork heartbeat falhou: %s", message)
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
