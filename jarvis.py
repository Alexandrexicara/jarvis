import os
import secrets
import time
from collections import defaultdict, deque
from functools import wraps

import requests
from flask import Flask, Response, jsonify, request

from dealwork_client import register_routes as register_dealwork_routes
from dealwork_heartbeat import start_heartbeat, register_heartbeat_route

from task_queue import (
    cancel_task, enqueue_tasks, get_task, get_tasks, get_tasks_paused, set_tasks_paused, start_workers, task_stats
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

FRONTEND_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in os.getenv("JARVIS_FRONTEND_ORIGINS", "https://jarvis-br.netlify.app").split(",")
    if origin.strip()
}
_FRONTEND_REQUESTS = defaultdict(deque)

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "").rstrip("/")
    if origin in FRONTEND_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        response.headers["Access-Control-Max-Age"] = "86400"
    return response

def require_frontend(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        origin = request.headers.get("Origin", "").rstrip("/")
        if origin not in FRONTEND_ORIGINS:
            return jsonify({"error": {"message": "Origem do painel Jarvis não autorizada."}}), 403
        now = time.time()
        client = request.remote_addr or "unknown"
        recent = _FRONTEND_REQUESTS[client]
        while recent and now - recent[0] > 60:
            recent.popleft()
        if len(recent) >= 60:
            return jsonify({"error": {"message": "Muitas solicitações. Aguarde um minuto."}}), 429
        recent.append(now)
        return fn(*args, **kwargs)
    return wrapper


NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "8BWp4523yEDDjOJi73mz")

JARVIS_ACCESS_KEY = os.getenv("JARVIS_ACCESS_KEY", "")
JARVIS_PROXY_KEY = os.getenv("JARVIS_PROXY_KEY", "")


def require_access_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        valid_keys = [key for key in (JARVIS_ACCESS_KEY, JARVIS_PROXY_KEY) if key]
        if not valid_keys:
            return jsonify({"error": {"message": "Nenhuma chave interna configurada no Render."}}), 503
        supplied = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not any(secrets.compare_digest(supplied, key) for key in valid_keys):
            return jsonify({"error": {"message": "Não autorizado."}}), 401
        return fn(*args, **kwargs)
    return wrapper


@app.before_request
def boot_task_workers():
    if request.path.startswith("/v1/tasks"):
        try:
            start_workers()
        except Exception:
            app.logger.exception("Não foi possível iniciar os workers de tarefas")


@app.get("/")
def index():
    return jsonify({
        "name": "Jarvis Free AI Bridge",
        "status": "online",
        "compatible": "API nativa do Jarvis",
        "features": ["chat completions", "fila persistente PostgreSQL", "workers paralelos", "heartbeat DealworkAI"],
        "endpoints": ["/api/health", "/v1/models", "/v1/chat/completions", "/v1/tasks", "/v1/tasks/<id>", "/v1/tasks/stats"]
    })


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "jarvis-free-ai-bridge"})


@app.get("/v1/models")
@require_frontend
def models():
    return jsonify({"object": "list", "data": [{"id": NVIDIA_MODEL, "object": "model", "owned_by": "nvidia-nim"}]})


@app.post("/v1/chat/completions")
@require_frontend
def chat_completions():
    if not NVIDIA_API_KEY:
        return jsonify({"error": {"message": "NVIDIA_API_KEY não configurada no Render."}}), 503
    body = request.get_json(silent=True) or {}
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        return jsonify({"error": {"message": "Envie messages como uma lista não vazia."}}), 400
    payload = {
        "model": body.get("model") or NVIDIA_MODEL,
        "messages": messages,
        "temperature": body.get("temperature", 0.2),
        "max_tokens": body.get("max_tokens", 1200),
        "stream": False
    }
    try:
        upstream = requests.post(
            f"{NVIDIA_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=120
        )
        return (upstream.content, upstream.status_code, {"Content-Type": upstream.headers.get("Content-Type", "application/json")})
    except requests.RequestException as exc:
        return jsonify({"error": {"message": f"Falha ao consultar NVIDIA NIM: {str(exc)}"}}), 502


