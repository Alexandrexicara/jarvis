"""Regras explícitas para o ciclo autônomo do Jarvis.

Monitoramento e diagnóstico são permitidos por padrão. Edição exige pastas
explicitamente autorizadas na máquina do worker. Deploy, segredos, exclusões
e operações financeiras nunca são autorizados por esta política.
"""
from __future__ import annotations

import os

READ_ONLY_ACTIONS = frozenset({"list_files", "read_file", "run_check"})
PROTECTED_ACTIONS = frozenset({
    "deploy", "delete", "delete_data", "manage_secrets",
    "change_credentials", "financial_operation", "production_write",
})


def max_repair_attempts() -> int:
    try:
        return max(0, min(int(os.getenv("JARVIS_AUTO_REPAIR_MAX_ATTEMPTS", "2")), 3))
    except (TypeError, ValueError):
        return 2


def auto_repair_enabled() -> bool:
    return os.getenv("JARVIS_AUTO_REPAIR_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def classify_action(action: str) -> str:
    """Retorna auto, restricted ou approval_required; nunca concede permissões."""
    if action in READ_ONLY_ACTIONS:
        return "auto"
    if action in PROTECTED_ACTIONS:
        return "approval_required"
    if action == "write_file":
        return "restricted"
    return "approval_required"


def repair_may_run(attempt: int) -> bool:
    """Limita tentativas e mantém autocorreção desligada até habilitação explícita."""
    return auto_repair_enabled() and 0 <= attempt < max_repair_attempts()
