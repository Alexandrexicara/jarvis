






























import json
import os
import re
import shutil
import subprocess
import threading
from datetime import datetime, timezone
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# ============================================================
# JARVIS - CONFIGURAÇÃO
# ============================================================

PORTA = int(os.environ.get("PORT", os.environ.get("JARVIS_PORT", "8000")))

BASE_DIR = Path(__file__).resolve().parent

PADRAO_WORKSPACE = BASE_DIR.parent.parent / "workspace"

WORKSPACE = Path(
    os.environ.get(
        "JARVIS_WORKSPACE",
        str(PADRAO_WORKSPACE if PADRAO_WORKSPACE.exists() else BASE_DIR)
    )
).resolve()

NVIDIA_BASE_URL = os.environ.get(
    "NVIDIA_BASE_URL",
    "https://integrate.api.nvidia.com/v1"
).rstrip("/")

MODELO_PREFERIDO = os.environ.get("NVIDIA_MODEL", "").strip()

AUTO_APROVAR_COMANDOS = os.environ.get(
    "JARVIS_AUTO_APPROVE",
    "0"
).lower() in {"1", "true", "yes", "sim"}

CONTROLE_DIR = WORKSPACE / ".jarvis"
BACKUP_DIR = CONTROLE_DIR / "backups"
AUDIT_FILE = CONTROLE_DIR / "audit.jsonl"

# ============================================================
# PLAYWRIGHT / NAVEGADOR
# ============================================================

BROWSER_DISPONIVEL = False
BROWSER_ERRO_IMPORT = ""

try:
    from browser_controller import get_browser

    BROWSER_DISPONIVEL = True
except Exception as erro:
    BROWSER_ERRO_IMPORT = str(erro)
    print("DEBUG: browser_controller indisponível:", erro)


def navegador():
    if not BROWSER_DISPONIVEL:
        raise RuntimeError(
            "Controle de navegador indisponível. "
            f"Erro ao carregar browser_controller: {BROWSER_ERRO_IMPORT}"
        )

    perfil = CONTROLE_DIR / "browser-profile"
    perfil.mkdir(parents=True, exist_ok=True)

    return get_browser(perfil)


# ============================================================
# PROMPT NORMAL
# ============================================================

SYSTEM_PROMPT = """Você é JARVIS, um assistente de IA geral e agente de programação.

Responda em português brasileiro, salvo se o usuário pedir outro idioma.

Você pode:
- responder perguntas gerais;
- explicar assuntos;
- resolver problemas;
- escrever textos;
- ajudar com programação;
- matemática;
- estudos;
- tarefas do dia a dia;
- pesquisar na internet;
- controlar um navegador através do Playwright;
- abrir sites;
- clicar em links e botões;
- digitar;
- navegar;
- rolar páginas;
- executar várias ações em sequência.

Quando o usuário pedir para o navegador fazer alguma coisa, não diga apenas como fazer.
A tarefa deve ser executada pelo agente quando possível.

Se não souber algo, diga claramente que não tem certeza.
Não invente fatos.

Seja útil e direto.
"""


# ============================================================
# PROMPT DO AGENTE
# ============================================================

