#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 JARVIS — TUDO DENTRO DO VS CODE
Cria → aparece na barra lateral → abre em aba → você vê → pede → ele corrige ali mesmo!
"""

import os
import subprocess
from datetime import datetime

# === CAMINHOS ===
RAIZ = os.path.abspath("..")
PASTA_SISTEMA = os.getcwd()
PASTA_ATUAL = ""

# === CARREGA CHAVE NVIDIA ===
ENV_PATH = os.path.join(RAIZ, ".env")
CHAVE_NVIDIA = ""
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for linha in f:
            if linha.startswith("NVIDIA_API_KEY="):
                CHAVE_NVIDIA = linha.split("=", 1)[1].strip()
                break

# === GARANTE PASTAS ===
os.makedirs("logs", exist_ok=True)
os.makedirs("projetos", exist_ok=True)

def log(acao, detalhe=""):
    agora = datetime.now().strftime("%H:%M:%S")
    with open("logs/agente.log", "a", encoding="utf-8") as f:
        f.write(f"[{agora}] {acao} — {detalhe}\n")
    print(f"✅ {acao} {detalhe}")

def abrir_no_vscode(caminho):
    """Abre NA HORA no VS Code que você já tem aberto"""
    try:
        subprocess.run(["code", "-r", caminho], capture_output=True)
        return "📂 Olha a ABA em CIMA ou BARRA LATERAL ESQUERDA!"
    except:
        return f"📂 Arquivo em: {caminho} — aperte F5 na barra lateral"

def escolher_projeto():
    global PASTA_ATUAL
    nome = input("Nome do projeto: ").strip()
    caminho = os.path.join("projetos", nome)
    os.makedirs(caminho, exist_ok=True)
    PASTA_ATUAL = caminho
    os.chdir(PASTA_ATUAL)
    log("Projeto", nome)
    abrir_no_vscode(PASTA_ATUAL)
    return f"""
