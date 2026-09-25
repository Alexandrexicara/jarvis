const axios = require('axios');
require('dotenv').config();

const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY;
const OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434';

const PROVIDERS = {
    gemini: { name: 'Gemini', color: '🔵' },
    chatgpt: { name: 'ChatGPT', color: '🟢' },
    claude: { name: 'Claude', color: '🟣' },
    deepseek: { name: 'DeepSeek', color: '🔴' },
    ollama: { name: 'Ollama', color: '🟤' }
};

async function perguntarIA(texto, provider = 'gemini') {
    const prompt = `Responda de forma objetiva, natural e concisa em português:\n${texto}`;
    
    switch (provider.toLowerCase()) {
        case 'gemini':
            return await perguntarGemini(prompt);
        case 'chatgpt':
        case 'openai':
            return await perguntarChatGPT(prompt);
        case 'claude':
        case 'anthropic':
            return await perguntarClaude(prompt);
        case 'deepseek':
            return await perguntarDeepSeek(prompt);
        case 'ollama':
            return await perguntarOllama(prompt);
        default:
            return await perguntarGemini(prompt);
    }
}

async function perguntarGemini(prompt) {
    if (!GEMINI_API_KEY || GEMINI_API_KEY === 'SUA_CHAVE_GEMINI_AQUI') {
        throw new Error('GEMINI_API_KEY não configurada no arquivo .env');
    }

    try {
        const response = await axios.post(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.0-pro:generateContent?key=${GEMINI_API_KEY}`,
            {
                contents: [{ parts: [{ text: prompt }] }]
            },
            { headers: { 'Content-Type': 'application/json' } }
        );

        if (response.data.candidates?.[0]?.content?.parts?.[0]) {
            return response.data.candidates[0].content.parts[0].text;
        }
        return 'Resposta não encontrada';
    } catch (err) {
        console.error('Erro Gemini:', err.response?.data || err.message);
        throw new Error(`Erro na API Gemini: ${err.response?.data?.error?.message || err.message}`);
    }
}

async function perguntarChatGPT(prompt) {
    if (!OPENAI_API_KEY || OPENAI_API_KEY === 'SUA_CHAVE_OPENAI_AQUI') {
        throw new Error('OPENAI_API_KEY não configurada no arquivo .env - Adicione sua chave da OpenAI');
    }

    try {
        const response = await axios.post(
            'https://api.openai.com/v1/chat/completions',
            {
                model: 'gpt-3.5-turbo',
                messages: [{ role: 'user', content: prompt }],
                temperature: 0.7
            },
            {
                headers: {
                    'Authorization': `Bearer ${OPENAI_API_KEY}`,
                    'Content-Type': 'application/json'
                }
            }
        );

        return response.data.choices?.[0]?.message?.content || 'Resposta não encontrada';
    } catch (err) {
        console.error('Erro ChatGPT:', err.response?.data || err.message);
        throw new Error(`Erro na API ChatGPT: ${err.response?.data?.error?.message || err.message}`);
    }
}

async function perguntarClaude(prompt) {
    if (!ANTHROPIC_API_KEY || ANTHROPIC_API_KEY === 'SUA_CHAVE_ANTHROPIC_AQUI') {
        throw new Error('ANTHROPIC_API_KEY não configurada no arquivo .env - Adicione sua chave do Anthropic');
    }

    try {
        const response = await axios.post(
            'https://api.anthropic.com/v1/messages',
            {
                model: 'claude-3-haiku-20240307',
                max_tokens: 1024,
                messages: [{ role: 'user', content: prompt }]
            },
            {
                headers: {
                    'x-api-key': ANTHROPIC_API_KEY,
                    'anthropic-version': '2023-06-01',
                    'Content-Type': 'application/json'
                }
            }
        );

        return response.data.content?.[0]?.text || 'Resposta não encontrada';
    } catch (err) {
        console.error('Erro Claude:', err.response?.data || err.message);
        throw new Error(`Erro na API Claude: ${err.response?.data?.error?.message || err.message}`);
    }
}

async function perguntarDeepSeek(prompt) {
    if (!DEEPSEEK_API_KEY || DEEPSEEK_API_KEY === 'SUA_CHAVE_DEEPSEEK_AQUI') {
        throw new Error('DEEPSEEK_API_KEY não configurada no arquivo .env - Adicione sua chave do DeepSeek');
    }

    try {
        const response = await axios.post(
            'https://api.deepseek.com/v1/chat/completions',
            {
                model: 'deepseek-chat',
                messages: [{ role: 'user', content: prompt }],
                temperature: 0.7
            },
            {
                headers: {
                    'Authorization': `Bearer ${DEEPSEEK_API_KEY}`,
                    'Content-Type': 'application/json'
                }
            }
        );

        return response.data.choices?.[0]?.message?.content || 'Resposta não encontrada';
    } catch (err) {
        console.error('Erro DeepSeek:', err.response?.data || err.message);
        throw new Error(`Erro na API DeepSeek: ${err.response?.data?.error?.message || err.message}`);
    }
}

async function perguntarOllama(prompt) {
    try {
        const response = await axios.post(
            `${OLLAMA_URL}/api/generate`,
            {
                model: process.env.OLLAMA_MODEL || 'llama2',
                prompt: prompt,
                stream: false
            },
            {
                headers: { 'Content-Type': 'application/json' },
                timeout: 60000
            }
        );

        return response.data.response || 'Resposta não encontrada';
    } catch (err) {
        console.error('Erro Ollama:', err.message);
        throw new Error(`Erro no Ollama: Verifique se está rodando em ${OLLAMA_URL} | ${err.message}`);
    }
}

module.exports = { perguntarIA, PROVIDERS };