AGENT_PROMPT = """Você é o agente JARVIS trabalhando em um computador.

Você pode:
- programar;
- editar arquivos;
- executar comandos;
- pesquisar na internet;
- controlar um navegador real usando Playwright.

Quando receber uma tarefa, EXECUTE a tarefa usando as ferramentas disponíveis.

RESPONDA SEMPRE com JSON válido, sem markdown:

{
  "reply": "mensagem curta para o usuário",
  "actions": [
    {"tool":"nome_da_ferramenta","...":"..."}
  ],
  "done": false
}

============================================================
FERRAMENTAS DE ARQUIVOS
============================================================

- list_files
- read_file
- write_file
- run_command
- project_plan
- backup_workspace
- git_status

============================================================
FERRAMENTAS DE INTERNET
============================================================

- fetch_url
- search_web

============================================================
FERRAMENTAS DE NAVEGADOR
============================================================

- browser_open_url
- browser_click_text
- browser_click_selector
- browser_type
- browser_back
- browser_forward
- browser_reload
- browser_scroll
- browser_info
- browser_close

============================================================
COMO USAR O NAVEGADOR
============================================================

browser_open_url:

{
  "tool": "browser_open_url",
  "url": "https://exemplo.com",
  "new_tab": false
}

browser_click_text:

{
  "tool": "browser_click_text",
  "text": "Entrar",
  "exact": false
}

browser_click_selector:

{
  "tool": "browser_click_selector",
  "selector": "button[type='submit']"
}

browser_type:

{
  "tool": "browser_type",
  "selector": "input[name='q']",
  "text": "minha pesquisa"
}

browser_back:

{
  "tool": "browser_back"
}

browser_forward:

{
  "tool": "browser_forward"
}

browser_reload:

{
  "tool": "browser_reload"
}

browser_scroll:

{
  "tool": "browser_scroll",
  "direction": "down",
  "amount": 700
}

browser_info:

{
  "tool": "browser_info"
}

browser_close:

{
  "tool": "browser_close"
}

============================================================
REGRA FUNDAMENTAL DO NAVEGADOR
============================================================

Quando o usuário pedir:

"abra"
"acesse"
"entre"
"clique"
"clique no botão"
"abra o segundo resultado"
"pesquise e abra"
"vá para"
"digite"
"preencha"
"role"
"volte"
"avance"
"atualize"

USE AS FERRAMENTAS DO NAVEGADOR.

Não responda apenas com instruções.

Exemplo:

Usuário:
"Pesquise carros usados e abra o segundo resultado."

Você deve fazer algo semelhante a:

1. search_web para descobrir os resultados, quando necessário.
2. browser_open_url para abrir a página.
3. browser_click_text ou browser_click_selector para clicar.
4. browser_info para confirmar a página atual.
5. Continue até terminar.

IMPORTANTE:

Uma tarefa pode possuir VÁRIAS ações.

Não pare depois de uma ação.

Continue executando ações até concluir a solicitação.

Se uma ferramenta retornar erro de clique:
- tente novamente sem exact;
- tente outro seletor;
- use browser_info;
- role a página se necessário;
- procure outro elemento;
- continue a tarefa.

Não invente que clicou.
Só diga que clicou quando a ferramenta retornar sucesso.

Para tarefas de navegador, prefira reutilizar a mesma página/aba.
Não abra uma nova aba desnecessariamente.

============================================================
REGRAS DE PROGRAMAÇÃO
============================================================

- Primeiro inspecione arquivos quando necessário.
- Preserve funcionalidades existentes.
- Não apague recursos sem motivo.
- Use caminhos relativos ao workspace.
- Não escreva fora do workspace.
- Execute testes quando possível.
- Não termine apenas com tutorial quando o usuário pediu execução.

============================================================
FINALIZAÇÃO
============================================================

Quando terminar:

{
  "reply": "Tarefa concluída.",
  "actions": [],
  "done": true
}

Se ainda houver ações necessárias, continue usando actions.
"""


# ============================================================
# ESTADO
# ============================================================

HISTORICO = []
MAX_MENSAGENS = 20
MAX_AGENT_RODADAS = 10

HISTORICO_LOCK = threading.Lock()
PENDENTE_LOCK = threading.Lock()

PENDENTE_ACAO = None


# ============================================================
# NVIDIA
# ============================================================

def ler_arquivo_chaves(caminho):
    if not caminho.exists():
        return []

    try:
        texto = caminho.read_text(encoding="utf-8")
    except Exception:
        return []

    chaves = []

    for linha in texto.splitlines():
        linha = linha.strip()

        if not linha or linha.startswith("#"):
            continue

        if "=" in linha:
            nome, valor = linha.split("=", 1)

            if nome.strip() in {
                "NVIDIA_API_KEY",
                "NVIDIA_API_KEYS",
                "NVIDIA_API_KEY_POOL"
            }:
                linha = valor.strip().strip('"\'')
        elif linha.startswith("NVIDIA_API_KEY:"):
            linha = linha.split(":", 1)[1].strip().strip('"\'')
        
        for item in linha.replace(";", "\n").replace(",", "\n").splitlines():
            item = item.strip()

            if item.startswith("nvapi-"):
                chaves.append(item)

    return chaves


def carregar_chaves_nvidia():
    valores = []

    for nome in (
        "NVIDIA_API_KEYS",
        "NVIDIA_API_KEY_POOL",
        "NVIDIA_API_KEY"
    ):
        valor = os.environ.get(nome, "")

        if valor:
            valores.extend(
                valor.replace(";", "\n")
                .replace(",", "\n")
                .splitlines()
            )

    for arquivo in (
        BASE_DIR / ".env",
        BASE_DIR / "nvidia.env",
        BASE_DIR / "NVIDIA_API_KEY.txt"
    ):
        valores.extend(ler_arquivo_chaves(arquivo))

    chaves = []

    for valor in valores:
        valor = valor.strip().strip('"\'')

        if valor.startswith("nvapi-") and valor not in chaves:
            chaves.append(valor)

    return chaves


