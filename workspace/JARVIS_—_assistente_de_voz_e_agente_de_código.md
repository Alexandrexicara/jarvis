# JARVIS — assistente de voz e agente de código

Este projeto disponibiliza uma interface web de voz em português, conversa com um modelo compatível com a API NVIDIA, pesquisa páginas públicas, edita arquivos dentro do workspace e executa comandos de desenvolvimento com proteção básica contra comandos destrutivos.

## Publicar no Render

1. Suba esta pasta para um repositório GitHub, mantendo `render.yaml` na raiz.
2. No Render, escolha **New > Blueprint** e selecione o repositório.
3. Cadastre `NVIDIA_API_KEY` como variável secreta. Opcionalmente, informe `NVIDIA_MODEL`.
4. Após o deploy, abra a URL pública e acrescente `/interface.html` se a rota inicial não for redirecionada automaticamente.
5. Confirme o funcionamento em `/api/health`, que deve retornar `ok: true`.

O servidor usa automaticamente a variável `PORT` fornecida pelo Render. Não coloque chaves reais no GitHub; use as Environment Variables do Render. O arquivo `index.html` foi removido conforme solicitado; a rota `/` serve `interface.html` diretamente.

## Executar localmente

### Linux/macOS

```bash
cd jarvis/Jarvis-Completo
cp .env.example .env
# edite .env e preencha NVIDIA_API_KEY
python3 jarvis.py
```

Abra `http://127.0.0.1:8000/`.

### Windows

Execute `jarvis/INICIAR-JARVIS.bat` e abra `http://127.0.0.1:8000/`.

## Usar com VS Code

Abra a pasta `workspace` no VS Code, não apenas a pasta `Jarvis-Completo`. O inicializador Windows já aponta `JARVIS_WORKSPACE` para essa pasta quando ela existe. O projeto de teste fica em `workspace/demo-site`.

1. Execute o JARVIS e mantenha o servidor aberto.
2. Abra `workspace` no VS Code.
3. Diga ou envie: “Crie um website completo com login e banco de dados dentro de `demo-site`”.
4. O agente deve listar/ler arquivos, escrever o código, testar e informar o que mudou.
5. No terminal do VS Code, entre na pasta criada e execute os comandos do README do projeto, por exemplo `pytest -q` e `python app.py`.
6. Depois peça melhorias específicas: “adicione recuperação de senha”, “crie uma API”, “corrija o teste que falhou”.

O VS Code é o editor e terminal; o JARVIS é o agente que altera os arquivos. Antes de pedir mudanças grandes, salve o projeto em Git para poder revisar ou desfazer alterações.

## Recursos robustos implementados

- **Plano de projeto:** o agente pode salvar um plano em `.jarvis/plan.md` antes de começar um app ou website.
- **Backup automático:** antes de editar arquivo existente ou executar comando aprovado, cria uma cópia em `.jarvis/backups/`.
- **Auditoria:** registra ações em `.jarvis/audit.jsonl`, incluindo arquivos escritos, comandos, backups e aprovações.
- **Aprovação:** comandos de maior risco, como instalação de pacotes, `git push`, `git reset --hard`, `sudo` e remoções, ficam bloqueados até confirmação. Para ambiente pessoal totalmente automático, defina `JARVIS_AUTO_APPROVE=1`, somente se você aceitar o risco.
- **Git:** o agente pode consultar o estado do repositório antes de alterar o projeto.
- **Testes:** o agente é instruído a validar sintaxe, executar testes e corrigir falhas quando possível.
- **Status:** `/api/status` mostra workspace, modo de aprovação e ação pendente.

Uma ação aprovada pode ser executada em `/api/approve` com `{"approved": true}`. A interface web mostra uma confirmação quando o agente solicita essa autorização.

## Modo descanso e fala limpa

Diga **“Jarvis, descansar”** para ele continuar ouvindo, mas não responder por voz. Nesse modo, falas comuns são ignoradas silenciosamente. Diga apenas **“Jarvis”** para reativá-lo; ele responderá que voltou a ouvir. Dizer **“Jarvis, descansar”** novamente entra no modo silencioso.

Antes de falar, a interface remove emojis, asteriscos, markdown, crases, URLs e símbolos que não fazem sentido na leitura. O texto visual do chat continua podendo mostrar a resposta original.

## Capacidades

- Conversa geral e contexto das últimas mensagens.
- Comandos locais de hora, data, Google, YouTube e pesquisa.
- Agente de programação com `list_files`, `read_file`, `write_file`, `run_command` e `fetch_url`.
- Criação e alteração de projetos dentro do workspace definido por `JARVIS_WORKSPACE`.
- Criação real de apps, websites, APIs e scripts: o agente cria os arquivos, adiciona instruções e executa validações quando possível.
- Leitura de páginas públicas HTTP/HTTPS pelo agente.
- Pesquisa web pública quando você pedir explicitamente para pesquisar, buscar ou procurar algo; o agente recebe títulos, links e trechos para responder.

E-mail, redes sociais, pagamentos e publicação automática não são ativados sem as respectivas APIs, OAuth e autorização do proprietário. O agente não simula envios nem publica conteúdo sem uma integração configurada.

### Sobre o acesso à internet

Sim, depois de publicado com uma `NVIDIA_API_KEY`, o servidor pode acessar a internet para pesquisa pública. Ele pode pesquisar resultados públicos e abrir URLs públicas que você pedir, inclusive sites encontrados em buscadores. Isso não é acesso ilimitado a qualquer site: páginas que exigem login, CAPTCHA, assinatura, bloqueio de robôs, conteúdo privado ou aplicativos sem API pública não ficam disponíveis automaticamente. Para uma resposta atualizada, diga por exemplo: “JARVIS, pesquise na internet sobre ...”.

O JARVIS não deve burlar autenticação, CAPTCHA, paywall ou restrições de uma plataforma. Para e-mail, redes sociais, GitHub, Render e outros serviços privados, é necessário configurar a API/OAuth oficial e a permissão correspondente.
