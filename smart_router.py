#!/usr/bin/env python3
"""
Smart Router Wrapper - Detecta modelo ativo e ajusta prompts automaticamente.
Integra com 9router para transparentemente limitar prompts antes de enviar.
"""
import json, sys, os
from pathlib import Path
from prompt_limiter import limit_prompt, get_model_limits, count_tokens

NINEROUTER_URL = os.environ.get("NINEROUTER_URL", "http://localhost:20128")
LIMITS_FILE = Path.home() / ".config/opencode/model_limits.json"

def get_active_model() -> str:
    """Detecta qual modelo está ativo no combo-round-robin."""
    # Por ora retorna do env ou default
    return os.environ.get("ACTIVE_MODEL", "groq/llama-3.3-70b-versatile")

def smart_route(prompt: str, model_override: str = None) -> str | list:
    """
    Roteia inteligentemente: detecta limites e ajusta prompt se necessário.
    
    Args:
        prompt: Texto do prompt
        model_override: Modelo específico (ou None para auto-detect)
    
    Returns:
        Prompt ajustado ou lista de chunks
    """
    model = model_override or get_active_model()
    limits = get_model_limits(model)
    current_tokens = count_tokens(prompt)
    max_tpm = limits.get("tpm", 30000)
    
    if current_tokens > max_tpm * 0.8:
        # Prompt grande - escolhe estratégia baseado no modelo
        if "groq" in model.lower() and "70b" in model.lower():
            # Groq 70B tem TPM baixo - split
            return limit_prompt(model, prompt, "split")
        else:
            # Outros modelos - truncate
            return limit_prompt(model, prompt, "truncate")
    
    return prompt

def main():
    """CLI para testar roteamento."""
    if len(sys.argv) < 2:
        print("Smart Router - Detecta e ajusta prompts automaticamente")
        print("\nUso: smart_router.py <prompt_file|prompt_text> [model_id]")
        print("\nExemplos:")
        print("  python3 smart_router.py prompt.txt")
        print("  python3 smart_router.py 'texto grande' groq/llama-3.3-70b-versatile")
        sys.exit(1)
    
    prompt_input = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else None
    
    if Path(prompt_input).exists():
        prompt = Path(prompt_input).read_text()
    else:
        prompt = prompt_input
    
    result = smart_route(prompt, model)
    
    print(f"Modelo: {model or get_active_model()}")
    print(f"Original: {count_tokens(prompt)} tokens")
    
    if isinstance(result, list):
        print(f"Resultado: {len(result)} chunks")
        for i, chunk in enumerate(result, 1):
            print(f"\n--- CHUNK {i} ({count_tokens(chunk)} tokens) ---")
            print(chunk[:500] + "..." if len(chunk) > 500 else chunk)
    else:
        print(f"Resultado: {count_tokens(result)} tokens")
        print("\n--- RESULTADO ---")
        print(result)

if __name__ == "__main__":
    main()
