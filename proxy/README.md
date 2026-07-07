# Prompt Limiter Proxy

Middleware que intercepta requests OpenCode → 9router e limita prompts automaticamente.

## Como ativar

### 1. Iniciar o proxy

```bash
python3 proxy/proxy_server.py
```

Escuta na porta **20130** e encaminha pro 9router (porta 20128).

### 2. Configurar OpenCode

Edite `~/.config/opencode/opencode.json`:

```diff
"9router": {
-    "options": { "baseURL": "http://127.0.0.1:20128/v1" },
+    "options": { "baseURL": "http://127.0.0.1:20130/v1" },
}
```

### 3. Reiniciar OpenCode sessions

A partir da próxima sessão, todo request passará pelo limiter.

## O que faz

Quando o proxy detecta que um modelo tem TPM baixo (ex: Groq 70B = 12K TPM):

1. Conta tokens do prompt
2. Se exceder 75% do TPM, aplica truncagem
3. Adiciona marcador `_prompt_limited` no body
4. Encaminha request limitado para o 9router

## Logs

```
14:32:01 PROXY ⚠ groq/llama-3.3-70b-versatile: 33107t excede 12000 TPM — limitando...
14:32:01 PROXY   → 33107t → 8120t (12 msgs)
```

## Testar sem OpenCode

```bash
curl -X POST http://localhost:20130/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "groq/llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "teste"}]
  }'
```
