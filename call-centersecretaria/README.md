# 🤖 Multi Bot IA - Gerenciador

Sistema profissional para rodar **múltiplos bots simultâneos** em diferentes plataformas, cada um respondendo automaticamente usando IA (Gemini).

## ✨ Funcionalidades

- ✅ **Múltiplos bots** - Até 10 bots simultâneos
- ✅ **Plataformas diferentes** - Cada bot em um site independente
- ✅ **Controle individual** - Start/Stop por bot
- ✅ **Logs separados** - Identifica cada bot por ID
- ✅ **Interface moderna** - Painel web responsivo

## 📁 Estrutura

```
bot-ia/
├── server.js          # Servidor Express + Socket.io
├── bot-manager.js     # Gerenciador de múltiplos bots
├── ia.js              # Integração com Gemini API
├── .env               # Configurações (chave API)
├── package.json
└── public/
    └── index.html     # Painel de controle multi-bot
```

## 🚀 Instalação

```bash
# Instalar dependências
npm install

# Instalar navegadores do Playwright
npx playwright install chromium
```

## ⚙️ Configuração

Edite `.env`:
```env
GEMINI_API_KEY=sua_chave_aqui  # Obtenha em makersuite.google.com
```

## ▶️ Como usar

```bash
npm start
```

Abra: http://localhost:3000

### Interface:
1. **Adicione plataformas** - Digite a URL e clique "Adicionar Bot"
2. **Inicie cada bot** - Clique ▶ no card do bot
3. **Monitore logs** - Veja atividade de todos os bots
4. **Controle individual** - Pare ou remova bots específicos

## 🔧 Personalização

Edite `bot-manager.js` e ajuste os seletores CSS:

- `detectarPergunta()` → onde o bot procura perguntas
- `preencherResposta()` → campo de texto pra resposta
- `enviarResposta()` → botão de enviar

## 📋 Requisitos

- Node.js 16+
- Chave API Gemini (gratuita)
- RAM suficiente (cada bot abre um navegador)