def _elevenlabs_male_voice_candidates(api_key):
    """Lista somente vozes masculinas que a própria chave consegue acessar."""
    candidates = []
    seen = set()
    headers = {"xi-api-key": api_key, "Accept": "application/json"}
    endpoints = (
        "https://api.elevenlabs.io/v2/voices?voice_type=non-community&page_size=100&include_total_count=false",
        "https://api.elevenlabs.io/v2/voices?voice_type=default&page_size=100&include_total_count=false",
    )
    for endpoint in endpoints:
        try:
            listed = requests.get(endpoint, headers=headers, timeout=20)
            if not listed.ok:
                app.logger.warning("ElevenLabs voice discovery HTTP %s", listed.status_code)
                continue
            for voice in listed.json().get("voices", []):
                voice_id = str(voice.get("voice_id") or "").strip()
                labels = voice.get("labels") or {}
                gender = str(labels.get("gender") or "").strip().lower()
                if not voice_id or voice_id in seen or gender not in ("male", "masculine"):
                    continue
                seen.add(voice_id)
                candidates.append({
                    "id": voice_id,
                    "name": str(voice.get("name") or voice_id),
                    "category": str(voice.get("category") or ""),
                })
        except (requests.RequestException, ValueError, TypeError) as exc:
            app.logger.warning("ElevenLabs voice discovery failed: %s", str(exc)[:300])
    # Vozes geradas/da própria conta vêm antes das vozes padrão.
    candidates.sort(key=lambda item: 0 if item["category"] == "generated" else 1)
    return candidates


@app.post("/v1/audio/speech")
@require_frontend
def audio_speech():
    if not ELEVENLABS_API_KEY:
        return jsonify({"error": {"message": "ELEVENLABS_API_KEY não configurada no Render."}}), 503
    body = request.get_json(silent=True) or {}
    text = str(body.get("input") or body.get("text") or "").strip()
    if not text:
        return jsonify({"error": {"message": "Envie o texto em 'input'."}}), 400
    if len(text) > 5000:
        return jsonify({"error": {"message": "O texto excede o limite de 5.000 caracteres por fala."}}), 413

    candidates = _elevenlabs_male_voice_candidates(ELEVENLABS_API_KEY)
    if not candidates:
        return jsonify({"error": {"message": "A chave ElevenLabs não retornou nenhuma voz masculina liberada para uso pela API. O Jarvis deve usar a voz masculina alternativa do navegador."}}), 503

    last_status = 402
    last_detail = "Nenhuma voz masculina disponível foi aceita pela ElevenLabs."
    for candidate in candidates:
        try:
            upstream = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{candidate['id']}",
                headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"},
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.52, "similarity_boost": 0.78, "style": 0.25, "use_speaker_boost": True}
                },
                params={"output_format": "mp3_44100_128"},
                timeout=90
            )
            if upstream.ok and upstream.content:
                app.logger.info("ElevenLabs TTS success with accessible male voice: %s", candidate["name"])
                return Response(upstream.content, status=200, content_type=upstream.headers.get("Content-Type", "audio/mpeg"))
            last_status = upstream.status_code
            try:
                error_data = upstream.json()
            except ValueError:
                error_data = {"message": upstream.text[:500]}
            detail = error_data.get("detail") if isinstance(error_data, dict) else None
            if isinstance(detail, dict):
                detail = detail.get("message") or detail.get("status")
            last_detail = str(detail or error_data.get("message") or "A ElevenLabs recusou esta voz.")[:500]
            app.logger.warning("ElevenLabs voice %s unavailable (HTTP %s): %s", candidate["name"], last_status, last_detail)
            # 402/404/422 podem indicar voz não liberada ou incompatível; testar a próxima.
            if last_status not in (402, 404, 422):
                break
        except requests.RequestException as exc:
            last_status = 502
            last_detail = str(exc)[:500]
            app.logger.warning("ElevenLabs request failed for %s: %s", candidate["name"], last_detail)

    return jsonify({"error": {"message": "Não encontrei uma voz masculina da ElevenLabs liberada para esta chave. " + last_detail, "provider_status": last_status}}), 502 if last_status not in (402, 404, 422) else 503


