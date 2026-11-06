import os
import secrets
from functools import wraps

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
JARVIS_ACCESS_KEY = os.getenv("JARVIS_ACCESS_KEY", "")

def require_access_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Require a private key for all AI endpoints; health stays public for Render.
        if not JARVIS_ACCESS_KEY:
            return jsonify({"error": {"message": "JARVIS_ACCESS_KEY não configurada no Render."}}), 503
        supplied = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not secrets.compare_digest(supplied, JARVIS_ACCESS_KEY):
            return jsonify({"error": {"message": "Não autorizado."}}), 401
        return fn(*args, **kwargs)
    return wrapper

@app.get("/")
def index():
    return jsonify({
        "name": "Jarvis Free AI Bridge",
        "status": "online",
        "compatible": "OpenAI-compatible API (OpenClaw/custom provider)",
        "endpoints": ["/api/health", "/v1/models", "/v1/chat/completions"]
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
        content_type = upstream.headers.get("Content-Type", "application/json")
        return (upstream.content, upstream.status_code, {"Content-Type": content_type})
    except requests.RequestException as exc:
        return jsonify({"error": {"message": f"Falha ao consultar NVIDIA NIM: {str(exc)}"}}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
