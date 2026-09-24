# -*- coding: utf-8 -*-
"""Compatibilidade: este entrypoint agora delega para o JARVIS principal."""

from jarvis import *  # noqa: F401,F403

raise SystemExit(0)

# -*- coding: utf-8 -*-
"""
🧠 JARVIS + AGENTE — INTEGRADOS E FUNCIONANDO!
JARVIS = Você fala → AGENTE executa, instala, corrige
"""
import os
import sys
import subprocess
from datetime import datetime

RAIZ = os.path.abspath(".")
PASTA_PROJETOS = os.path.join(RAIZ, "projetos")
PASTA_ATUAL = ""

os.makedirs(PASTA_PROJETOS, exist_ok=True)
os.makedirs("logs", exist_ok=True)

# ==============================================
# 🤖 AGENTE — EXECUTA, CRIA, INSTALA, CORRIGE
# ==============================================
class Agente:
    def __init__(self, pasta_alvo):
        self.pasta = pasta_alvo
        os.makedirs(self.pasta, exist_ok=True)

    def executar_comando(self, cmd):
        """Roda comando na pasta do projeto e retorna resultado"""
        print(f"🔧 AGENTE EXECUTA: {cmd}")
        try:
            res = subprocess.run(
                cmd, shell=True, cwd=self.pasta,
                capture_output=True, text=True, encoding='utf-8'
            )
            saida = res.stdout + res.stderr
            if res.returncode == 0:
                print(f"✅ SUCESSO:\n{saida}")
                return True, saida
            else:
                print(f"⚠️ ERRO — AGENTE CORRIGINDO...\n{saida}")
                return False, saida
        except Exception as e:
            print(f"❌ FALHA: {e}")
            return False, str(e)

    def criar_arquivo(self, nome, conteudo):
        """Cria arquivo na pasta do projeto"""
        caminho = os.path.join(self.pasta, nome)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        print(f"📄 AGENTE CRIOU: {nome}")
        return True

    def instalar_deps(self):
        """Roda npm install e corrige se der erro"""
        print("📦 AGENTE: Instalando dependências...")
        ok, saida = self.executar_comando("npm install")
        if not ok:
            if "npm" in saida.lower() and "not found" in saida.lower():
                return False, "Instale o Node.js primeiro: https://nodejs.org/"
            ok, saida = self.executar_comando("npm install --legacy-peer-deps")
        return ok, saida

    def rodar_servidor(self):
        """Inicia o servidor"""
        print("🚀 AGENTE: Iniciando servidor...")
        return self.executar_comando("npm start")

    def listar_arquivos(self):
        """Mostra tudo que tem no projeto"""
        arquivos = sorted(os.listdir(self.pasta))
        return "\n".join(f"  - {a}" for a in arquivos)

# ==============================================
# 🧠 JARVIS — CÉREBRO QUE RECEBE E COMUNICA
# ==============================================
agente = None

def set_projeto(nome):
    global agente, PASTA_ATUAL
    PASTA_ATUAL = os.path.join(PASTA_PROJETOS, nome)
    agente = Agente(PASTA_ATUAL)
    return f"""
✅ JARVIS: Projeto '{nome}' criado!
🤝 AGENTE conectado e trabalhando em: {PASTA_ATUAL}
Digite o que quer fazer:
- "Cria o jogo da parede da sorte"
- "Instala tudo"
- "Rodar o projeto"
- "Lista os arquivos"
- "Corrige os erros"
"""

def criar_parede_sorte():
    if not agente:
        return "❌ JARVIS: Primeiro digite: Cria um projeto chamado cassino"
    
    codigo = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Parede da Sorte | BrasVegas</title>