@app.post("/v1/tasks/control")
@require_frontend
def control_tasks():
    body = request.get_json(silent=True) or {}
    if "paused" not in body or not isinstance(body["paused"], bool):
        return jsonify({"error": {"message": "Envie 'paused' como true ou false."}}), 400
    try:
        paused = set_tasks_paused(body["paused"])
        return jsonify({
            "paused": paused,
            "message": "Fila de tarefas pausada." if paused else "Fila de tarefas retomada."
        })
    except Exception as exc:
        app.logger.exception("Falha ao alterar controle da fila")
        return jsonify({"error": {"message": str(exc)}}), 503


@app.post("/v1/tasks")
@require_frontend
def create_tasks():
    body = request.get_json(silent=True) or {}
    items = body.get("tasks")
    if items is None:
        items = [body]
    if not isinstance(items, list) or not items:
        return jsonify({"error": {"message": "Envie uma tarefa ou uma lista em 'tasks'."}}), 400
    if len(items) > 500:
        return jsonify({"error": {"message": "Máximo de 500 tarefas por envio. Você pode enviar novos lotes depois."}}), 400
    try:
        created = enqueue_tasks(items)
        start_workers()
        return jsonify({"created": len(created), "tasks": created}), 202
    except ValueError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400
    except Exception as exc:
        app.logger.exception("Falha ao adicionar tarefas")
        return jsonify({"error": {"message": str(exc)}}), 503


@app.route("/v1/tasks/control", methods=["GET", "POST"])
@require_frontend
def task_control():
    if request.method == "GET":
        return jsonify({"paused": get_tasks_paused()})
    body = request.get_json(silent=True) or {}
    paused = body.get("paused")
    if not isinstance(paused, bool):
        return jsonify({"error": {"message": "Envie paused como true ou false."}}), 400
    current = set_tasks_paused(paused)
    return jsonify({
        "paused": current,
        "message": "Fila pausada. As tarefas pendentes aguardam." if current else "Fila retomada. O Jarvis voltou a processar as tarefas."
    })


@app.get("/v1/tasks")
@require_frontend
def list_tasks():
    try:
        limit = request.args.get("limit", "100")
        status = request.args.get("status")
        if status and status not in {"pending", "running", "completed", "failed", "cancelled"}:
            return jsonify({"error": {"message": "Status inválido."}}), 400
        return jsonify({"tasks": get_tasks(limit, status)})
    except Exception as exc:
        return jsonify({"error": {"message": str(exc)}}), 503


@app.get("/v1/tasks/stats")
@require_frontend
def tasks_stats():
    try:
        return jsonify(task_stats())
    except Exception as exc:
        return jsonify({"error": {"message": str(exc)}}), 503


@app.get("/v1/tasks/<task_id>")
@require_frontend
def task_detail(task_id):
    try:
        task = get_task(task_id)
        return (jsonify(task), 200) if task else (jsonify({"error": {"message": "Tarefa não encontrada."}}), 404)
    except Exception as exc:
        return jsonify({"error": {"message": str(exc)}}), 503


@app.delete("/v1/tasks/<task_id>")
@require_frontend
def task_cancel(task_id):
    try:
        cancelled = cancel_task(task_id)
        return jsonify({"cancelled": cancelled, "message": "Tarefa cancelada." if cancelled else "Só é possível cancelar tarefas pendentes."})
    except Exception as exc:
        return jsonify({"error": {"message": str(exc)}}), 503


register_dealwork_routes(app, require_access_key, require_frontend)
register_heartbeat_route(app, require_access_key)
start_heartbeat()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
