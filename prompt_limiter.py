#!/usr/bin/env python3
"""
Prompt Limiter - Ajusta automaticamente prompts para caber nos limites do modelo.
Uso: python3 prompt_limiter.py <model_id> <prompt_file> [--strategy truncate|summarize|split]
"""
import json, sys, os
from pathlib import Path

LIMITS_FILE = Path.home() / ".config/opencode/model_limits.json"

def load_limits():
    if LIMITS_FILE.exists():
        return json.loads(LIMITS_FILE.read_text())
    return {"models": {}, "default_limits": {"tpm": 30000, "rpm": 60, "context": 8192}}

def count_tokens(text: str) -> int:
    """Conta tokens aproximados (4 chars ≈ 1 token)."""
    return len(text) // 4

def get_model_limits(model_id: str) -> dict:
    limits = load_limits()
    return limits["models"].get(model_id, limits["default_limits"])

def truncate_prompt(prompt: str, max_tokens: int) -> str:
    """Trunca prompt mantendo o final (mais importante)."""
    lines = prompt.split('\n')
    result = []
    current_tokens = 0
    
    for line in reversed(lines):
        line_tokens = count_tokens(line)
        if current_tokens + line_tokens > max_tokens:
            break
        result.insert(0, line)
        current_tokens += line_tokens
    
    return '\n'.join(result)

def split_prompt(prompt: str, max_tokens: int) -> list:
    """Divide prompt em chunks menores."""
    lines = prompt.split('\n')
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for line in lines:
        line_tokens = count_tokens(line)
        if current_tokens + line_tokens > max_tokens:
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_tokens = line_tokens
        else:
            current_chunk.append(line)
            current_tokens += line_tokens
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks

def limit_prompt(model_id: str, prompt: str, strategy: str = "truncate") -> str | list:
    limits = get_model_limits(model_id)
    max_tpm = limits.get("tpm", 30000)
    safe_limit = int(max_tpm * 0.8)  # 80% margem
    
    current_tokens = count_tokens(prompt)
    
    if current_tokens <= safe_limit:
        return prompt
    
    print(f"⚠ Prompt ({current_tokens} tokens) excede limite ({max_tpm} TPM)", file=sys.stderr)
    print(f"  Estratégia: {strategy}", file=sys.stderr)
    
    if strategy == "split":
        chunks = split_prompt(prompt, safe_limit)
        print(f"  ✓ {len(chunks)} chunks", file=sys.stderr)
        return chunks
    else:
        result = truncate_prompt(prompt, safe_limit)
        print(f"  ✓ Truncado para {count_tokens(result)} tokens", file=sys.stderr)
        return result

def main():
    if len(sys.argv) < 3:
        print("Uso: prompt_limiter.py <model_id> <prompt_file|prompt_text> [--strategy truncate|split]")
        sys.exit(1)
    
    model_id = sys.argv[1]
    prompt_input = sys.argv[2]
    strategy = "truncate"
    
    if "--strategy" in sys.argv:
        idx = sys.argv.index("--strategy")
        if idx + 1 < len(sys.argv):
            strategy = sys.argv[idx + 1]
    
    if prompt_input == "-":
        prompt = sys.stdin.read()
    elif Path(prompt_input).exists():
        prompt = Path(prompt_input).read_text()
    else:
        prompt = prompt_input
    
    result = limit_prompt(model_id, prompt, strategy)
    
    if isinstance(result, list):
        for i, chunk in enumerate(result, 1):
            print(f"\n{'='*50}\nCHUNK {i}/{len(result)}\n{'='*50}\n{chunk}")
    else:
        print(result)

if __name__ == "__main__":
    main()
