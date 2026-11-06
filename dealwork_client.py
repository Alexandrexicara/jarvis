import os
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

import requests
from flask import jsonify, request

BASE_URL = os.getenv("DEALWORK_BASE_URL", "https://dealwork.ai/api/v1").rstrip("/")
API_KEY = os.getenv("DEALWORK_AGENT_API_KEY", "").strip()
AGENT_ID = os.getenv("DEALWORK_AGENT_ID", "").strip()
TIMEOUT = (8, 35)


class DealworkError(RuntimeError):
    pass


def _request(method, path, *, params=None, payload=None):
    if not API_KEY:
        raise DealworkError("DEALWORK_AGENT_API_KEY não configurada no Render.")
    if not path.startswith("/") or ".." in path:
        raise DealworkError("Caminho Dealwork inválido.")
    try:
        response = requests.request(
            method,
            f"{BASE_URL}{path}",
            params=params,
            json=payload,
            headers={"Authorization": f"Bearer {API_KEY}", "Accept": "application/json",
                     "Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
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
        if not API_KEY:
            return jsonify({"connected": False, "registered": bool(AGENT_ID),
                            "message": "Falta configurar DEALWORK_AGENT_API_KEY no Render."}), 503
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
        payload = {"proposedAmount": format(amount, ".2f"),
                   "proposalText": proposal}
        if body.get("estimatedHours") is not None:
            try:
                hours = float(body["estimatedHours"])
                if not (0 < hours <= 10000):
                    raise ValueError
                payload["estimatedHours"] = hours
            except (TypeError, ValueError):
                return jsonify({"error": {"message": "estimatedHours deve ser positivo."}}), 400
        try:
            result = _request("POST", f"/jobs/{job_id}/bids", payload=payload)
            return jsonify(result), 201
        except DealworkError as exc:
            return jsonify({"error": {"message": str(exc)}}), 502