def http_json(url, chave, metodo="GET", payload=None, timeout=45):
    dados = None

    headers = {
        "Authorization": f"Bearer {chave}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    if payload is not None:
        dados = json.dumps(
            payload,
            ensure_ascii=False
        ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=dados,
        headers=headers,
        method=metodo
    )

    with urllib.request.urlopen(req, timeout=timeout) as resposta:
        corpo = resposta.read().decode("utf-8")

        return json.loads(corpo) if corpo else {}


def descobrir_modelos(chave):
    try:
        dados = http_json(
            f"{NVIDIA_BASE_URL}/models",
            chave,
            timeout=20
        )

        return [
            x.get("id")
            for x in dados.get("data", [])
            if isinstance(x, dict) and x.get("id")
        ]

    except Exception as erro:
        print(
            f"DEBUG: catálogo NVIDIA indisponível: {erro}"
        )

        return []


def ordenar_modelos(modelos):
    preferidos = [
        MODELO_PREFERIDO,
        "nvidia/nemotron-3.5-super-120b-a12b",
        "nvidia/nemotron-3.5-nano-12b-v2",
        "nvidia/nemotron-3.5-nano-9b-v2",
        "openai/gpt-oss-20b",
        "qwen/qwen3.5-122b-a10b",
        "deepseek-ai/deepseek-v4.1-flash",
        "z-ai/glm-5.3-flash",
        "meta/llama-3.3-70b-instruct",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
    ]

    resultado = []
    vistos = set()

    for modelo in preferidos + modelos:
        if modelo and modelo not in vistos:
            vistos.add(modelo)
            resultado.append(modelo)

    return resultado


def chamar_modelo(chave, modelo, mensagens, max_tokens=4096):
    payload = {
        "model": modelo,
        "messages": mensagens,
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": max_tokens,
        "stream": False
    }

    dados = http_json(
        f"{NVIDIA_BASE_URL}/chat/completions",
        chave,
        "POST",
        payload,
        120
    )

    escolhas = dados.get("choices") or []

    if not escolhas:
        raise RuntimeError(
            "A NVIDIA respondeu sem choices."
        )

    msg = escolhas[0].get("message") or {}

    conteudo = (
        msg.get("content")
        or msg.get("reasoning_content")
    )

    if not conteudo:
        raise RuntimeError(
            "A NVIDIA respondeu sem conteúdo."
        )

    return str(conteudo).strip()


def executar_com_modelo(mensagens, max_tokens=4096):
    chaves = carregar_chaves_nvidia()

    if not chaves:
        raise RuntimeError(
            "Nenhuma NVIDIA_API_KEY foi encontrada no .env"
        )

    erros = []

    for indice, chave in enumerate(chaves, 1):

        modelos = ordenar_modelos(
            descobrir_modelos(chave)
        )[:25]

        for modelo in modelos:

            try:
                print(
                    f"DEBUG: chave {indice}/{len(chaves)} -> {modelo}"
                )

                return (
                    chamar_modelo(
                        chave,
                        modelo,
                        mensagens,
                        max_tokens
                    ),
                    modelo
                )

            except urllib.error.HTTPError as erro:

                corpo = ""

                try:
                    corpo = erro.read().decode(
                        "utf-8",
                        errors="replace"
                    )[:500]
                except Exception:
                    pass

                erros.append(
                    f"{modelo}: HTTP {erro.code} {corpo}"
                )

                if erro.code in (401, 403):
                    break

            except Exception as erro:
                erros.append(
                    f"{modelo}: {erro}"
                )

    raise RuntimeError(
        " | ".join(erros[-4:])
        or "Nenhum modelo NVIDIA respondeu."
    )


# ============================================================
# CHAT NORMAL
# ============================================================

def consultar_nvidia(mensagem):
    global HISTORICO

    mensagens = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    with HISTORICO_LOCK:
        mensagens.extend(
            HISTORICO[-MAX_MENSAGENS:]
        )

    mensagens.append(
        {
            "role": "user",
            "content": mensagem
        }
    )

    resposta, modelo = executar_com_modelo(
        mensagens
    )

    with HISTORICO_LOCK:
        HISTORICO.extend(
            [
                {
                    "role": "user",
                    "content": mensagem
                },
                {
                    "role": "assistant",
                    "content": resposta
                }
            ]
        )

        HISTORICO[:] = HISTORICO[-MAX_MENSAGENS:]

    print(
        f"DEBUG: resposta normal via {modelo}"
    )

    return resposta


# ============================================================
# SEGURANÇA DE CAMINHOS
# ============================================================

def seguro_relativo(path):
    p = (
        WORKSPACE / str(path)
    ).resolve()

    if (
        p != WORKSPACE
        and WORKSPACE not in p.parents
    ):
        raise ValueError(
            "Caminho fora do workspace bloqueado."
        )

    return p


# ============================================================
# AUDITORIA
# ============================================================

def registrar_auditoria(evento, dados=None):
    CONTROLE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    registro = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "event": evento,
        "data": dados or {}
    }

    with AUDIT_FILE.open(
        "a",
        encoding="utf-8"
    ) as arquivo:
        arquivo.write(
            json.dumps(
                registro,
                ensure_ascii=False
            ) + "\n"
        )


# ============================================================
# BACKUP
# ============================================================