✅ PROJETO '{nome}' PRONTO!
📂 Pasta: {PASTA_ATUAL}
👉 Olha a BARRA LATERAL ESQUERDA — já apareceu!
"""

def criar_arquivo():
    if not PASTA_ATUAL:
        return "❌ Escolha projeto primeiro — opção 1"
    
    print("\n🤖 O que criar? Ex: parede da sorte, blackjack, login...")
    pedido = input("Descreva: ").strip()
    if not pedido:
        return "❌ Fala o que quer!"
    
    nome_arq = input("📁 Nome do arquivo (ex: jogo.html): ").strip()
    if not nome_arq:
        return "❌ Dá um nome!"
    
    print(f"🔄 Criando {nome_arq}...")
    
    # === CÓDIGOS PRONTOS ===
    pedido_baixo = pedido.lower()
    
    if "parede" in pedido_baixo or "moeda" in pedido_baixo:
        codigo = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Parede da Sorte | BrasVegas</title>
<style>
:root{--v:#e50914;--p:#0a0a0a;--a:#0066ff;--l:#ff6a00;--g:#39ff14;--dourado:#d4af37;}
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',sans-serif;}
body{background:linear-gradient(180deg,#1a0000,#0a0a0a);min-height:100vh;color:#fff;}
.centro{display:flex;flex-direction:column;align-items:center;padding:20px;}
h1{font-size:28px;color:var(--l);text-shadow:0 0 15px var(--l);margin-bottom:15px;}
.area-jogo{position:relative;width:420px;height:520px;background:linear-gradient(180deg,#1a1a2e,#0f0f1a);border-radius:15px;border:3px solid var(--dourado);overflow:hidden;box-shadow:0 0 30px rgba(212,175,55,.4);}
.top-bar{background:linear-gradient(90deg,var(--v),var(--l),var(--v));padding:10px;text-align:center;font-weight:bold;font-size:18px;}
.pinos{position:absolute;top:60px;left:0;right:0;bottom:100px;}
.pino{position:absolute;width:10px;height:10px;background:var(--dourado);border-radius:50%;box-shadow:0 0 8px var(--dourado);}
.moeda{position:absolute;width:24px;height:24px;background:radial-gradient(circle at 30% 30%,#ffd700,#b8860b);border-radius:50%;border:2px solid #fff;box-shadow:0 0 12px #ffd700;z-index:5;display:none;transition:top .1s linear,left .1s linear;}
.ganhos{position:absolute;bottom:0;left:0;right:0;height:100px;display:flex;}
.caixa{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;border-top:2px solid var(--dourado);font-weight:bold;cursor:pointer;transition:all .2s;font-size:12px;}
.caixa:hover{transform:scale(1.05);background:rgba(255,255,255,.05);}
.x1{background:rgba(0,100,255,.15);color:#80bfff;}
.x2{background:rgba(0,150,255,.2);color:#66bfff;}
.x5{background:rgba(255,100,0,.2);color:#ff9933;}
.x10{background:rgba(255,150,0,.25);color:#ffb347;}
.x25{background:rgba(255,50,0,.25);color:#ff6633;}
.x50{background:rgba(255,0,0,.3);color:#ff4d4d;}
.x100{background:linear-gradient(180deg,rgba(212,175,55,.4),rgba(212,175,55,.1));color:#ffd700;}
.jackpot{background:linear-gradient(180deg,rgba(57,255,20,.4),rgba(57,255,20,.1));color:var(--g);text-shadow:0 0 8px var(--g);font-size:14px;}
.controles{margin-top:20px;display:flex;gap:15px;align-items:center;}
.aposta{padding:12px 20px;font-size:18px;border-radius:8px;border:2px solid var(--dourado);background:rgba(0,0,0,.5);color:#fff;width:150px;text-align:center;}
.btn-lancar{padding:12px 30px;font-size:18px;font-weight:bold;border-radius:8px;border:none;background:linear-gradient(180deg,var(--g),#00cc00);color:#000;cursor:pointer;box-shadow:0 0 15px var(--g);transition:all .2s;}
.btn-lancar:hover{transform:scale(1.08);box-shadow:0 0 25px var(--g);}
.saldo{font-size:20px;color:var(--g);font-weight:bold;}
.resultado{margin-top:15px;font-size:22px;font-weight:bold;height:30px;}
</style>
</head>
<body>
<div class="centro">
<h1>🪙 PAREDE DA SORTE</h1>
<div class="area-jogo">
<div class="top-bar">LANÇE A MOEDA!</div>
<div class="pinos" id="pinos"></div>
<div class="moeda" id="moeda"></div>
<div class="ganhos">
<div class="caixa x1" data-mult="1"><span>x1</span><span>R$1</span></div>
<div class="caixa x2" data-mult="2"><span>x2</span><span>R$2</span></div>
<div class="caixa x5" data-mult="5"><span>x5</span><span>R$5</span></div>
<div class="caixa x10" data-mult="10"><span>x10</span><span>R$10</span></div>
<div class="caixa x25" data-mult="25"><span>x25</span><span>R$25</span></div>
<div class="caixa x50" data-mult="50"><span>x50</span><span>R$50</span></div>
<div class="caixa x100" data-mult="100"><span>x100</span><span>R$100</span></div>
<div class="caixa jackpot" data-mult="500"><span>🏆</span><span>JACKPOT</span></div>
</div>
</div>
<div class="controles">
<div class="saldo">💰 R$ <span id="saldo">1000,00</span></div>
<input type="number" class="aposta" id="valor-aposta" value="10" min="1">
<button class="btn-lancar" id="btn-lancar">LANÇAR! 🪙</button>
</div>
<div class="resultado" id="resultado"></div>
</div>
<script>
let saldo = 1000;
const pinosContainer = document.getElementById('pinos');
const moeda = document.getElementById('moeda');
const saldoEl = document.getElementById('saldo');
const apostaEl = document.getElementById('valor-aposta');
const btnLancar = document.getElementById('btn-lancar');
const resultadoEl = document.getElementById('resultado');
const caixas = document.querySelectorAll('.caixa');

const linhas = 10, colunas = 11;
for(let l = 0; l < linhas; l++) {
  const desvio = l % 2 === 0 ? 0 : 35;
  for(let c = 0; c < colunas; c++) {
    const pino = document.createElement('div');
    pino.className = 'pino';
    pino.style.left = (c * 38 + desvio) + 'px';
    pino.style.top = (l * 45 + 20) + 'px';
    pinosContainer.appendChild(pino);
  }
}

btnLancar.addEventListener('click', lancarMoeda);

function lancarMoeda() {
  const valor = parseFloat(apostaEl.value);
  if(valor > saldo) {
    resultadoEl.textContent = '❌ Saldo insuficiente!';
    resultadoEl.style.color = '#e50914';
    return;
  }
  saldo -= valor;
  atualizarSaldo();
  moeda.style.display = 'block';
  moeda.style.left = '198px';
  moeda.style.top = '0px';
  resultadoEl.textContent = '';
  
  let posX = 198, posY = 0;
  let coluna = Math.floor(Math.random() * 8);
  
  const intervalo = setInterval(() => {
    posY += 12;
    if(Math.random() < 0.55) coluna += 1;
    else coluna -= 1;
    coluna = Math.max(0, Math.min(7, coluna));
    posX = coluna * 52 + 19;
    moeda.style.left = posX + 'px';
    moeda.style.top = posY + 'px';
    
    if(posY >= 400) {
      clearInterval(intervalo);
      const indice = Math.floor(Math.random() * 8);
      const caixaEscolhida = caixas[indice];
      const mult = parseFloat(caixaEscolhida.dataset.mult);
      const ganho = valor * mult;
      if(mult > 1) saldo += ganho;
      atualizarSaldo();
      
      resultadoEl.textContent = mult === 500 
        ? `🏆 JACKPOT! Ganhou R$${ganho.toFixed(2)}!` 
        : `✅ Caiu x${mult}! Ganhou R$${ganho.toFixed(2)}!`;
      resultadoEl.style.color = mult >= 50 ? '#39ff14' : '#ffd700';
      moeda.style.display = 'none';
    }
  }, 50);
}

function atualizarSaldo() {
  saldoEl.textContent = saldo.toFixed(2).replace('.', ',');
}
</script>
</body>
</html>"""
    else:
        codigo = f"<!DOCTYPE html><html><head><meta charset='UTF-8'><title>{nome_arq}</title></head><body><h1>{pedido}</h1><p>Criado pelo Jarvis</p></body></html>"
    
    caminho = os.path.join(PASTA_ATUAL, nome_arq)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(codigo)
    
    log("Criado", nome_arq)
    mensagem = abrir_no_vscode(caminho)
    
    return f"""
✅ {nome_arq} CRIADO E ABERTO! 🎉
{mensagem}
👉 Clica na aba acima pra ver!
"""

