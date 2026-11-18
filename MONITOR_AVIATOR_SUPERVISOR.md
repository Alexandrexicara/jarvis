# Jarvis — supervisor do Monitor Aviator

O módulo `monitor_aviator_supervisor.py` consulta a API existente do Monitor Aviator em intervalo configurável. É uma integração de observabilidade somente leitura.

## Configuração

No Render do Monitor API:
- `JARVIS_AGENT_TOKEN`: token aleatório exclusivo para a integração.
- Preserve `DATABASE_URL` e `COLLECTOR_TOKEN` já usados pelo Monitor.

No Render do Jarvis:
- `MONITOR_AVIATOR_API_URL`: URL HTTPS do Monitor API.
- `MONITOR_AVIATOR_AGENT_TOKEN`: exatamente o mesmo token criado no Monitor API.
- `MONITOR_AVIATOR_POLL_SECONDS`: 60 por padrão (mínimo 30).

Nunca coloque tokens em arquivos versionados, mensagens ou logs.

## Consulta

O supervisor começa quando o Jarvis recebe uma requisição e as duas variáveis de integração estão configuradas. O estado fica disponível em `GET /v1/monitor-aviator/status`, protegido por `JARVIS_ACCESS_KEY` ou `JARVIS_PROXY_KEY`.

O Jarvis classifica o Monitor como:
- `online`: API, PostgreSQL e token do coletor estão configurados.
- `degraded`: API respondeu, mas banco persistente ou autenticação do coletor não está pronto.
- `offline`: não foi possível consultar a API.
- `not_configured`: integração ainda não recebeu as variáveis.

Mudanças de estado são enviadas para a trilha de eventos da API do Monitor e persistidas no Neon.

## Limites atuais

- O supervisor verifica disponibilidade e configuração; não altera arquivos nem dados de rodadas.
- Não executa apostas nem tenta prever resultados.
- Não reinicia serviços Render, não faz deploy e não modifica os executáveis do usuário.
- A coleta automática real do Aviator ainda precisa ser validada separadamente; o painel existente também possui entrada manual.
- A delegação Proofable do agente Jarvis ainda está inativa. A integração não presume nem contorna essa autorização.
- O worker Windows do Jarvis continua sendo um componente separado, que precisa ser pareado e testado no computador autorizado antes de qualquer operação local.

Esta branch não deve ser implantada em produção antes da revisão, configuração dos segredos e teste de homologação.