def criar_backup(motivo="alteracao"):
    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    nome = (
        datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )
        + "-"
        + re.sub(
            r"[^a-zA-Z0-9_-]+",
            "-",
            motivo
        )[:40]
    )

    destino = (
        BACKUP_DIR / nome
    )

    destino.mkdir(
        parents=True,
        exist_ok=False
    )

    for item in WORKSPACE.iterdir():

        if item.name == ".jarvis":
            continue

        alvo = destino / item.name

        if item.is_dir():
            shutil.copytree(
                item,
                alvo,
                ignore=shutil.ignore_patterns(
                    ".git",
                    "__pycache__",
                    ".venv",
                    "node_modules"
                )
            )
        else:
            shutil.copy2(
                item,
                alvo
            )

    registrar_auditoria(
        "backup_created",
        {
            "path": destino.relative_to(
                WORKSPACE
            ).as_posix(),
            "reason": motivo
        }
    )

    return destino.relative_to(
        WORKSPACE
    ).as_posix()


# ============================================================
# GIT
# ============================================================

def comando_git(args):
    resultado = subprocess.run(
        ["git", *args],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=30
    )

    return (
        f"EXIT {resultado.returncode}\n"
        f"STDOUT:\n{resultado.stdout[-8000:]}\n"
        f"STDERR:\n{resultado.stderr[-4000:]}"
    )


# ============================================================
# FERRAMENTAS DO JARVIS
# ============================================================

