JARVIS - CONFIGURAÇÃO NVIDIA

1. Edite .env e coloque sua chave NVIDIA:
   NVIDIA_API_KEY=nvapi-...

2. Para usar várias chaves:
   NVIDIA_API_KEYS=nvapi-CHAVE1,nvapi-CHAVE2,nvapi-CHAVE3
   ou uma chave por linha.

3. Não é necessário informar um modelo. O Jarvis consulta /v1/models e tenta modelos disponíveis.
   Para fixar um modelo, use:
   NVIDIA_MODEL=nome/do/modelo

4. Execute INICIAR-JARVIS.bat.

5. Abra http://127.0.0.1:8000/interface.html

O Jarvis agora mantém contexto das últimas mensagens e envia para a NVIDIA qualquer pergunta que
não seja um comando local específico. Ele não depende de uma lista fechada de perguntas.
