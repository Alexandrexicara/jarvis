"""Política local do braço Windows do Jarvis. Sem shell e sem execução arbitrária."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

MAX_FILE_BYTES = 1_000_000
MAX_OUTPUT_CHARS = 20_000
COMMAND_TIMEOUT_SECONDS = 300
BLOCKED_PARTS = {".git", ".env", ".venv", "venv", "__pycache__", "secrets", "credentials"}
BLOCKED_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
CHECKS = {
    "python-tests": ["python", "-m", "pytest", "-q"],
    "npm-build": ["npm", "run", "build"],
    "npm-lint": ["npm", "run", "lint"],
    "git-status": ["git", "status", "--short"],
    "git-diff-check": ["git", "diff", "--check"],
}


class PolicyError(ValueError):
    """Operação bloqueada pela política local."""


def workspace_root(value: str | Path) -> Path:
    root = Path(value).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise PolicyError("O workspace autorizado precisa ser uma pasta.")
    return root


def resolve_workspace_path(root: str | Path, relative_path: str) -> Path:
    base = workspace_root(root)
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise PolicyError("Informe um caminho relativo.")
    candidate = Path(relative_path)
    if candidate.is_absolute() or candidate.drive or any(part == ".." for part in candidate.parts):
        raise PolicyError("Caminho absoluto ou traversal não permitido.")
    if any(part.lower() in BLOCKED_PARTS for part in candidate.parts):
        raise PolicyError("Acesso a pasta protegida bloqueado.")
    if candidate.suffix.lower() in BLOCKED_SUFFIXES or candidate.name.lower() in {".env", ".env.local", ".env.production"}:
        raise PolicyError("Acesso a arquivo de segredo bloqueado.")
    target = (base / candidate).resolve(strict=False)
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise PolicyError("O caminho sai do workspace autorizado.") from exc
    return target


def read_project_file(root: str | Path, relative_path: str) -> str:
    target = resolve_workspace_path(root, relative_path)
    if not target.is_file():
        raise PolicyError("Arquivo não encontrado.")
    if target.stat().st_size > MAX_FILE_BYTES:
        raise PolicyError("Arquivo excede o limite de leitura.")
    return target.read_text(encoding="utf-8")


def write_project_file(root: str | Path, relative_path: str, content: str) -> str:
    target = resolve_workspace_path(root, relative_path)
    if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_FILE_BYTES:
        raise PolicyError("Conteúdo inválido ou acima do limite de 1 MB.")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Revalidar após criar diretórios para reduzir risco de symlink race.
    target = resolve_workspace_path(root, relative_path)
    target.write_text(content, encoding="utf-8")
    return str(target.relative_to(workspace_root(root)))


def run_approved_check(root: str | Path, check_name: str) -> dict:
    base = workspace_root(root)
    command = CHECKS.get(check_name)
    if command is None:
        raise PolicyError("Verificação não permitida.")
    # No Windows, npm normalmente é um arquivo .cmd. Executamos somente
    # a linha fixa previamente permitida; nunca interpolamos dados do pedido.
    if os.name == "nt" and check_name in {"npm-build", "npm-lint"}:
        command = ["cmd.exe", "/d", "/s", "/c", "npm run " + ("build" if check_name == "npm-build" else "lint")]
    safe_env = {
        key: value for key, value in os.environ.items()
        if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA", "PATHEXT"}
    }
    completed = subprocess.run(
        command,
        cwd=str(base),
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=COMMAND_TIMEOUT_SECONDS,
        env=safe_env,
        check=False,
    )
    return {
        "check": check_name,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-MAX_OUTPUT_CHARS:],
        "stderr": completed.stderr[-MAX_OUTPUT_CHARS:],
    }