def ferramenta(action):
    global PENDENTE_ACAO

    tool = action.get("tool")

    # --------------------------------------------------------
    # ARQUIVOS
    # --------------------------------------------------------

    if tool == "list_files":

        p = seguro_relativo(
            action.get("path", ".")
        )

        itens = []

        for x in sorted(
            p.iterdir(),
            key=lambda z: (
                not z.is_dir(),
                z.name.lower()
            )
        )[:300]:

            itens.append(
                ("DIR " if x.is_dir() else "FILE ")
                + x.relative_to(
                    WORKSPACE
                ).as_posix()
            )

        return "\n".join(itens) or "(vazio)"

    # --------------------------------------------------------

    if tool == "read_file":

        p = seguro_relativo(
            action["path"]
        )

        if p.stat().st_size > 2_000_000:
            raise ValueError(
                "Arquivo grande demais para leitura automática."
            )

        return p.read_text(
            encoding="utf-8",
            errors="replace"
        )

    # --------------------------------------------------------

    if tool == "project_plan":

        plano = str(
            action.get("plan", "")
        ).strip()

        if not plano:
            raise ValueError(
                "O plano não pode ser vazio."
            )

        p = seguro_relativo(
            ".jarvis/plan.md"
        )

        p.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        p.write_text(
            "# Plano JARVIS\n\n"
            + plano
            + "\n",
            encoding="utf-8"
        )

        registrar_auditoria(
            "plan_created",
            {
                "path": ".jarvis/plan.md"
            }
        )

        return "Plano salvo em .jarvis/plan.md"

    # --------------------------------------------------------

    if tool == "backup_workspace":

        return (
            "Backup criado em "
            + criar_backup(
                str(
                    action.get(
                        "reason",
                        "antes-de-alterar"
                    )
                )
            )
        )

    # --------------------------------------------------------

    if tool == "git_status":

        if not (
            WORKSPACE / ".git"
        ).exists():

            return (
                "Este workspace ainda não é "
                "um repositório Git."
            )

        resultado = comando_git(
            ["status", "--short", "--branch"]
        )

        registrar_auditoria(
            "git_status",
            {}
        )

        return resultado

    # --------------------------------------------------------
    # INTERNET
    # --------------------------------------------------------

    if tool == "fetch_url":

        url = str(
            action.get("url", "")
        ).strip()

        if not re.match(
            r"^https?://",
            url,
            re.I
        ):
            raise ValueError(
                "A URL deve começar com http:// ou https://."
            )

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "JARVIS/1.0"
            }
        )

        with urllib.request.urlopen(
            req,
            timeout=20
        ) as resposta:

            tipo = (
                resposta.headers
                .get_content_type()
            )

            if tipo not in {
                "text/html",
                "text/plain",
                "application/json",
                "application/xml"
            }:
                raise ValueError(
                    f"Tipo de conteúdo não suportado: {tipo}"
                )

            conteudo = resposta.read(
                1_000_000
            ).decode(
                "utf-8",
                errors="replace"
            )

        return conteudo[:20_000]

    # --------------------------------------------------------

    if tool == "search_web":

        consulta = str(
            action.get("query", "")
        ).strip()

        if not consulta:
            raise ValueError(
                "A consulta de pesquisa não pode ser vazia."
            )

        url = (
            "https://html.duckduckgo.com/html/?q="
            + urllib.parse.quote_plus(
                consulta
            )
        )

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                    "Mozilla/5.0 JARVIS/1.0"
            }
        )

        with urllib.request.urlopen(
            req,
            timeout=20
        ) as resposta:

            html = resposta.read(
                1_500_000
            ).decode(
                "utf-8",
                errors="replace"
            )

        resultados = []

        for bloco in re.findall(
            r'<div class="result results_links results_links_deep web-result">(.*?)</div>\s*</div>',
            html,
            re.S
        ):

            link = re.search(
                r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>',
                bloco,
                re.S
            )

            trecho = re.search(
                r'class="result__snippet"[^>]*>(.*?)</a?\s*>',
                bloco,
                re.S
            )

            if link:

                limpar = (
                    lambda valor:
                    re.sub(
                        r"<[^>]+>",
                        "",
                        valor
                    )
                    .replace(
                        "&quot;",
                        '"'
                    )
                    .replace(
                        "&amp;",
                        "&"
                    )
                    .strip()
                )

                resultados.append(
                    {
                        "title":
                            limpar(link.group(2)),
                        "url":
                            link.group(1),
                        "snippet":
                            limpar(
                                trecho.group(1)
                            )
                            if trecho
                            else ""
                    }
                )

        if not resultados:

            links = re.findall(
                r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>',
                html,
                re.S
            )

            resultados = [
                {
                    "title":
                        re.sub(
                            r"<[^>]+>",
                            "",
                            titulo
                        ).strip(),
                    "url":
                        link,
                    "snippet":
                        ""
                }
                for link, titulo in links[:8]
            ]

        if not resultados:

            google_url = (
                "https://www.google.com/search?hl=pt-BR&q="
                + urllib.parse.quote_plus(
                    consulta
                )
            )

            google_req = urllib.request.Request(
                google_url,
                headers={
                    "User-Agent":
                        "Mozilla/5.0 JARVIS/1.0"
                }
            )

            try:

                with urllib.request.urlopen(
                    google_req,
                    timeout=20
                ) as resposta:

                    google_html = resposta.read(
                        2_000_000
                    ).decode(
                        "utf-8",
                        errors="replace"
                    )

                for link, titulo in re.findall(
                    r'<a href="/url\?q=(https?://[^&"]+)[^>]*><h3[^>]*>(.*?)</h3>',
                    google_html,
                    re.S
                ):

                    resultados.append(
                        {
                            "title":
                                re.sub(
                                    r"<[^>]+>",
                                    "",
                                    titulo
                                ).strip(),
                            "url":
                                urllib.parse.unquote(
                                    link
                                ),
                            "snippet":
                                ""
                        }
                    )

            except Exception as erro:

                print(
                    "DEBUG: fallback Google indisponível:",
                    erro
                )

        return json.dumps(
            resultados[:8],
            ensure_ascii=False
        )

    # ========================================================
    # NAVEGADOR PLAYWRIGHT
    # ========================================================

    if tool == "browser_open_url":

        url = str(
            action.get("url", "")
        ).strip()

        if not url:
            raise ValueError(
                "Informe a URL para abrir."
            )

        resultado = navegador().open_url(
            url,
            new_tab=bool(
                action.get(
                    "new_tab",
                    False
                )
            )
        )

        registrar_auditoria(
            "browser_open_url",
            {
                "url": url,
                "result": resultado
            }
        )

        return json.dumps(
            resultado,
            ensure_ascii=False
        )

    # --------------------------------------------------------

    if tool == "browser_click_text":

        texto = str(
            action.get("text", "")
        ).strip()

        if not texto:
            raise ValueError(
                "Informe o texto que deve ser clicado."
            )

        exact = bool(
            action.get(
                "exact",
                False
            )
        )

        resultado = navegador().click_text(
            texto,
            exact=exact
        )

        # Se não conseguiu com o modo solicitado,
        # tenta novamente sem exact.
        if (
            isinstance(resultado, dict)
            and not resultado.get("success")
            and exact
        ):
            resultado = navegador().click_text(
                texto,
                exact=False
            )

        registrar_auditoria(
            "browser_click_text",
            {
                "text": texto,
                "result": resultado
            }
        )

        return json.dumps(
            resultado,
            ensure_ascii=False
        )

    # --------------------------------------------------------

    if tool == "browser_click_selector":

        selector = str(
            action.get("selector", "")
        ).strip()

        if not selector:
            raise ValueError(
                "Informe o seletor CSS."
            )

        resultado = navegador().click_selector(
            selector
        )

        registrar_auditoria(
            "browser_click_selector",
            {
                "selector": selector,
                "result": resultado
            }
        )

        return json.dumps(
            resultado,
            ensure_ascii=False
        )

    # --------------------------------------------------------

    if tool == "browser_type":

        selector = str(
            action.get("selector", "")
        ).strip()

        texto = str(
            action.get("text", "")
        )

        if not selector:
            raise ValueError(
                "Informe o seletor do campo."
            )

        resultado = navegador().type_text(
            selector,
            texto
        )

        registrar_auditoria(
            "browser_type",
            {
                "selector": selector
            }
        )

        return json.dumps(
            resultado,
            ensure_ascii=False
        )

    # --------------------------------------------------------

    if tool == "browser_back":

        resultado = navegador().back()

        registrar_auditoria(
            "browser_back",
            {
                "result": resultado
            }
        )

        return json.dumps(
            resultado,
            ensure_ascii=False
        )

    # --------------------------------------------------------

    if tool == "browser_forward":

        resultado = navegador().forward()

        registrar_auditoria(
            "browser_forward",
            {
                "result": resultado
            }
        )

        return json.dumps(
            resultado,
            ensure_ascii=False
        )

    # --------------------------------------------------------

    if tool == "browser_reload":

        resultado = navegador().reload()

        registrar_auditoria(
            "browser_reload",
            {
                "result": resultado
            }
        )

        return json.dumps(
            resultado,
            ensure_ascii=False
        )

    # --------------------------------------------------------

    if tool == "browser_scroll":

        direction = str(
            action.get(
                "direction",
                "down"
            )
        )

        amount = int(
            action.get(
                "amount",
                700
            )
        )

        resultado = navegador().scroll(
            direction,
            amount
        )

        registrar_auditoria(
            "browser_scroll",
            {
                "direction": direction,
                "amount": amount,
                "result": resultado
            }
        )

        return json.dumps(
            resultado,
            ensure_ascii=False
        )

    # --------------------------------------------------------

    if tool == "browser_info":

        resultado = navegador().page_info()

        return json.dumps(
            resultado,
            ensure_ascii=False
        )

    # --------------------------------------------------------

    if tool == "browser_close":

        navegador().close()

        registrar_auditoria(
            "browser_close",
            {}
        )

        return json.dumps(
            {
                "success": True,
                "message":
                    "Navegador encerrado."
            },
            ensure_ascii=False
        )

    # ========================================================
    # WRITE FILE
    # ========================================================

    if tool == "write_file":

        p = seguro_relativo(
            action["path"]
        )

        if (
            not AUTO_APROVAR_COMANDOS
            and p.exists()
            and p.stat().st_size > 0
        ):
            backup = criar_backup(
                "antes-de-editar-" + p.name
            )
        else:
            backup = None

        p.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        p.write_text(
            str(
                action.get(
                    "content",
                    ""
                )
            ),
            encoding="utf-8"
        )

        registrar_auditoria(
            "file_written",
            {
                "path":
                    p.relative_to(
                        WORKSPACE
                    ).as_posix(),
                "backup":
                    backup
            }
        )

        return (
            "Arquivo gravado: "
            + p.relative_to(
                WORKSPACE
            ).as_posix()
        )

    # ========================================================
    # COMMAND
    # ========================================================

    if tool == "run_command":

        comando = str(
            action.get(
                "command",
                ""
            )
        ).strip()

        if not comando:
            return "Comando vazio."

        proibidos = [
            "format c:",
            "format c ",
            "del /s /q c:\\",
            "shutdown /",
            "diskpart",
            "reg delete hklm",
            "rm -rf /",
            "mkfs."
        ]

        if any(
            x in comando.lower()
            for x in proibidos
        ):
            raise ValueError(
                "Comando destrutivo bloqueado pelo agente local."
            )

        riscos = [
            "git push",
            "git reset --hard",
            "git clean -fd",
            "rm -rf",
            "sudo ",
            "pip install",
            "npm install",
            "curl |",
            "wget |"
        ]

        if (
            not AUTO_APROVAR_COMANDOS
            and any(
                x in comando.lower()
                for x in riscos
            )
        ):

            with PENDENTE_LOCK:
                PENDENTE_ACAO = {
                    "tool":
                        "run_command",
                    "command":
                        comando
                }

            registrar_auditoria(
                "approval_required",
                {
                    "command":
                        comando
                }
            )

            return (
                "APROVAÇÃO NECESSÁRIA: "
                "o comando foi bloqueado até "
                "o usuário aprovar: "
                + comando
            )

        r = subprocess.run(
            comando,
            cwd=WORKSPACE,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )

        registrar_auditoria(
            "command_run",
            {
                "command":
                    comando,
                "returncode":
                    r.returncode
            }
        )

        return (
            f"EXIT {r.returncode}\n"
            f"STDOUT:\n{r.stdout[-8000:]}\n"
            f"STDERR:\n{r.stderr[-4000:]}"
        )

    raise ValueError(
        f"Ferramenta desconhecida: {tool}"
    )


