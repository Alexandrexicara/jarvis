# -*- coding: utf-8 -*-
"""JARVIS + AGENTE — integração estável para criação de projeto e geração de código."""

import os
import subprocess

from jarvis_core import criar_projeto, gerar_codigo, get_projects_dir, parse_project_name

PASTA_PROJETOS = get_projects_dir()
PASTA_ATUAL = ""


class Agente:
    def __init__(self, pasta):
        self.pasta = pasta
        os.makedirs(self.pasta, exist_ok=True)

    def criar_arquivo(self, nome, conteudo):
        caminho = os.path.join(self.pasta, nome)
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(conteudo)
        return caminho

    def listar_arquivos(self):
        if not os.path.isdir(self.pasta):
            return "📋 Pasta vazia"
        itens = sorted(os.listdir(self.pasta))
        return "\n".join(f"  - {item}" for item in itens)

    def executar_comando(self, cmd):
        try:
            res = subprocess.run(cmd, shell=True, cwd=self.pasta,
                                 capture_output=True, text=True, encoding="utf-8")
            return res.returncode == 0, (res.stdout or "") + (res.stderr or "")
        except Exception as error:
            return False, str(error)


agente = None


def abrir_vscode(caminho):
    try:
        subprocess.run(["code", "-r", caminho], capture_output=True)
    except Exception:
        pass


def escolher_projeto(nome):
    global PASTA_ATUAL, agente
    nome = parse_project_name(nome) if isinstance(nome, str) and not nome.strip().endswith(".py") else nome.strip()
    pasta = criar_projeto(nome)
    PASTA_ATUAL = pasta
    agente = Agente(pasta)
    abrir_vscode(pasta)
    return f"✅ Projeto '{nome}' pronto! A pasta foi criada em: {pasta}"


def criar_parede_sorte():
    if not agente:
        return "❌ Primeiro digite: Cria um projeto chamado cassino"
    caminho = agente.criar_arquivo(
        "parede-sorte.html",
        """<!DOCTYPE html>
<html lang=\"pt-BR\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Parede da Sorte</title>
  <style>
    body { font-family: Arial, sans-serif; background: #111827; color: white; display: flex; justify-content: center; padding: 40px; }
    .card { background: #1f2937; border-radius: 12px; border: 1px solid #fbbf24; padding: 20px; width: 420px; }
    h1 { color: #fbbf24; text-align: center; }
    .valor { font-size: 28px; text-align: center; margin: 20px 0; }
    button { width: 100%; padding: 12px; font-size: 18px; border-radius: 8px; border: none; background: #10b981; cursor: pointer; }
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>🪙 Parede da Sorte</h1>
    <div class=\"valor\" id=\"valor\">💰 R$ 100</div>
    <button onclick=\"sortear()\">Sortear</button>
  </div>
  <script>
    function sortear() {
      const valor = Math.floor(Math.random() * 1000) + 1;
      document.getElementById('valor').textContent = '💰 R$ ' + valor;
    }
  </script>
</body>
</html>"""
    )
    return f"✅ Jogo criado em {caminho}"


def listar():
    if not agente:
        return "❌ Primeiro digite: Cria um projeto chamado cassino"
    return "📋 Arquivos:\n" + agente.listar_arquivos()


def gerar_codigo_do_prompt(descricao):
    if not agente:
        return "❌ Primeiro digite: Cria um projeto chamado cassino"
    nome_arquivo = gerar_codigo("app", descricao)
    return f"✅ Código gerado em: {nome_arquivo}"


print("""
╔══════════════════════════════════════════════════╗
║   🧠 JARVIS + AGENTE — PRONTO!                 ║
║                                                ║
║   Exemplos:                                    ║
║   Cria um projeto chamado cassino              ║
║   Gera o código de um app de vendas            ║
║   Cria o jogo da parede da sorte               ║
║   Lista os arquivos                            ║
║   Sair                                         ║
╚══════════════════════════════════════════════════╝
""")

while True:
    fala = input("🤖 JARVIS > ").strip()
    if not fala:
        continue
    f = fala.lower()

    if "sair" in f or "encerrar" in f:
        print("👋 Até logo!")
        break

    if "projeto" in f or "chamado" in f or "cria" in f or "criar" in f:
        nome = parse_project_name(fala)
        if nome:
            print(escolher_projeto(nome))
            continue

    if "parede" in f and "sorte" in f:
        print(criar_parede_sorte())
        continue

    if "gera" in f and "codigo" in f:
        print(gerar_codigo_do_prompt(fala))
        continue

    if "lista" in f or "mostra" in f:
        print(listar())
        continue

    print(f"🤖 Entendi: '{fala}' — vou criar e organizar no projeto atual.")
