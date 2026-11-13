# -*- coding: utf-8 -*-
"""Cliente seguro e pequeno para a API Dealwork.ai.

Credenciais nunca devem ser gravadas no repositório. Use DEALWORK_API_KEY
como variável de ambiente ou o arquivo privado ~/.openwork/credentials.json.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

BASE_URL = os.getenv("DEALWORK_API_BASE") or os.getenv("DEALWORK_BASE_URL") or "https://dealwork.ai/api/v1"
BASE_URL = BASE_URL.rstrip("/")
CREDENTIALS_PATH = Path.home() / ".openwork" / "credentials.json"
TIMEOUT = 25


class DealworkError(RuntimeError):
    pass


class DealworkClient:
    def __init__(
        self,
        api_key: str | None = None,
        agent_id: str | None = None,
        hmac_secret: str | None = None,
        session: requests.Session | None = None,
    ):
        credentials = self._load_credentials()
        self.api_key = (
            api_key or os.getenv("DEALWORK_API_KEY") or credentials.get("apiKey", "")
        ).strip()
        self.agent_id = (
            agent_id or os.getenv("DEALWORK_AGENT_ID")
            or credentials.get("agentAccountId", "")
        ).strip()
        self.hmac_secret = (
            hmac_secret or os.getenv("DEALWORK_HMAC_SECRET")
            or credentials.get("hmacSecret", "")
        ).strip()
        if not self.agent_id or not self.hmac_secret:
            raise DealworkError(
                "Autenticação HMAC incompleta. Configure DEALWORK_AGENT_ID e "
                "DEALWORK_HMAC_SECRET no ambiente ou salve as credenciais em "
                f"{CREDENTIALS_PATH}. Não gere nem rotacione outra chave."
            )
        self.session = session or requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Jarvis-Dealwork-Agent/1.0",
        })

    @staticmethod
    def _load_credentials() -> dict[str, Any]:
        try:
            data = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    @staticmethod
    def save_credentials(data: dict[str, Any]) -> Path:
        api_key = data.get("apiKey")
        if not api_key or not data.get("hmacSecret") or not data.get("agentAccountId"):
            raise DealworkError(
                "A resposta do cadastro precisa conter agentAccountId, apiKey e hmacSecret."
            )
        CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            os.chmod(CREDENTIALS_PATH, 0o600)
        except OSError:
            pass
        return CREDENTIALS_PATH

    @staticmethod
    def onboard() -> dict[str, Any]:
        identity = os.getenv("DEALWORK_IDENTITY_KEY", "").strip()
        if len(identity) < 8:
            raise DealworkError(
                "Defina DEALWORK_IDENTITY_KEY com pelo menos 8 caracteres "
                "antes do cadastro. Use sempre o mesmo valor para recuperar a conta."
            )
        payload = {
            "autonomous": True,
            "agentName": os.getenv("DEALWORK_AGENT_NAME", "Jarvis Dev Agent"),
            "description": (
                "Agente de desenvolvimento com foco em Python, Flask, APIs REST, "
                "JavaScript, HTML/CSS, automação com Playwright, depuração e testes. "
                "Aceita tarefas compatíveis com essas ferramentas e requisitos verificáveis."
            ),
            "capabilityTags": [
                "python", "flask", "rest-api", "javascript", "html-css",
                "playwright", "automation", "debugging", "testing"
            ],
            "identityKey": identity,
        }
        response = requests.post(
            f"{BASE_URL}/agents/onboard",
            json=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        body = _decode_response(response)
        data = body.get("data", body)
        DealworkClient.save_credentials(data)
        # Não imprimir apiKey/hmacSecret no terminal nem nos logs.
        return {
            "saved_to": str(CREDENTIALS_PATH),
            "agentAccountId": data.get("agentAccountId"),
            "claimUrl": data.get("claimUrl"),
            "recovered": data.get("recovered", False),
        }

    def request(self, method: str, path: str, *, params=None, payload=None):
        # A assinatura usa exatamente o corpo transmitido. GET sempre assina
        # uma string vazia, conforme o contrato HMAC da Dealwork.
        body = (
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            if payload is not None else ""
        )
        timestamp = str(int(time.time()))
        signed_payload = f"{self.agent_id}{timestamp}{body}".encode("utf-8")
        signature = hmac.new(
            self.hmac_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "X-Agent-ID": self.agent_id,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        }
        response = self.session.request(
            method.upper(),
            f"{BASE_URL}/{path.lstrip('/')}",
            params=params,
            data=body if body else None,
            headers=headers,
            timeout=TIMEOUT,
        )
        return _decode_response(response)

    def list_jobs(self, *, page: int = 1, per_page: int = 20, sort: str = "recommended"):
        return self.request(
            "GET", "/jobs",
            params={"page": page, "per_page": min(max(per_page, 1), 50), "sort": sort},
        )

    def wallet_balance(self):
        return self.request("GET", "/wallet/balance")

    def my_contracts(self):
        return self.request("GET", "/contracts", params={"role": "worker", "per_page": 20})

    def submit_bid(
        self, job_id: str, proposed_amount: str, estimated_hours: float,
        proposal_text: str, *, confirm: bool = False
    ):
        if not confirm:
            raise DealworkError(
                "Proposta não enviada. Revise o trabalho e confirme explicitamente com --confirm."
            )
        if not job_id.strip() or not proposal_text.strip():
            raise DealworkError("job_id e proposalText são obrigatórios.")
        if float(proposed_amount) <= 0 or estimated_hours <= 0:
            raise DealworkError("Valor e horas estimadas devem ser positivos.")
        return self.request(
            "POST",
            f"/jobs/{quote(job_id, safe='')}/bids",
            payload={
                "proposedAmount": proposed_amount,
                "estimatedHours": estimated_hours,
                "proposalText": proposal_text,
            },
        )


def _decode_response(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        data = {"message": response.text[:1000]}
    if not response.ok:
        message = data.get("message") or data.get("error") or f"HTTP {response.status_code}"
        raise DealworkError(f"Dealwork respondeu {response.status_code}: {message}")
    return data if isinstance(data, dict) else {"data": data}


def main():
    parser = argparse.ArgumentParser(description="Integração Jarvis ↔ Dealwork.ai")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("onboard", help="Cadastrar o agente e guardar credenciais localmente")
    jobs = sub.add_parser("jobs", help="Consultar trabalhos disponíveis")
    jobs.add_argument("--page", type=int, default=1)
    jobs.add_argument("--per-page", type=int, default=20)
    sub.add_parser("balance", help="Consultar saldo da carteira")
    sub.add_parser("contracts", help="Consultar contratos como trabalhador")
    bid = sub.add_parser("bid", help="Enviar proposta após revisão humana")
    bid.add_argument("--job-id", required=True)
    bid.add_argument("--amount", required=True)
    bid.add_argument("--hours", required=True, type=float)
    bid.add_argument("--proposal", required=True)
    bid.add_argument("--confirm", action="store_true")

    args = parser.parse_args()
    try:
        if args.command == "onboard":
            result = DealworkClient.onboard()
        else:
            client = DealworkClient()
            if args.command == "jobs":
                result = client.list_jobs(page=args.page, per_page=args.per_page)
            elif args.command == "balance":
                result = client.wallet_balance()
            elif args.command == "contracts":
                result = client.my_contracts()
            else:
                result = client.submit_bid(
                    args.job_id, args.amount, args.hours, args.proposal,
                    confirm=args.confirm,
                )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (DealworkError, requests.RequestException) as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()
