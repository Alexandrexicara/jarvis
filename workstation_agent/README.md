# Worker local do Jarvis — Windows 10/11

## Preparação (somente após a liberação do serviço hospedado)

1. Baixe a branch `feat/jarvis-windows-workstation` pelo GitHub (Code > Download ZIP).
2. Extraia em uma pasta local, por exemplo `E:\\Jarvis-Worker`.
3. Copie `.env.example` para `.env` e preencha URL HTTPS do Jarvis, token individual e pasta de projetos autorizada.
4. Execute `INICIAR-WORKER.bat`.

## Segurança e limites atuais

- O worker inicia apenas conexões HTTPS de saída; não abre portas no computador.
- Cada computador tem token individual, armazenado no banco somente como hash e revogável pelo administrador.
- O token é exibido uma única vez no pareamento. Nunca compartilhe o arquivo `.env`.
- Não há execução livre de PowerShell/CMD, instalação de programas, exclusão de arquivos, deploy ou controle remoto da tela.
- Operações disponíveis: listar, ler e escrever arquivos dentro do workspace e executar verificações nomeadas.
- Escritas e verificações exigem aprovação explícita no pedido (`approved: true`), além da chave administrativa da API.
- `.env`, chaves privadas, pastas `.git`, ambientes virtuais, `node_modules` e diretórios de credenciais são bloqueados.
- Resultados acima de 100 KB são rejeitados integralmente para não gravar JSON truncado/corrompido.
- As verificações npm ainda precisam de validação em Windows real; o primeiro teste local deve começar por `git-status` e `python-tests`.

## Estado

Implementação preliminar em branch isolada. Não foi implantada nem testada contra o Render; requer CI e teste integrado antes de uso real.
