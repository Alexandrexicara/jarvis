# -*- coding: utf-8 -*-
"""
🧠 JARVIS — VERSÃO WEB FUNCIONANDO NO RENDER!
Acessa pelo navegador, não precisa digitar no terminal!
"""
import os
import subprocess
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
RAIZ = os.path.abspath(".")
PASTA_PROJETOS = os.path.join(RAIZ, "projetos")
PASTA_ATUAL = ""

os.makedirs(PASTA_PROJETOS, exist_ok=True)
os.makedirs("logs", exist_ok=True)

def escolher_projeto(nome):
    global PASTA_ATUAL
    PASTA_ATUAL = os.path.join(PASTA_PROJETOS, nome)
    os.makedirs(PASTA_ATUAL, exist_ok=True)
    return f"✅ Projeto '{nome}' pronto!"

def criar_parede_sorte():
    if not PASTA_ATUAL:
        return "❌ Primeiro: Cria um projeto chamado cassino"
    caminho = os.path.join(PASTA_ATUAL, "parede-sorte.html")
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
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(codigo)
    return "✅ Jogo criado! Acesse na pasta do projeto!"

def listar():
    if not PASTA_ATUAL:
        return "❌ Primeiro crie um projeto"
    return "📋 Arquivos:\n" + "\n".join(f"  - {i}" for i in sorted(os.listdir(PASTA_ATUAL)))

@app.route('/')
def home():
    return render_template_string('''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>🧠 JARVIS + AGENTE</title>
<style>
body{font-family:Segoe UI,sans-serif;background:#0a0a0a;color:#fff;padding:20px;max-width:800px;margin:0 auto;}
h1{color:#ff6a00;text-align:center;}
.terminal{background:#111;border:2px solid #39ff14;border-radius:10px;padding:20px;margin:20px 0;}
#entrada{width:70%;padding:12px;font-size:18px;background:#222;border:1px solid #39ff14;color:#fff;border-radius:5px;}
#btn{padding:12px 25px;font-size:18px;background:#39ff14;color:#000;border:none;border-radius:5px;cursor:pointer;font-weight:bold;}
#btn:hover{transform:scale(1.05);}
#saida{margin-top:20px;padding:15px;background:#1a1a1a;border-radius:5px;min-height:100px;white-space:pre-wrap;font-family:monospace;}
.exemplos{margin-top:30px;padding:15px;background:#1a1a1a;border-radius:5px;}
.exemplo{padding:8px 12px;margin:5px 0;background:#222;border-radius:5px;cursor:pointer;}
.exemplo:hover{background:#333;}
</style>
</head>
<body>
<h1>🧠 JARVIS + AGENTE — ONLINE!</h1>
<div class="terminal">
  <h3>Digite o que quer fazer:</h3>
  <input type="text" id="entrada" placeholder="Ex: Cria um projeto chamado cassino">
  <button id="btn">ENVIAR</button>
  <div id="saida">✅ Conectado! Digite seu pedido acima ↗</div>
</div>
<div class="exemplos">
  <h3>📋 Clique em um exemplo:</h3>
  <div class="exemplo" onclick="document.getElementById('entrada').value=this.textContent">Cria um projeto chamado cassino</div>
  <div class="exemplo" onclick="document.getElementById('entrada').value=this.textContent">Faz o jogo da parede da sorte</div>
  <div class="exemplo" onclick="document.getElementById('entrada').value=this.textContent">Lista os arquivos</div>
</div>
<script>
async function enviar(){
  const txt=document.getElementById('entrada').value;
  if(!txt.trim()) return;
  document.getElementById('saida').textContent='🔄 Processando...';
  const res=await fetch('/comando',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({fala:txt})
  });
  const d=await res.json();
  document.getElementById('saida').textContent=d.resposta;
}
document.getElementById('btn').onclick=enviar;
document.getElementById('entrada').onkeydown=e=>e.key==='Enter'&&enviar();
</script>
</body>
</html>
    ''')

@app.route('/comando', methods=['POST'])
def comando():
    dados = request.json
    fala = dados.get('fala', '').strip()
    f = fala.lower()
    resposta = "🤖 Não entendi. Tente: 'Cria um projeto chamado cassino'"
    
    if "projeto" in f or "chamado" in f:
        for p in ["projeto", "chamado", "cria", "criar"]:
            if p in f:
                nome = f.split(p)[-1].strip().strip('"').strip("'").strip()
                if nome:
                    resposta = escolher_projeto(nome)
                    break
    elif "parede" in f and "sorte" in f:
        resposta = criar_parede_sorte()
    elif "lista" in f or "mostra" in f:
        resposta = listar()
    
    return jsonify({"resposta": resposta})

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=porta)
