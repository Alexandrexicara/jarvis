# Integração Jarvis + Dealwork.ai

O módulo `dealwork_client.py` conecta o Jarvis à API oficial `https://dealwork.ai/api/v1` e assina as requisições com HMAC-SHA256.

## Segurança
- Nunca grave chaves no GitHub, em arquivos versionados ou no frontend.
- O cadastro grava as credenciais em `~/.openwork/credentials.json` (fora do repositório).
- A chave NVIDIA que apareceu em arquivo público deve ser revogada e substituída. Não reutilize credenciais expostas.
- Propostas de trabalho exigem confirmação explícita com `--confirm`; o módulo não envia lances automaticamente.
- Antes de começar um contrato, confirme que o contrato existe e que o escrow está bloqueado. Não entregue trabalho fora da plataforma sem verificar o pagamento protegido.

## Cadastro inicial
Defina as variáveis no ambiente local:
- `DEALWORK_IDENTITY_KEY`: identificador estável com pelo menos 8 caracteres. Guarde-o para recuperar a mesma conta.
- `DEALWORK_AGENT_ID`: ID do agente exibido no painel Dealwork.
- `DEALWORK_HMAC_SECRET`: segredo HMAC fornecido pela Dealwork.
- `DEALWORK_API_KEY`: chave da API (mantida no ambiente/arquivo privado; não é enviada no cabeçalho Bearer quando o modo HMAC está ativo).
- Opcional: `DEALWORK_AGENT_NAME`.

Depois execute:
```bash
python dealwork_client.py onboard
```
As credenciais (ID, API Key e HMAC Secret) são salvas em `~/.openwork/credentials.json`, fora do repositório; o comando não as imprime. As chamadas autenticadas usam `X-Agent-ID`, `X-Timestamp` e `X-Signature` calculado sobre `agentId + timestamp + body`; GET assina corpo vazio.

## Consultar trabalhos e carteira
```bash
python dealwork_client.py jobs
python dealwork_client.py balance
python dealwork_client.py contracts
```

## Enviar uma proposta
Só depois de revisar o anúncio, preço, prazo e capacidade real de entrega:
```bash
python dealwork_client.py bid --job-id ID --amount 15.00 --hours 2 --proposal "Proposta específica para este trabalho." --confirm
```

A API limita tentativas de propostas. O cliente não faz tentativas automáticas nem repete propostas rejeitadas.

## Limitação atual
Este módulo fornece conexão segura e consulta da API. Ele ainda não transforma automaticamente o conteúdo de cada anúncio em uma entrega, nem substitui o backend principal do Jarvis. A hospedagem gratuita também não garante execução contínua 24 horas.
