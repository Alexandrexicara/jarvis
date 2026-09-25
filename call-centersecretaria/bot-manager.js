const { chromium } = require('playwright');
const { perguntarIA } = require('./ia');
const fs = require('fs');
const path = require('path');

// Helpers para humanização
function randomDelay(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Diretório para salvar sessões
const SESSIONS_DIR = path.join(__dirname, 'sessions');
if (!fs.existsSync(SESSIONS_DIR)) {
    fs.mkdirSync(SESSIONS_DIR, { recursive: true });
}

const USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
];

class BotInstance {
    constructor(id, url, io, credentials = null, apiProvider = 'gemini') {
        this.id = id;
        this.url = url;
        this.io = io;
        this.credentials = credentials; // { email, password }
        this.apiProvider = apiProvider; // 'gemini', 'chatgpt', 'claude', 'deepseek', 'ollama'
        this.rodando = false;
        this.browser = null;
        this.page = null;
        this.context = null;
        this.status = 'stopped';
        this.sessionFile = path.join(SESSIONS_DIR, `bot_${id}_cookies.json`);
        this.noTaskCount = 0; // Contador de tentativas sem encontrar tarefas
        this.totalCompleted = 0; // Total de tarefas completadas
    }

    log(msg, type = 'info') {
        this.io.emit('bot-log', { botId: this.id, message: msg, type });
    }

    async saveSession() {
        try {
            if (this.context) {
                const storage = await this.context.storageState();
                fs.writeFileSync(this.sessionFile, JSON.stringify(storage));
                this.log('💾 Sessão salva', 'info');
            }
        } catch (err) {
            this.log(`⚠️ Erro ao salvar sessão: ${err.message}`, 'warning');
        }
    }

    async loadSession() {
        try {
            if (fs.existsSync(this.sessionFile)) {
                const storage = JSON.parse(fs.readFileSync(this.sessionFile, 'utf8'));
                this.log('📂 Sessão anterior carregada', 'info');
                return { storageState: storage };
            }
        } catch (err) {
            this.log(`⚠️ Erro ao carregar sessão: ${err.message}`, 'warning');
        }
        return {};
    }

