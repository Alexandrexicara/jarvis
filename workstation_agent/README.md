# Worker local do Jarvis — Windows 10/11

## Preparação (somente após a liberação do serviço hospedado)

1. Baixe a branch `feat/jarvis-windows-workstation` pelo GitHub (Code > Download ZIP).
2. Extraia em uma pasta local, por exemplo `E:\\Jarvis-Worker`.
3. Copie `.env.example` para `.env` e preencha URL HTTPS do Jarvis, token individual e pasta de projetos autorizada.
4. Execute `INICIAR-WORKER.bat`.

## Segurança e autonomia

- O worker inicia apenas conexões HTTPS de saída; não abre portas no computador.
- Cada computador tem token individual, armazenado no banco somente como hash e revogável pelo administrador.
- O token é exibido uma única vez no pareamento. Nunca compartilhe o arquivo `.env`.
- Monitoramento, leitura e verificações nomeadas podem ser executados automaticamente.
- A autocorreção fica desligada por padrão. Para habilitá-la, configure `JARVIS_AUTO_REPAIR_ENABLED=true` localmente e liste somente as pastas autorizadas em `JARVIS_AUTO_EDIT_PATHS` (ex.: `src,tests`).
- A política local bloqueia caminhos fora do workspace, traversal, symlinks externos, segredos e diretórios protegidos.
- Edição usa gravação atômica para reduzir o risco de arquivo parcialmente gravado.
- O limite de tentativas de reparo é configurável, mas nunca passa de 3 por ciclo.
- Não há execução livre de PowerShell/CMD, instalação de programas, exclusão de arquivos, deploy ou controle remoto da tela.
- Deploy, exclusão de dados, credenciais, segredos e operações financeiras continuam exigindo autorização específica.
- Resultados acima de 100 KB são rejeitados integralmente para não gravar JSON truncado/corrompido.
- As verificações npm ainda precisam de validação em Windows real; o primeiro teste local deve começar por `git-status` e `python-tests`.

## Estado

Esta é a camada de política e execução local, não um ciclo completo de autocorreção por IA. A geração de patch, validação do diff, auditoria persistente, retentativas coordenadas e rollback ainda precisam ser integrados e testados antes de habilitar reparos em projetos reais. Não foi implantada nem testada contra o Render.