# ============================================================
# JSON
# ============================================================

def extrair_json(texto):
    texto = texto.strip()

    if texto.startswith("```"):

        texto = re.sub(
            r"^```(?:json)?\s*",
            "",
            texto,
            flags=re.I
        )

        texto = re.sub(
            r"\s*```$",
            "",
            texto
        )

    try:
        return json.loads(texto)

    except Exception:

        inicio = texto.find("{")
        fim = texto.rfind("}")

        if (
            inicio >= 0
            and fim > inicio
        ):
            return json.loads(
                texto[
                    inicio:fim + 1
                ]
            )

        raise


# ============================================================
# EXECUTOR DO AGENTE
# ============================================================

def executar_agente(mensagem):

    historico = [
        {
            "role":
                "system",
            "content":
                AGENT_PROMPT
        },
        {
            "role":
                "user",
            "content":
                mensagem
        }
    ]

    ultima = (
        "Vou analisar e executar a tarefa."
    )

    for rodada in range(
        MAX_AGENT_RODADAS
    ):

        print(
            f"DEBUG: rodada do agente {rodada + 1}/{MAX_AGENT_RODADAS}"
        )

        bruto, modelo = executar_com_modelo(
            historico,
            max_tokens=6000
        )

        try:
            plano = extrair_json(
                bruto
            )

        except Exception:

            print(
                "DEBUG: modelo não retornou JSON válido."
            )

            return bruto

        ultima = str(
            plano.get(
                "reply",
                ultima
            )
        )

        actions = (
            plano.get("actions")
            or []
        )

        done = bool(
            plano.get(
                "done",
                False
            )
        )

        print(
            "DEBUG: ações recebidas:",
            json.dumps(
                actions,
                ensure_ascii=False
            )
        )

        if (
            not actions
            and done
        ):
            return ultima

        if not actions:
            historico.append(
                {
                    "role":
                        "assistant",
                    "content":
                        json.dumps(
                            plano,
                            ensure_ascii=False
                        )
                }
            )

            historico.append(
                {
                    "role":
                        "user",
                    "content":
                        "Ainda não concluiu. "
                        "Continue a tarefa usando "
                        "as ferramentas necessárias."
                }
            )

            continue

        resultados = []

        # Até 12 ações por rodada.
        # Isso permite sequências maiores de cliques.
        for action in actions[:12]:

            try:

                resultado = ferramenta(
                    action
                )

                resultados.append(
                    {
                        "tool":
                            action.get(
                                "tool"
                            ),
                        "ok":
                            True,
                        "result":
                            resultado
                    }
                )

                print(
                    "DEBUG: ferramenta OK:",
                    action.get("tool")
                )

            except Exception as erro:

                resultados.append(
                    {
                        "tool":
                            action.get(
                                "tool"
                            ),
                        "ok":
                            False,
                        "result":
                            str(erro)
                    }
                )

                print(
                    "DEBUG: ferramenta ERRO:",
                    action.get("tool"),
                    erro
                )

        historico.append(
            {
                "role":
                    "assistant",
                "content":
                    json.dumps(
                        plano,
                        ensure_ascii=False
                    )
            }
        )

        historico.append(
            {
                "role":
                    "user",
                "content":
                    (
                        "RESULTADOS DAS FERRAMENTAS:\n"
                        + json.dumps(
                            resultados,
                            ensure_ascii=False
                        )
                        + "\n\n"
                        "Continue a tarefa. "
                        "Analise os resultados. "
                        "Se ainda houver alguma ação necessária, "
                        "execute-a. "
                        "Não diga que uma ação foi realizada "
                        "se a ferramenta retornou erro. "
                        "Se terminou, actions=[] e done=true."
                    )
            }
        )

    return (
        ultima
        + " Terminei o número máximo de etapas automáticas."
    )