    async iniciar() {
        if (this.rodando) {
            this.log('⚠️ Bot já está rodando', 'warning');
            return;
        }

        this.rodando = true;
        this.status = 'running';
        this.io.emit('bot-status', { botId: this.id, status: 'running' });
        this.log(`🚀 Iniciando Bot #${this.id} (IA: ${this.apiProvider.toUpperCase()})`, 'success');

        try {
            // User-agent aleatório
            const userAgent = USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
            
            this.browser = await chromium.launch({ 
                headless: false,
                args: [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            });
            
            const sessionData = await this.loadSession();
            
            this.context = await this.browser.newContext({
                userAgent: userAgent,
                viewport: { width: 1280, height: 720 },
                locale: 'pt-BR',
                timezoneId: 'America/Sao_Paulo',
                ...sessionData
            });
            
            this.page = await this.context.newPage();
            
            // Remove webdriver flag
            await this.page.addInitScript(() => {
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            });

            this.log(`🌐 Acessando: ${this.url}`, 'info');
            
            // Delay aleatório antes de navegar (parece usuário pensando)
            await sleep(randomDelay(1000, 3000));
            
            await this.page.goto(this.url, { waitUntil: 'networkidle', timeout: 60000 });
            
            // Verifica se precisa de login
            await this.verificarLogin();
            
            await sleep(randomDelay(2000, 5000));
            
            this.log('✅ Página carregada (humanizado)', 'success');

            await this.loopDeAutomacao();

        } catch (err) {
            this.log(`❌ Erro: ${err.message}`, 'error');
            this.status = 'error';
            this.io.emit('bot-status', { botId: this.id, status: 'error' });
        } finally {
            if (this.context) {
                await this.context.close();
            }
            if (this.browser) {
                await this.browser.close();
            }
            this.rodando = false;
            this.status = 'stopped';
            this.io.emit('bot-status', { botId: this.id, status: 'stopped' });
            this.log(`🛑 Bot #${this.id} parado`, 'info');
        }
    }

    async loopDeAutomacao() {
        while (this.rodando) {
            try {
                // Delay aleatório entre verificações (parece usuário casual)
                await sleep(randomDelay(3000, 8000));
                
                const pergunta = await this.detectarPergunta();
                
                if (pergunta) {
                    this.noTaskCount = 0; // Reset contador quando encontra tarefa
                    this.log(`❓ Pergunta detectada`, 'info');
                    
                    // Delay como se estivesse lendo/interpretando
                    await sleep(randomDelay(2000, 4000));
                    
                    this.log(`🤖 Consultando ${this.apiProvider.toUpperCase()}...`, 'info');
                    const resposta = await perguntarIA(pergunta, this.apiProvider);
                    this.log(`💡 ${this.apiProvider.toUpperCase()} gerou resposta`, 'success');
                    
                    // Delay como se estivesse digitando mentalmente
                    await sleep(randomDelay(1500, 3000));
                    
                    await this.preencherResposta(resposta);
                    
                    // Delay antes de enviar (revisando)
                    await sleep(randomDelay(1000, 2500));
                    
                    await this.enviarResposta();
                    this.totalCompleted++;
                    this.log(`✅ Resposta enviada! Total: ${this.totalCompleted}`, 'success');
                    
                    // Report a cada 5 tarefas
                    if (this.totalCompleted % 5 === 0) {
                        this.log(`📊 RELATÓRIO: ${this.totalCompleted} tarefas completadas!`, 'success');
                    }
                    
                    // Delay maior após enviar (esperando próxima)
                    await sleep(randomDelay(5000, 10000));
                } else {
                    // Não encontrou tarefa
                    this.noTaskCount++;
                    
                    // Avisa quando tentou várias vezes sem sucesso
                    if (this.noTaskCount === 10) {
                        this.log('📭 Nenhuma tarefa encontrada nas últimas 10 verificações.', 'warning');
                    } else if (this.noTaskCount === 30) {
                        this.log('📭⚠️ ATENÇÃO: Nenhuma tarefa encontrada nas últimas 30 verificações. Plataforma pode estar sem tarefas disponíveis.', 'warning');
                    }
                }
            } catch (e) {
                if (this.rodando) {
                    this.log(`⚠️ ${e.message}`, 'warning');
                    await sleep(randomDelay(5000, 8000));
                }
            }
        }
    }

    async verificarLogin() {
        // Verifica se há botões de login social primeiro
        const authType = this.credentials?.authType || 'manual';
        
        if (authType === 'google') {
            await this.clicarLoginSocial('google', ['text=Google', 'text=Continue with Google', '[data-provider="google"]']);
            return;
        }
        if (authType === 'github') {
            await this.clicarLoginSocial('github', ['text=GitHub', 'text=Continue with GitHub', '[data-provider="github"]']);
            return;
        }
        if (authType === 'facebook') {
            await this.clicarLoginSocial('facebook', ['text=Facebook', 'text=Continue with Facebook', '[data-provider="facebook"]']);
            return;
        }

        // Login tradicional com email/senha
        const loginSelectors = [
            'input[type="password"]',
            'input[name="password"]',
            '.login-form',
            'text=Sign in',
            'text=Login',
            'text=Entrar'
        ];

        for (const selector of loginSelectors) {
            try {
                const el = await this.page.locator(selector).first();
                if (await el.isVisible({ timeout: 2000 })) {
                    this.log('🔐 Página de login detectada', 'warning');
                    
                    if (this.credentials?.email && this.credentials?.password && authType === 'email') {
                        await this.efetuarLogin();
                    } else {
                        this.log(`⏳ Faça login ${authType === 'manual' ? 'manualmente' : 'com ' + authType}. Continuando em 60s...`, 'info');
                        await sleep(60000);
                        await this.saveSession();
                    }
                    return;
                }
            } catch { continue; }
        }
    }

    async clicarLoginSocial(provider, selectors) {
        this.log(`🔐 Procurando botão de login ${provider}...`, 'info');
        
        for (const selector of selectors) {
            try {
                const btn = await this.page.locator(selector).first();
                if (await btn.isVisible({ timeout: 3000 })) {
                    this.log(`👆 Clicando em "Continue with ${provider.charAt(0).toUpperCase() + provider.slice(1)}"...`, 'info');
                    await btn.click();
                    
                    this.log(`⏳ Complete o login no ${provider} no navegador. Aguardando 90s...`, 'warning');
                    await sleep(90000); // 90 segundos para login social
                    await this.saveSession();
                    this.log('✅ Login social concluído e sessão salva', 'success');
                    return;
                }
            } catch { continue; }
        }
        
        this.log(`⚠️ Botão ${provider} não encontrado. Faça login manual.`, 'warning');
        await sleep(60000);
        await this.saveSession();
    }

    async efetuarLogin() {
        try {
            this.log('🔑 Efetuando login automático com email...', 'info');
            
            const emailSelectors = ['input[type="email"]', 'input[name="email"]', 'input[name="username"]'];
            const passSelectors = ['input[type="password"]', 'input[name="password"]'];
            const btnSelectors = ['button[type="submit"]', 'button:has-text("Sign")', 'button:has-text("Login")', 'button:has-text("Entrar")'];

            // Preenche email
            for (const sel of emailSelectors) {
                try {
                    const el = await this.page.locator(sel).first();
                    if (await el.isVisible({ timeout: 1000 })) {
                        await el.fill(this.credentials.email, { timeout: 5000 });
                        break;
                    }
                } catch { continue; }
            }

            await sleep(randomDelay(500, 1500));

            // Preenche senha
            for (const sel of passSelectors) {
                try {
                    const el = await this.page.locator(sel).first();
                    if (await el.isVisible({ timeout: 1000 })) {
                        await el.fill(this.credentials.password, { timeout: 5000 });
                        break;
                    }
                } catch { continue; }
            }

            await sleep(randomDelay(800, 2000));

            // Clica no botão
            for (const sel of btnSelectors) {
                try {
                    const el = await this.page.locator(sel).first();
                    if (await el.isVisible({ timeout: 1000 })) {
                        await el.click();
                        break;
                    }
                } catch { continue; }
            }

            await sleep(5000); // Espera redirecionamento
            await this.saveSession();
            this.log('✅ Login efetuado e sessão salva', 'success');

        } catch (err) {
            this.log(`❌ Erro no login: ${err.message}`, 'error');
        }
    }

    async detectarPergunta() {
        // Primeiro verifica se há campo de senha (estamos em login)
        const hasPasswordField = await this.page.locator('input[type="password"]').first().isVisible({ timeout: 1000 }).catch(() => false);
        if (hasPasswordField) {
            this.log('⏳ Aguardando login...', 'warning');
            return null;
        }

        const seletores = [
            '.pergunta', '.question', '[data-testid="question"]',
            '.task-question', '.prompt-text', '.instruction-text',
            '.pergunta-texto', '.questao', '.enunciado',
            '[data-testid="task-content"]'
        ];

        for (const seletor of seletores) {
            try {
                const elemento = await this.page.locator(seletor).first();
                if (await elemento.isVisible({ timeout: 2000 })) {
                    const texto = await elemento.textContent();
                    
                    // Ignora textos de login/títulos genéricos
                    const ignorar = ['login', 'sign in', 'entrar', 'welcome', 'bem-vindo', 'loading', 'carregando'];
                    const textoLower = texto.toLowerCase().trim();
                    
                    if (ignorar.some(palavra => textoLower === palavra || textoLower.includes(palavra))) {
                        continue;
                    }
                    
                    // Só aceita se tiver pelo menos 20 caracteres (pergunta real)
                    if (texto.trim().length < 20) {
                        continue;
                    }
                    
                    await this.humanizedMouseMove(elemento);
                    return texto;
                }
            } catch { continue; }
        }
        return null;
    }

    async humanizedMouseMove(elemento) {
        try {
            const box = await elemento.boundingBox();
            if (box) {
                // Move mouse para posição aleatória próxima ao elemento
                const x = box.x + randomDelay(10, Math.max(11, box.width - 10));
                const y = box.y + randomDelay(10, Math.max(11, box.height - 10));
                await this.page.mouse.move(x, y, { steps: randomDelay(5, 15) });
            }
        } catch {
            // Ignora erro de movimento
        }
    }

    async preencherResposta(texto) {
        const seletores = ['textarea', 'input[type="text"]', '[contenteditable="true"]', '.resposta-input'];

        for (const seletor of seletores) {
            try {
                const campo = await this.page.locator(seletor).first();
                if (await campo.isVisible({ timeout: 2000 })) {
                    // Move mouse humanizado até o campo
                    await this.humanizedMouseMove(campo);
                    
                    // Clica com delay
                    await campo.click({ delay: randomDelay(100, 300) });
                    await sleep(randomDelay(300, 800));
                    
                    // Digitação com delay entre caracteres (humanizado)
                    await campo.fill(texto, { timeout: 30000 });
                    
                    // Pausa após digitar
                    await sleep(randomDelay(500, 1500));
                    return;
                }
            } catch { continue; }
        }
        throw new Error('Campo não encontrado');
    }

    async enviarResposta() {
        const seletores = [
            'button[type="submit"]', 'button:has-text("Enviar")',
            'button:has-text("Responder")', '.btn-enviar', 'input[type="submit"]'
        ];

        for (const seletor of seletores) {
            try {
                const botao = await this.page.locator(seletor).first();
                if (await botao.isVisible({ timeout: 2000 })) {
                    // Move mouse até o botão (humanizado)
                    await this.humanizedMouseMove(botao);
                    await sleep(randomDelay(300, 800));
                    
                    // Clica com delay realista
                    await botao.click({ delay: randomDelay(80, 250) });
                    return;
                }
            } catch { continue; }
        }
        throw new Error('Botão não encontrado');
    }

    parar() {
        this.rodando = false;
        this.status = 'stopped';
        this.io.emit('bot-status', { botId: this.id, status: 'stopped' });
        
        // Relatório final
        if (this.totalCompleted > 0) {
            this.log(`📊 RELATÓRIO FINAL Bot #${this.id}: ${this.totalCompleted} tarefas completadas`, 'success');
        }
        this.log('🛑 Bot parado', 'info');
    }
}

class BotManager {
    constructor(io) {
        this.io = io;
        this.bots = new Map();
        this.maxBots = 10;
    }

