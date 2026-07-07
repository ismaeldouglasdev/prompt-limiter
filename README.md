# Prompt Limiter

Auto-ajusta prompts para caber nos limites de tokens por minuto (TPM) de cada modelo. Evita erros como:

```
Request too large for model (TPM: Limit 12000, Requested 51505)
```

## Instalação

```bash
git clone https://github.com/ismaeldouglasdev/prompt-limiter.git
cd prompt-limiter
pip install -r requirements.txt
```

## Uso

```bash
# Truncar prompt para caber no limite
python3 prompt_limiter.py groq/llama-3.3-70b-versatile prompt.txt

# Via stdin
cat prompt.txt | python3 prompt_limiter.py groq/llama-3.3-70b-versatile -

# Dividir em chunks
python3 prompt_limiter.py groq/llama-3.3-70b-versatile prompt.txt --strategy split
```

## Estratégias

| Estratégia | Descrição | Quando usar |
|------------|-----------|-------------|
| `truncate` | Remove linhas do início até caber no limite | Default — mantém o final que é mais relevante |
| `split` | Divide em chunks processáveis separadamente | Quando precisa do prompt completo em partes |

## Arquivos

```
prompt-limiter/
├── prompt_limiter.py    # Limitador core
├── smart_router.py      # Wrapper com auto-detect de modelo
├── model_limits.json    # Database de limites por modelo
├── requirements.txt     # Dependências
└── README.md            # Esta documentação
```

## Modelos suportados

- Groq: llama-3.3-70b (12K TPM), llama-3.1-8b (30K), qwen3-32b (30K)
- NVIDIA NIM: minimax-m3 (1M TPM)
- Cloudflare Workers AI: llama-3.3-70b (180K)
- Ollama: gpt-oss:120b (ilimitado)
- Kiro/Antigravity: claude-sonnet-4.5 (400K TPM)

Para adicionar modelos, edite `model_limits.json`:

```json
{
  "models": {
    "novo/modelo": { "tpm": 50000, "rpm": 100, "context": 128000 }
  }
}
```

## Limitações

- Contagem de tokens é aproximada (~4 chars/token)
- Não considera tokens de resposta/sistema
- Sumarização via LLM não implementada (placeholder)

## Licença

MIT
