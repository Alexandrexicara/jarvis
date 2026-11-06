import os
import secrets
from functools import wraps

import requests
from flask import Flask, Response, jsonify, request

from task_queue import (
    cancel_task, enqueue_tasks, get_task, get_tasks, get_tasks_paused, set_tasks_paused, start_workers, task_stats
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response


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


@app.post("/v1/audio/speech")
@require_access_key
def text_to_speech():
    if not ELEVENLABS_API_KEY:
        return jsonify({"error": {"message": "ELEVENLABS_API_KEY não configurada no Render."}}), 503
    body = request.get_json(silent=True) or {}
    text = str(body.get("input") or body.get("text") or "").strip()
    if not text:
        return jsonify({"error": {"message": "Informe o texto em 'input'."}}), 400
    if len(text) > 5000:
        return jsonify({"error": {"message": "O texto deve ter no máximo 5.000 caracteres."}}), 400
    try:
        upstream = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "language_code": "pt",
                "voice_settings": {
                    "stability": 0.62,
                    "similarity_boost": 0.82,
                    "style": 0.25,
                    "use_speaker_boost": True
                }
            },
            timeout=60
        )
        if not upstream.ok:
            app.logger.warning("ElevenLabs TTS retornou HTTP %s", upstream.status_code)
            return jsonify({"error": {"message": "A ElevenLabs recusou a geração de voz (HTTP %s)." % upstream.status_code}}), 502
        return (upstream.content, 200, {
            "Content-Type": "audio/mpeg",
            "Cache-Control": "no-store"
        })
    except requests.RequestException:
        app.logger.exception("Falha ao consultar ElevenLabs TTS")
        return jsonify({"error": {"message": "Não foi possível conectar à ElevenLabs."}}), 502


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
        "compatible": "OpenAI-compatible API (OpenClaw/custom provider)",
        "features": ["chat completions", "persistent multi-task queue", "parallel workers"],
        "endpoints": ["/api/health", "/v1/models", "/v1/chat/completions", "/v1/tasks", "/v1/tasks/<id>", "/v1/tasks/stats"]
    })


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "jarvis-free-ai-bridge"})


@app.get("/v1/models")
@require_access_key
def models():
    return jsonify({"object": "list", "data": [{"id": NVIDIA_MODEL, "object": "model", "owned_by": "nvidia-nim"}]})


@app.post("/v1/chat/completions")
@require_access_key
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


@app.post("/v1/audio/speech")
@require_access_key
def audio_speech():
    if not ELEVENLABS_API_KEY:
        return jsonify({"error": {"message": "ELEVENLABS_API_KEY não configurada no Render."}}), 503
    body = request.get_json(silent=True) or {}
    text = str(body.get("input") or body.get("text") or "").strip()
    if not text:
        return jsonify({"error": {"message": "Envie o texto em 'input'."}}), 400
    if len(text) > 5000:
        return jsonify({"error": {"message": "O texto excede o limite de 5.000 caracteres por fala."}}), 413
    try:
        upstream = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"},
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.52, "similarity_boost": 0.78, "style": 0.25, "use_speaker_boost": True}
            },
            params={"output_format": "mp3_44100_128"},
            timeout=90
        )
        return Response(
            upstream.content,
            status=upstream.status_code,
            content_type=upstream.headers.get("Content-Type", "audio/mpeg")
        )
    except requests.RequestException as exc:
        app.logger.exception("Falha na síntese ElevenLabs")
        return jsonify({"error": {"message": f"Falha ao gerar voz ElevenLabs: {str(exc)}"}}), 502


@app.post("/v1/tasks/control")
@require_access_key
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
@require_access_key
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
@require_access_key
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
@require_access_key
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
@require_access_key
def tasks_stats():
    try:
        return jsonify(task_stats())
    except Exception as exc:
        return jsonify({"error": {"message": str(exc)}}), 503


@app.get("/v1/tasks/<task_id>")
@require_access_key
def task_detail(task_id):
    try:
        task = get_task(task_id)
        return (jsonify(task), 200) if task else (jsonify({"error": {"message": "Tarefa não encontrada."}}), 404)
    except Exception as exc:
        return jsonify({"error": {"message": str(exc)}}), 503


@app.delete("/v1/tasks/<task_id>")
@require_access_key
def task_cancel(task_id):
    try:
        cancelled = cancel_task(task_id)
        return jsonify({"cancelled": cancelled, "message": "Tarefa cancelada." if cancelled else "Só é possível cancelar tarefas pendentes."})
    except Exception as exc:
        return jsonify({"error": {"message": str(exc)}}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
