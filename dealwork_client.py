import os
import re
import hmac
import hashlib
import json
import time
from decimal import Decimal, InvalidOperation
import requests
from flask import jsonify, request

BASE_URL = os.getenv("DEALWORK_BASE_URL", "https://dealwork.ai/api/v1").rstrip("/")
AGENT_ID = os.getenv("DEALWORK_AGENT_ID", "").strip()
HMAC_SECRET = os.getenv("DEALWORK_HMAC_SECRET", "").strip()
TIMEOUT = (8, 35)

class DealworkError(RuntimeError):
    pass

def _request(method, path, *, params=None, payload=None):
    if not AGENT_ID or not HMAC_SECRET:
        raise DealworkError("Credenciais HMAC do Dealwork não configuradas no Render.")
    if not path.startswith("/") or ".." in path:
        raise DealworkError("Caminho Dealwork inválido.")
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) if payload is not None else ""
    timestamp = str(int(time.time()))
    signed_payload = f"{AGENT_ID}{timestamp}{body}".encode("utf-8")
    signature = hmac.new(HMAC_SECRET.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    headers = {
        "X-Agent-ID": AGENT_ID,
        "X-Timestamp": timestamp,
        "X-Signature": signature,
        "Accept": "application/json",
    }
    if body:
        headers["Content-Type"] = "application/json"
    try:
        response = requests.request(
            method, f"{BASE_URL}{path}", params=params,
            data=body.encode("utf-8") if body else None,
            headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise DealworkError(f"Falha de conexão com Dealwork: {exc}") from exc
    try:
        data = response.json()
    except ValueError:
        data = {"message": response.text[:1000]}
    if not response.ok:
        error = data.get("error", {}) if isinstance(data, dict) else {}
        message = error.get("message") or data.get("message") or f"HTTP {response.status_code}"
        raise DealworkError(f"Dealwork HTTP {response.status_code}: {message}")
    return data

def register_routes(app, require_access_key):
    @app.get("/v1/dealwork/status")
    @require_access_key
    def dealwork_status():
        if not AGENT_ID or not HMAC_SECRET:
            return jsonify({"connected": False, "agent_id": AGENT_ID or None,
                            "message": "Faltam as credenciais HMAC do Dealwork no Render."}), 503
        try:
            profile = _request("GET", "/agents/me")
            return jsonify({"connected": True, "agent_id": AGENT_ID or None,
                            "profile": profile.get("data", profile)})
        except DealworkError as exc:
            return jsonify({"connected": False, "agent_id": AGENT_ID or None,
                            "error": str(exc)}), 502

    @app.get("/v1/dealwork/jobs")
    @require_access_key
    def dealwork_jobs():
        try:
            page = max(1, min(int(request.args.get("page", "1")), 10000))
            per_page = max(1, min(int(request.args.get("per_page", "20")), 50))
            params = {"page": page, "per_page": per_page}
            for key in ("category", "eligible_worker_types", "budget_min", "budget_max", "sort"):
                value = request.args.get(key)
                if value:
                    params[key] = value[:120]
            return jsonify(_request("GET", "/jobs", params=params))
        except (ValueError, DealworkError) as exc:
            return jsonify({"error": {"message": str(exc)}}), 400

    @app.get("/v1/dealwork/contracts")
    @require_access_key
    def dealwork_contracts():
        try:
            role = request.args.get("role", "worker")
            if role not in {"worker", "buyer", "agent"}:
                return jsonify({"error": {"message": "role deve ser worker, buyer ou agent."}}), 400
            params = {"role": role, "per_page": max(1, min(int(request.args.get("per_page", "20")), 50))}
            if request.args.get("state"):
                params["state"] = request.args["state"][:40]
            return jsonify(_request("GET", "/contracts", params=params))
        except (ValueError, DealworkError) as exc:
            return jsonify({"error": {"message": str(exc)}}), 400

    @app.post("/v1/dealwork/jobs/<job_id>/bids")
    @require_access_key
    def dealwork_place_bid(job_id):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", job_id):
            return jsonify({"error": {"message": "ID de trabalho inválido."}}), 400
        body = request.get_json(silent=True) or {}
        try:
            amount = Decimal(str(body.get("proposedAmount", "")))
            if not amount.is_finite() or amount <= 0 or amount > Decimal("1000000"):
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return jsonify({"error": {"message": "proposedAmount deve ser um valor positivo em USD."}}), 400
        proposal = str(body.get("proposalText") or "").strip()
        if not proposal or len(proposal) > 10000:
            return jsonify({"error": {"message": "Informe proposalText (1 a 10.000 caracteres)."}}), 400
        payload = {"proposedAmount": format(amount, ".2f"), "proposalText": proposal}
        if body.get("estimatedHours") is not None:
            try:
                hours = float(body["estimatedHours"])
                if not (0 < hours <= 10000):
                    raise ValueError
                payload["estimatedHours"] = hours
            except (TypeError, ValueError):
                return jsonify({"error": {"message": "estimatedHours deve ser positivo."}}), 400
        try:
            return jsonify(_request("POST", f"/jobs/{job_id}/bids", payload=payload)), 201
        except DealworkError as exc:
            return jsonify({"error": {"message": str(exc)}}), 502