<style>
:root{--v:#e50914;--p:#0a0a0a;--l:#ff6a00;--g:#39ff14;--d:#d4af37;}
*{margin:0;padding:0;box-sizing:border-box;font-family:Segoe UI,sans-serif;}
body{background:linear-gradient(180deg,#1a0000,#0a0a0a);min-height:100vh;color:#fff;}
.centro{display:flex;flex-direction:column;align-items:center;padding:20px;}
h1{font-size:28px;color:var(--l);text-shadow:0 0 15px var(--l);margin-bottom:15px;}
.jogo{width:420px;height:520px;background:linear-gradient(180deg,#1a1a2e,#0f0f1a);border-radius:15px;border:3px solid var(--d);position:relative;overflow:hidden;}
.topo{background:linear-gradient(90deg,var(--v),var(--l),var(--v));padding:10px;text-align:center;font-weight:bold;font-size:18px;}
.pinos{position:absolute;top:60px;left:0;right:0;bottom:100px;}
.pino{position:absolute;width:10px;height:10px;background:var(--d);border-radius:50%;}
.moeda{position:absolute;width:24px;height:24px;background:radial-gradient(circle at 30% 30%,#ffd700,#b8860b);border-radius:50%;border:2px solid #fff;display:none;z-index:5;}
.caixas{position:absolute;bottom:0;left:0;right:0;height:100px;display:flex;}
.caixa{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;border-top:2px solid var(--d);font-weight:bold;cursor:pointer;}
.caixa:hover{transform:scale(1.05);background:rgba(255,255,255,.05);}
.x1{background:rgba(0,100,255,.15);color:#80bfff;}
.x2{background:rgba(0,150,255,.2);color:#66bfff;}
.x5{background:rgba(255,100,0,.2);color:#ff9933;}
.x10{background:rgba(255,150,0,.25);color:#ffb347;}
.x25{background:rgba(255,50,0,.25);color:#ff6633;}
.x50{background:rgba(255,0,0,.3);color:#ff4d4d;}
.x100{background:linear-gradient(180deg,rgba(212,175,55,.4),rgba(212,175,55,.1));color:#ffd700;}
.jackpot{background:linear-gradient(180deg,rgba(57,255,20,.4),rgba(57,255,20,.1));color:var(--g);}
.ctrls{margin-top:20px;display:flex;gap:15px;align-items:center;}
.saldo{font-size:20px;color:var(--g);font-weight:bold;}
.aposta{padding:12px 20px;font-size:18px;border-radius:8px;border:2px solid var(--d);background:rgba(0,0,0,.5);color:#fff;width:150px;text-align:center;}
.btn{padding:12px 30px;font-size:18px;font-weight:bold;border-radius:8px;border:none;background:linear-gradient(180deg,var(--g),#00cc00);color:#000;cursor:pointer;}
.btn:hover{transform:scale(1.08);}
.res{margin-top:15px;font-size:22px;font-weight:bold;min-height:30px;}
</style>
</head>
<body>
<div class="centro">
<h1>🪙 PAREDE DA SORTE</h1>
<div class="jogo">
<div class="topo">LANÇE A MOEDA!</div>
<div class="pinos" id="p"></div>
<div class="moeda" id="m"></div>
<div class="caixas">
<div class="caixa x1" data-m="1"><span>x1</span><span>R$1</span></div>
<div class="caixa x2" data-m="2"><span>x2</span><span>R$2</span></div>
<div class="caixa x5" data-m="5"><span>x5</span><span>R$5</span></div>
<div class="caixa x10" data-m="10"><span>x10</span><span>R$10</span></div>
<div class="caixa x25" data-m="25"><span>x25</span><span>R$25</span></div>
<div class="caixa x50" data-m="50"><span>x50</span><span>R$50</span></div>
<div class="caixa x100" data-m="100"><span>x100</span><span>R$100</span></div>
<div class="caixa jackpot" data-m="500"><span>🏆</span><span>JACKPOT</span></div>
</div>
</div>
<div class="ctrls">
<div class="saldo">💰 R$ <span id="s">1000,00</span></div>
<input type="number" class="aposta" id="a" value="10" min="1">
<button class="btn" id="b">LANÇAR!</button>
</div>
<div class="res" id="r"></div>
</div>
<script>
let saldo=1000;
const pinos=document.getElementById('p'),moeda=document.getElementById('m'),saldoEl=document.getElementById('s'),aposta=document.getElementById('a'),btn=document.getElementById('b'),res=document.getElementById('r'),caixas=document.querySelectorAll('.caixa');
for(let l=0;l<10;l++){
  const d=l%2===0?0:35;
  for(let c=0;c<11;c++){
    const p=document.createElement('div');p.className='pino';p.style.left=(c*38+d)+'px';p.style.top=(l*45+20)+'px';pinos.appendChild(p);
  }
}
btn.onclick=()=>{
  const v=parseFloat(aposta.value);
  if(v>saldo){res.textContent='❌ Sem saldo!';res.style.color='#e50914';return;}
  saldo-=v;saldoEl.textContent=saldo.toFixed(2).replace('.',',');
  moeda.style.display='block';moeda.style.left='198px';moeda.style.top='0px';res.textContent='';
  let x=198,y=0,col=Math.floor(Math.random()*8);
  const i=setInterval(()=>{
    y+=12;col+=Math.random()<.55?1:-1;col=Math.max(0,Math.min(7,col));x=col*52+19;
    moeda.style.left=x+'px';moeda.style.top=y+'px';
    if(y>=400){
      clearInterval(i);
      const c=caixas[Math.floor(Math.random()*8)],m=parseFloat(c.dataset.m),g=v*m;
      if(m>1)saldo+=g;saldoEl.textContent=saldo.toFixed(2).replace('.',',');
      res.textContent=m===500?`🏆 JACKPOT! R$${g.toFixed(2)}!`:`✅ Caiu x${m}! R$${g.toFixed(2)}!`;
      res.style.color=m>=50?'#39ff14':'#ffd700';moeda.style.display='none';
    }
  },50);
};
</script>
</body>
</html>"""
    agente.criar_arquivo("parede-sorte.html", codigo)
    return "✅ JARVIS: Jogo criado! AGENTE colocou na pasta do projeto!"

def criar_package_json():
    if not agente:
        return "❌ JARVIS: Primeiro crie o projeto"
    pkg = '''{
  "name": "brasvegas",
  "version": "1.0.0",
  "description": "Plataforma de Jogos",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.19.2"
  }
}'''
    agente.criar_arquivo("package.json", pkg)
    return "✅ JARVIS: package.json criado!"

print("""
╔═════════════════════════════════════════════════════════╗
║   🧠 JARVIS + AGENTE — CONECTADOS E FUNCIONANDO!          ║
║                                                           ║
║   JARVIS = Você fala → AGENTE = executa na pasta          ║
║                                                           ║
║   Comandos:                                                ║
║   "Cria um projeto chamado cassino"                       ║
║   "Cria o jogo da parede da sorte"                        ║
║   "Cria o package.json"                                   ║
║   "Instala as dependências"                               ║
║   "Lista os arquivos"                                     ║
║   "Sair"                                                   ║
╚═════════════════════════════════════════════════════════╝
""")

while True:
    fala = input("🤖 JARVIS > ").strip()
    if not fala:
        continue
    f = fala.lower()

    if "sair" in f or "encerrar" in f:
        print("👋 JARVIS: Encerrando conexão com AGENTE... Até logo!")
        break

    if "projeto" in f or "chamado" in f:
        for p in ["projeto", "chamado", "cria", "criar"]:
            if p in f:
                nome = f.split(p)[-1].strip().strip('"').strip("'").strip()
                if nome:
                    print(set_projeto(nome))
                    break
        continue

    if "parede" in f and "sorte" in f:
        print(criar_parede_sorte())
        continue

    if "package" in f or "json" in f:
        print(criar_package_json())
        continue

    if "instal" in f or "dependência" in f or "deps" in f:
        if not agente:
            print("❌ JARVIS: Primeiro crie o projeto")
            continue
        ok, saida = agente.instalar_deps()
        if ok:
            print("✅ JARVIS: Tudo instalado com sucesso!")
        else:
            print(f"⚠️ JARVIS: AGENTE relatou — {saida[:300]}...")
        continue

    if "lista" in f or "mostra" in f:
        if not agente:
            print("❌ JARVIS: Primeiro crie o projeto")
            continue
        print(f"📋 JARVIS: Arquivos do projeto:\n{agente.listar_arquivos()}")
        continue

    print(f"🤖 JARVIS: Entendi — '{fala}'\n🔧 AGENTE trabalhando...")
