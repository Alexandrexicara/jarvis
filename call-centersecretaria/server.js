const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const path = require('path');
require('dotenv').config();

const { BotManager } = require('./bot-manager');
const { perguntarIA } = require('./ia');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

const PORT = process.env.PORT || 3000;

app.use(express.static(path.join(__dirname, 'public')));

const botManager = new BotManager(io);

io.on('connection', (socket) => {
    console.log('🔗 Cliente conectado:', socket.id);
    
    socket.emit('log', { message: '🔗 Conectado ao servidor', type: 'success' });
    socket.emit('bots-list', botManager.getAllBots());

    socket.on('create-bot', ({ url, email, password, authType, apiProvider }) => {
        if (!url || !url.startsWith('http')) {
            socket.emit('log', { message: '⚠️ URL inválida', type: 'error' });
            return;
        }
        const credentials = (email && password) ? { email, password, authType } : { authType };
        const bot = botManager.criarBot(url, credentials, apiProvider || 'gemini');
        if (bot) {
            const hasCreds = !!(email && password);
            io.emit('bot-created', { botId: bot.id, url, hasCredentials: hasCreds, authType: authType || 'manual', apiProvider: apiProvider || 'gemini' });
        }
    });

    socket.on('start-bot', (id) => {
        botManager.iniciarBot(id);
    });

    socket.on('stop-bot', (id) => {
        botManager.pararBot(id);
    });

    socket.on('remove-bot', (id) => {
        botManager.removerBot(id);
        socket.emit('log', { message: `🗑️ Bot #${id} removido`, type: 'info' });
    });

    socket.on('disconnect', () => {
        console.log('🔌 Cliente desconectado:', socket.id);
    });

    // Chat de voz com IA - para conversas naturais
    socket.on('voice-chat', async ({ message, assistantName, apiProvider = 'gemini' }) => {
        console.log(`🎙️ [${assistantName}] Pergunta:`, message);
        
        try {
            // Cria um prompt personalizado para a assistente de voz
            const prompt = `Você é ${assistantName}, uma assistente virtual amigável e natural. 
Responda de forma conversacional, calorosa e humana em português do Brasil.
Mantenha respostas curtas (máximo 2-3 frases) pois será falada em voz alta.
Seja gentil e prestativa.

Usuário disse: "${message}"

Responda naturalmente:`;

            const resposta = await perguntarIA(prompt, apiProvider);
            console.log(`🎙️ [${assistantName}] Resposta:`, resposta);
            
            socket.emit('voice-chat-response', { 
                success: true, 
                response: resposta,
                assistantName 
            });
        } catch (error) {
            console.error('Erro no voice-chat:', error.message);
            socket.emit('voice-chat-response', { 
                success: false, 
                error: error.message,
                assistantName 
            });
        }
    });
});

server.listen(PORT, () => {
    console.log('╔════════════════════════════════════════╗');
    console.log('║     🤖 BOT IA AUTOMÁTICO               ║');
    console.log('╠════════════════════════════════════════╣');
    console.log(`║  🌐 Painel: http://localhost:${PORT}      ║`);
    console.log('╚════════════════════════════════════════╝');
});
