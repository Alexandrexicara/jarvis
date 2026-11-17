"""Rotas autenticadas do braço Windows. Registrar em jarvis.py sem tocar nas rotas Dealwork."""
from functools import wraps

from flask import jsonify, request

from workstation_queue import (
    authenticate_device, claim_job, create_device, enqueue_job,
    finish_job, list_devices, revoke_device,
)


def register_workstation_routes(app, require_access_key):
    def require_device(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            token = auth.removeprefix("Bearer ").strip()
            device = authenticate_device(token)
            if not device:
                return jsonify({"error": "Dispositivo não autorizado."}), 401
            request.workstation_device = device
            return fn(*args, **kwargs)
        return wrapper

    @app.post("/v1/workstation/devices")
    @require_access_key
    def workstation_create_device():
        body = request.get_json(silent=True) or {}
        try:
            # Token aparece somente nesta resposta. Armazenamos apenas seu hash.
            return jsonify(create_device(body.get("label"))), 201
        except Exception as exc:
            app.logger.exception("Falha ao parear worker Windows")
            return jsonify({"error": str(exc)}), 503

    @app.get("/v1/workstation/devices")
    @require_access_key
    def workstation_list_devices():
        try:
            return jsonify({"devices": list_devices()})
        except Exception as exc:
            app.logger.exception("Falha ao listar workers Windows")
            return jsonify({"error": str(exc)}), 503

    @app.delete("/v1/workstation/devices/<device_id>")
    @require_access_key
    def workstation_revoke_device(device_id):
        try:
            return jsonify({"revoked": revoke_device(device_id)})
        except Exception as exc:
            app.logger.exception("Falha ao revogar worker Windows")
            return jsonify({"error": str(exc)}), 503

    @app.post("/v1/workstation/devices/<device_id>/jobs")
    @require_access_key
    def workstation_enqueue(device_id):
        body = request.get_json(silent=True) or {}
        try:
            job = enqueue_job(device_id, body.get("operation"), body.get("payload") or {})
            return jsonify(job), 202
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            app.logger.exception("Falha ao enfileirar tarefa Windows")
            return jsonify({"error": str(exc)}), 503

    @app.get("/v1/workstation/poll")
    @require_device
    def workstation_poll():
        try:
            job = claim_job(request.workstation_device["id"])
            return jsonify({"job": job})
        except Exception as exc:
            app.logger.exception("Falha ao consultar fila Windows")
            return jsonify({"error": str(exc)}), 503

    @app.post("/v1/workstation/jobs/<job_id>/result")
    @require_device
    def workstation_result(job_id):
        body = request.get_json(silent=True) or {}
        try:
            result = finish_job(
                request.workstation_device["id"], job_id,
                body.get("result") or {}, bool(body.get("failed")),
            )
            return (jsonify(result), 200) if result else (jsonify({"error": "Tarefa não encontrada ou já encerrada."}), 404)
        except Exception as exc:
            app.logger.exception("Falha ao registrar resultado Windows")
            return jsonify({"error": str(exc)}), 503
