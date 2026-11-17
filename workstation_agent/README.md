# Worker local do Jarvis — Windows 10/11

## Preparação (não executar antes do pareamento)

1. Baixe/clique em Code > Download ZIP da branch de desenvolvimento.
2. Extraia em uma pasta local, por exemplo E:\\Jarvis-Worker.
3. Copie .env.example para .env e preencha os três campos: URL HTTPS do Jarvis, token de dispositivo e pasta de projetos autorizada.
4. Execute INICIAR-WORKER.bat.

## Segurança

- O worker só inicia conexão HTTPS de saída; não abre portas no computador.
- O token é individual por computador e pode ser revogado pelo administrador.
- Nunca compartilhe o arquivo .env nem publique seu token.
- O worker não aceita comandos PowerShell/CMD livres.
- Operações disponíveis inicialmente: listar arquivos, ler/criar/editar arquivos no workspace e executar verificações nomeadas (pytest, npm build, npm lint, git status, git diff --check).
- Arquivos .env, chaves privadas, pastas .git, venv, node_modules e diretórios de credenciais são bloqueados.
- O deploy e a exclusão de arquivos não são operações disponíveis.

## Estado

Este pacote é código em preparação. Ainda precisa de testes integrados e revisão antes de ser usado com o serviço hospedado.