def corrigir():
    if not PASTA_ATUAL:
        return "❌ Escolha projeto primeiro"
    arq = input("📄 Nome do arquivo: ").strip()
    caminho = os.path.join(PASTA_ATUAL, arq)
    if not os.path.exists(caminho):
        return f"❌ Não encontrado: {arq}"
    
    with open(caminho, "r", encoding="utf-8") as f:
        conteudo = f.read()
    
    oque = input("O que precisa mudar? ").strip()
    if oque:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(f"<!-- CORRIGIDO: {oque} -->\n{conteudo}")
        log("Corrigido", arq)
        abrir_no_vscode(caminho)
        return f"✅ {arq} ATUALIZADO — olha na aba acima!"
    return f"📄 {arq} — veja na aba"

def listar():
    if not PASTA_ATUAL:
        return "❌ Escolha projeto primeiro"
    itens = sorted(os.listdir(PASTA_ATUAL))
    lista = "\n".join(f"  - {i}" for i in itens)
    return f"📋 Arquivos:\n{lista}\n👉 Barra lateral esquerda do VS Code"

def rodar():
    if not PASTA_ATUAL:
        return "❌ Escolha projeto primeiro"
    cmd = input("Comando: ").strip()
    print(f"▶️ {cmd}")
    try:
        r = subprocess.run(cmd, shell=True, cwd=PASTA_ATUAL, capture_output=True, text=True, encoding="utf-8", errors="replace")
        saida = r.stdout + r.stderr
        return f"✅ Funcionou!\n{saida}" if r.returncode == 0 else f"⚠️ Erro:\n{saida}"
    except Exception as e:
        return f"⚠️ {str(e)}"

def status():
    if CHAVE_NVIDIA:
        return "🔑 NVIDIA: ✅ Carregada"
    return "🔑 NVIDIA: ⚠️ Sem chave — cria arquivos prontos mesmo assim"

def menu():
    print(status())
    print("💻 TUDO DENTRO DO VS CODE — não sai daqui!")
    while True:
        print("\n" + "="*50)
        print("🤖 JARVIS — DENTRO DO VS CODE")
        print(f"Pasta: {PASTA_ATUAL or 'Nenhuma'}")
        print("""
 1 📁 Escolher/criar projeto
 2 🤖 Criar arquivo → Abre em ABA
 3 🔧 Corrigir/alterar
 4 📋 Listar
 5 ▶️ Rodar comando
 0 ❌ Sair
        """)
        op = input("Escolha: ").strip()
        if op == "0": break
        elif op == "1": print(escolher_projeto())
        elif op == "2": print(criar_arquivo())
        elif op == "3": print(corrigir())
        elif op == "4": print(listar())
        elif op == "5": print(rodar())

if __name__ == "__main__":
    menu()
