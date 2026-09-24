#!/bin/bash
echo "======================================================"
echo "   AGENTE DE CÓDIGO — CRIANDO ESTRUTURA"
echo "======================================================"
echo ""

mkdir -p agente_codigo/{projetos,logs,templates}
cd agente_codigo || exit 1

echo "[1/6] Criando agente_codigo.py..."
cat > agente_codigo.py << 'PYEOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGENTE DE CÓDIGO — JARVIS
"""

import os
import subprocess
import shutil
from datetime import datetime

RAIZ = os.path.abspath("..")
PASTA_ATUAL = ""

def log(acao, detalhe=""):
    agora = datetime.now().strftime("%H:%M:%S")
    with open("logs/agente.log", "a", encoding="utf-8") as f:
        f.write(f"[{agora}] {acao} — {detalhe}\n")
    print(f"✅ {acao} {detalhe}")

def escolher_projeto(nome=""):
    global PASTA_ATUAL
    if not nome: nome = input("Nome do projeto: ").strip()
    caminho = os.path.join("projetos", nome)
    if not os.path.exists(caminho): os.makedirs(caminho)
    PASTA_ATUAL = caminho
    os.chdir(PASTA_ATUAL)
    log("Projeto", nome)
    return f"📁 Projeto ativo: {nome}"

def criar_pasta(nome):
    if not PASTA_ATUAL: return "❌ Escolha projeto primeiro"
    caminho = os.path.join(PASTA_ATUAL, nome)
    os.makedirs(caminho, exist_ok=True)
    log("Pasta criada", nome)
    return f"📂 Pasta '{nome}' criada"

def criar_arquivo(nome, conteudo=""):
    if not PASTA_ATUAL: return "❌ Escolha projeto primeiro"
    caminho = os.path.join(PASTA_ATUAL, nome)
    with open(caminho, "w", encoding="utf-8") as f: f.write(conteudo)
    log("Arquivo criado", nome)
    return f"📄 Arquivo '{nome}' criado"

def alterar_arquivo(nome, texto, acresc=False):
    if not PASTA_ATUAL: return "❌ Escolha projeto primeiro"
    caminho = os.path.join(PASTA_ATUAL, nome)
    modo = "a" if acresc else "w"
    with open(caminho, modo, encoding="utf-8") as f: f.write(texto)
    log("Arquivo alterado", nome)
    return f"✏️ '{nome}' atualizado"

def ler_arquivo(nome):
    if not PASTA_ATUAL: return "❌ Escolha projeto primeiro"
    caminho = os.path.join(PASTA_ATUAL, nome)
    if not os.path.exists(caminho): return f"❌ '{nome}' não existe"
    with open(caminho, "r", encoding="utf-8") as f:
        return f"📖 {nome}:\n{f.read()}"

def excluir_item(nome):
    if not PASTA_ATUAL: return "❌ Escolha projeto primeiro"
    caminho = os.path.join(PASTA_ATUAL, nome)
    if os.path.isdir(caminho):
        shutil.rmtree(caminho)
        return f"🗑️ Pasta '{nome}' removida"
    elif os.path.exists(caminho):
        os.remove(caminho)
        return f"🗑️ Arquivo '{nome}' removido"
    return f"❌ Não encontrado: {nome}"

def listar_projeto():
    if not PASTA_ATUAL: return "❌ Escolha projeto primeiro"
    itens = "\n".join(f"  - {i}" for i in sorted(os.listdir(PASTA_ATUAL)))
    return f"📋 Arquivos:\n{itens}" if itens else "📋 Pasta vazia"

def executar_comando(cmd):
    if not PASTA_ATUAL: return "❌ Escolha projeto primeiro"
    r = subprocess.run(cmd, shell=True, cwd=PASTA_ATUAL, capture_output=True, text=True, encoding="utf-8")
    saida = r.stdout + r.stderr
    status = "✅ Sucesso" if r.returncode == 0 else "⚠️ Erro"
    return f"▶️ {status}:\n{saida}"

def abrir_vscode():
    try:
        subprocess.run(["code", PASTA_ATUAL or RAIZ])
        return "💻 VS Code aberto"
    except: return "⚠️ VS Code não encontrado"

def menu():
    while True:
        print("\n" + "="*50)
        print("🤖 AGENTE DE CÓDIGO — JARVIS")
        print(f"Pasta ativa: {PASTA_ATUAL or 'Nenhuma'}")
        print("""
 1 📁 Escolher/criar projeto
 2 📂 Criar pasta
 3 📄 Criar arquivo
 4 ✏️ Escrever/alterar
 5 📖 Ler arquivo
 6 🗑️ Excluir
 7 📋 Listar
 8 ▶️ Executar comando
 9 💻 Abrir VS Code
 0 ❌ Sair
        """)
        op = input("Escolha: ").strip()
        if op == "0": break
        elif op == "1": print(escolher_projeto())
        elif op == "2": print(criar_pasta(input("Nome: ")))
        elif op == "3": print(criar_arquivo(input("Arquivo: "), input("Conteúdo: ")))
        elif op == "4":
            arq = input("Arquivo: ")
            txt = input("Texto: ")
            acresc = input("Acrescentar? (s/n): ").lower().strip() == "s"
            print(alterar_arquivo(arq, txt, acresc))
        elif op == "5": print(ler_arquivo(input("Arquivo: ")))
        elif op == "6": print(excluir_item(input("Nome: ")))
        elif op == "7": print(listar_projeto())
        elif op == "8": print(executar_comando(input("Comando: ")))
        elif op == "9": print(abrir_vscode())

if __name__ == "__main__":
    menu()
PYEOF

echo "[2/6] Criando INICIAR-AGENTE.bat..."
cat > INICIAR-AGENTE.bat << 'EOF'
@echo off
python agente_codigo.py
pause
EOF

echo "[3/6] Criando INICIAR-AGENTE.sh..."
cat > INICIAR-AGENTE.sh << 'EOF'
#!/bin/bash
python3 agente_codigo.py
EOF
chmod +x INICIAR-AGENTE.sh

echo "[4/6] Criando exemplo..."
mkdir -p projetos/exemplo_inicial
cat > projetos/exemplo_inicial/ola.py << 'EOF'
print("🤖 Agente funcionando!")
print("Tudo pronto!")
EOF

echo "[5/6] Criando LEIA-ME.txt..."
cat > LEIA-ME.txt << 'EOF'
AGENTE DE CÓDIGO — JARVIS
Use: python agente_codigo.py
EOF

echo "[6/6] Concluído!"
echo ""
echo "✅ Tudo criado! Digite para usar:"
echo "cd agente_codigo"
echo "python agente_codigo.py"