    criarBot(url, credentials = null, apiProvider = 'gemini') {
        const id = this.bots.size + 1;
        if (id > this.maxBots) {
            this.io.emit('error', 'Limite máximo de 10 bots atingido');
            return null;
        }

        const bot = new BotInstance(id, url, this.io, credentials, apiProvider);
        this.bots.set(id, bot);
        // Evento emitido pelo server.js para ter controle total dos dados
        return bot;
    }

    getBot(id) {
        return this.bots.get(id);
    }

    getAllBots() {
        return Array.from(this.bots.values()).map(bot => ({
            id: bot.id,
            url: bot.url,
            status: bot.status,
            hasCredentials: !!(bot.credentials?.email && bot.credentials?.password),
            authType: bot.credentials?.authType || 'manual',
            apiProvider: bot.apiProvider || 'gemini'
        }));
    }

    async iniciarBot(id) {
        const bot = this.bots.get(id);
        if (bot) {
            await bot.iniciar();
        }
    }

    pararBot(id) {
        const bot = this.bots.get(id);
        if (bot) {
            bot.parar();
        }
    }

    removerBot(id) {
        const bot = this.bots.get(id);
        if (bot) {
            bot.parar();
            this.bots.delete(id);
            this.io.emit('bot-removed', { botId: id });
        }
    }
}

module.exports = { BotManager };
