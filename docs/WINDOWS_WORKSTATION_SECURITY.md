# Jarvis — braço de desenvolvimento Windows (preparação)

## Objetivo

Adicionar ao Jarvis uma capacidade local de desenvolvimento no Windows, mantendo intactas as rotas, credenciais e o heartbeat existentes do Dealwork. Esta implementação é isolada e não deve ser mesclada nem publicada no Render antes dos testes.

## Arquitetura prevista

- Jarvis hospedado continua sendo o agente principal e mantém a integração Dealwork.
- Um processo local leve (worker) roda no Windows, sob a conta do usuário, e inicia a conexão de saída com o servidor.
- O worker só aceita tarefas do tipo explicitamente permitido; não expõe PowerShell, CMD, SSH ou uma porta de controle pública.
- O worker trabalha somente em diretórios de projetos que o usuário autorizar explicitamente.
- O worker devolve ao Jarvis o resultado, logs resumidos e estado dos testes.

## Segurança obrigatória

1. Autenticação por token de dispositivo aleatório, armazenado fora do repositório e com possibilidade de revogação.
2. Transporte HTTPS; conexão iniciada pelo Windows (sem abrir porta no roteador).
3. Validação de caminho real e bloqueio de traversal, links simbólicos que escapem da pasta autorizada e caminhos de sistema.
4. Lista permitida de operações: listar arquivos, ler arquivos dentro do workspace, criar/editar arquivos, executar testes/builds previamente aprovados.
5. Comandos executados sem shell=True; argumentos separados, diretório de trabalho fixo e timeout/limite de saída.
6. Bloqueio por padrão para exclusão, instalação global, alteração de variáveis de ambiente, leitura de segredos, comandos administrativos e publicação/deploy.
7. Aprovação humana obrigatória para operações destrutivas, acesso a credenciais e deploy.
8. Redação de tokens, chaves e valores de .env nos logs e nas respostas.
9. Auditoria local de cada ação: horário, tarefa, arquivos afetados, comando permitido e código de saída.
10. O worker deve parar de aceitar tarefas se a autenticação falhar ou se o servidor enviar instrução desconhecida.

## Plano de entrega

- Fase A: revisar o contrato do worker e preservar as rotas Dealwork existentes.
- Fase B: implementar o worker local e testes unitários de caminhos, permissões, autenticação e limites.
- Fase C: implementar a fila de tarefas do braço Windows em armazenamento separado da fila de tarefas de IA existente.
- Fase D: preparar instalador/atalho simples para Windows 10 e instruções de pareamento.
- Fase E: testar localmente sem Render; após a liberação do serviço, publicar em janela controlada e testar health check, heartbeat Dealwork e o braço Windows.

## Critérios de aceite

- As rotas e o heartbeat Dealwork continuam presentes e sem alteração funcional.
- Nenhuma execução arbitrária de shell a partir de mensagem do modelo.
- O worker só acessa pastas explicitamente autorizadas.
- Testes negativos comprovam bloqueio de caminhos fora do workspace e comandos não permitidos.
- O deploy só ocorre após confirmação do usuário e validação da branch.