# ============================================================
# HTTP SERVER
# ============================================================

class JarvisHandler(
    SimpleHTTPRequestHandler
):

    def __init__(
        self,
        *args,
        **kwargs
    ):
        super().__init__(
            *args,
            directory=str(BASE_DIR),
            **kwargs
        )

    # --------------------------------------------------------

    def do_GET(self):

        if self.path in (
            "/",
            "/index.html"
        ):
            self.path = "/interface.html"

        # HEALTH
        if self.path == "/api/health":

            corpo = json.dumps(
                {
                    "ok": True,
                    "service": "JARVIS",
                    "workspace":
                        str(WORKSPACE),
                    "browser":
                        BROWSER_DISPONIVEL
                },
                ensure_ascii=False
            ).encode("utf-8")

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(corpo))
            )

            self.end_headers()

            self.wfile.write(
                corpo
            )

            return

        # STATUS
        if self.path == "/api/status":

            with PENDENTE_LOCK:
                pendente = PENDENTE_ACAO

            corpo = json.dumps(
                {
                    "ok":
                        True,
                    "workspace":
                        str(WORKSPACE),
                    "auto_approve":
                        AUTO_APROVAR_COMANDOS,
                    "pending_approval":
                        pendente,
                    "browser":
                        BROWSER_DISPONIVEL,
                    "browser_error":
                        BROWSER_ERRO_IMPORT
                },
                ensure_ascii=False
            ).encode("utf-8")

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(corpo))
            )

            self.end_headers()

            self.wfile.write(
                corpo
            )

            return

        super().do_GET()

    # --------------------------------------------------------

    def do_OPTIONS(self):

        self.send_response(204)

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.end_headers()

    # --------------------------------------------------------

    def do_POST(self):

        global PENDENTE_ACAO

        # ----------------------------------------------------
        # APROVAÇÃO
        # ----------------------------------------------------

        if self.path == "/api/approve":

            try:

                tamanho = int(
                    self.headers.get(
                        "Content-Length",
                        "0"
                    )
                )

                dados = json.loads(
                    self.rfile.read(
                        tamanho
                    ).decode("utf-8")
                )

                aprovado = bool(
                    dados.get(
                        "approved"
                    )
                )

                with PENDENTE_LOCK:

                    pendente = PENDENTE_ACAO

                    if aprovado:
                        PENDENTE_ACAO = None

                if not pendente:
                    raise ValueError(
                        "Não há ação pendente."
                    )

                if not aprovado:

                    registrar_auditoria(
                        "approval_denied",
                        {
                            "command":
                                pendente["command"]
                        }
                    )

                    corpo = json.dumps(
                        {
                            "ok":
                                True,
                            "reply":
                                "Ação cancelada."
                        },
                        ensure_ascii=False
                    ).encode("utf-8")

                    self.send_response(
                        200
                    )

                else:

                    comando = pendente[
                        "command"
                    ]

                    backup = criar_backup(
                        "antes-de-comando-aprovado"
                    )

                    resultado = subprocess.run(
                        comando,
                        cwd=WORKSPACE,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )

                    registrar_auditoria(
                        "approved_command_run",
                        {
                            "command":
                                comando,
                            "returncode":
                                resultado.returncode,
                            "backup":
                                backup
                        }
                    )

                    corpo = json.dumps(
                        {
                            "ok":
                                resultado.returncode == 0,
                            "reply":
                                (
                                    f"EXIT {resultado.returncode}\n"
                                    f"{resultado.stdout[-8000:]}\n"
                                    f"{resultado.stderr[-4000:]}"
                                )
                        },
                        ensure_ascii=False
                    ).encode("utf-8")

                    self.send_response(
                        200
                    )

            except Exception as erro:

                corpo = json.dumps(
                    {
                        "ok":
                            False,
                        "reply":
                            f"Erro na aprovação: {erro}"
                    },
                    ensure_ascii=False
                ).encode("utf-8")

                self.send_response(
                    400
                )

            self.send_header(
                "Access-Control-Allow-Origin",
                "*"
            )

            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(corpo))
            )

            self.end_headers()

            self.wfile.write(
                corpo
            )

            return

        # ----------------------------------------------------
        # CHAT / AGENTE
        # ----------------------------------------------------

        if self.path not in (
            "/api/chat",
            "/api/agent"
        ):

            self.send_error(
                404
            )

            return

        try:

            tamanho = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            if (
                tamanho <= 0
                or tamanho > 2_000_000
            ):
                raise ValueError(
                    "Corpo da requisição inválido ou grande demais."
                )

            dados = json.loads(
                self.rfile.read(
                    tamanho
                ).decode("utf-8")
            )

            mensagem = str(
                dados.get(
                    "message",
                    ""
                )
            ).strip()

            if not mensagem:
                raise ValueError(
                    "Mensagem vazia."
                )

            if self.path == "/api/agent":
                resposta = executar_agente(
                    mensagem
                )
            else:
                resposta = consultar_nvidia(
                    mensagem
                )

            corpo = json.dumps(
                {
                    "reply":
                        resposta
                },
                ensure_ascii=False
            ).encode("utf-8")

            self.send_response(
                200
            )

        except Exception as erro:

            print(
                "DEBUG: erro:",
                repr(erro)
            )

            corpo = json.dumps(
                {
                    "reply":
                        (
                            "Erro no Jarvis: "
                            f"{type(erro).__name__}: "
                            f"{erro}"
                        )
                },
                ensure_ascii=False
            ).encode("utf-8")

            self.send_response(
                500
            )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(corpo))
        )

        self.end_headers()

        self.wfile.write(
            corpo
        )

    # --------------------------------------------------------

    def log_message(
        self,
        formato,
        *args
    ):
        print(
            formato % args
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    print(
        f"JARVIS online em http://0.0.0.0:{PORTA}/interface.html"
    )

    print(
        f"Workspace do agente: {WORKSPACE}"
    )

    print(
        f"NVIDIA: {NVIDIA_BASE_URL}"
    )

    print(
        f"Modelo: {MODELO_PREFERIDO or 'descoberta automática'}"
    )

    print(
        f"Chaves carregadas: {len(carregar_chaves_nvidia())}"
    )

    print(
        f"Browser controller: {'OK' if BROWSER_DISPONIVEL else 'ERRO'}"
    )

    if BROWSER_ERRO_IMPORT:
        print(
            f"Browser error: {BROWSER_ERRO_IMPORT}"
        )

    servidor = ThreadingHTTPServer(
        ("0.0.0.0", PORTA),
        JarvisHandler
    )

    try:

        servidor.serve_forever()

    except KeyboardInterrupt:

        print(
            "\nJARVIS encerrado."
        )

    finally:

        servidor.server_close()