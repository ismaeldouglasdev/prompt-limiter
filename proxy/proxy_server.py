#!/usr/bin/env python3
"""
Prompt Limiter Proxy — intercepta requests OpenCode → 9router,
limita prompts automaticamente se excederem TPM do modelo.

Uso: python3 proxy_server.py [porta]

Depois configure opencode.json:
  "baseURL": "http://127.0.0.1:20130/v1"  (antes era :20128)
"""
import json, os, sys, time, logging
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import urllib.request
import urllib.error

# ── Config ──────────────────────────────────────────────────────────────────
PROXY_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 20130
NINEROUTER_URL = os.environ.get("NINEROUTER_URL", "http://localhost:20128")
NINEROUTER_KEY = os.environ.get("NINEROUTER_KEY", "")
LIMITS_FILE = Path(__file__).parent.parent / "model_limits.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s PROXY %(message)s",
    datefmt="%H:%M:%S",
)

def load_limits():
    if LIMITS_FILE.exists():
        return json.loads(LIMITS_FILE.read_text())
    return {"models": {}, "default_limits": {"tpm": 30000}}

def get_model_limits(model_id):
    limits = load_limits()
    return limits["models"].get(model_id, limits["default_limits"])

def count_tokens(text):
    """~4 chars = 1 token (aproximação conservadora)."""
    return len(text) // 4

def truncate_prompt(messages, max_tokens):
    """Remove mensagens do início até caber no limite."""
    total = 0
    kept = []
    for msg in reversed(messages):
        content = msg.get("content", "")
        tokens = count_tokens(content)
        if total + tokens > max_tokens:
            # Trunca o conteúdo desta mensagem
            chars = (max_tokens - total) * 4
            msg = dict(msg)
            msg["content"] = content[:chars] + "\n[...truncated...]"
            kept.insert(0, msg)
            break
        kept.insert(0, msg)
        total += tokens

    prefix = {"role": "system", "content": f"[Prompt Limiter] Contexto reduzido de ~{total}m tokens para {max_tokens/1000:.0f}K para caber no modelo."}
    return [prefix] + kept

def limit_request(body):
    """Aplica limitação se necessário. Retorna body modificado ou None."""
    model = body.get("model", "unknown")
    messages = body.get("messages", [])

    # Só limita modelos com TPM baixo
    limits = get_model_limits(model)
    max_tpm = limits.get("tpm", 30000)
    safe_limit = int(max_tpm * 0.75)  # 75% margem

    # Conta tokens de todas as mensagens
    all_text = " ".join(m.get("content", "") for m in messages)
    total_tokens = count_tokens(all_text)

    if total_tokens <= safe_limit:
        return None  # Tamanho ok, não precisa limitar

    logging.warning(f"⚠ {model}: {total_tokens}t excede {max_tpm} TPM — limitando...")

    limited_messages = truncate_prompt(messages, safe_limit)
    limited_text = " ".join(m.get("content", "") for m in limited_messages)
    limited_tokens = count_tokens(limited_text)

    body = dict(body)
    body["messages"] = limited_messages
    body["_prompt_limited"] = True
    body["_original_tokens"] = total_tokens
    body["_limited_tokens"] = limited_tokens

    logging.info(f"  → {total_tokens}t → {limited_tokens}t ({len(limited_messages)} msgs)")
    return body


class ProxyHandler(BaseHTTPRequestHandler):
    def _forward(self, body=None):
        """Forward request to 9router and return response."""
        path = self.path
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {NINEROUTER_KEY}",
        }
        data = json.dumps(body).encode() if body else None

        url = f"{NINEROUTER_URL}{path}"
        req = urllib.request.Request(url, data=data, headers=headers, method=self.command)

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ("transfer-encoding", "content-encoding", "content-length"):
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as e:
            resp_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp_body)

    def do_GET(self):
        self._forward()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        body = json.loads(raw)

        # Apply prompt limiting
        if "/chat/completions" in self.path or "/v1/chat/completions" in self.path:
            limited = limit_request(body)
            if limited:
                body = limited

        self._forward(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, fmt, *args):
        logging.info(f"{self.client_address[0]} {fmt % args}")


def run():
    server = HTTPServer(("0.0.0.0", PROXY_PORT), ProxyHandler)
    logging.info(f"🚀 Prompt Limiter Proxy → http://localhost:{PROXY_PORT}")
    logging.info(f"   Encaminhando para → {NINEROUTER_URL}")
    logging.info(f"")
    logging.info(f"   Para ativar, mude no opencode.json:")
    logging.info(f'     "baseURL": "http://127.0.0.1:{PROXY_PORT}/v1"')
    logging.info(f"")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        logging.info("Proxy encerrado.")


if __name__ == "__main__":
    run()
