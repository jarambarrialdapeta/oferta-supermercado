import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

# Importar lógica de búsqueda
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.search import compare_prices

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "9034938601:AAF6FJMFaUCiClMvUfwFafxPhCIdTt40Fso")

def send_reply(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
    except Exception as e:
        print(f"Error respondiendo a Telegram: {e}")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8")
        try:
            update = json.loads(body)
            message = update.get("message", {})
            chat = message.get("chat", {})
            chat_id = chat.get("id")
            text = message.get("text", "").strip()
            
            if chat_id and text:
                if text == "/start" or text == "/help":
                    reply = (
                        "👋 ¡Hola Julen! Soy tu bot de ofertas y comparador de precios.\n\n"
                        "💡 *¿Cómo usarme?*\n"
                        "Escribe el nombre de cualquier producto (ej: `salmon`, `banana`, `yogur natural`, `huevos`) "
                        "y buscaré en tiempo real los precios en Mercadona y Lidl para decirte dónde está más barato."
                    )
                else:
                    reply = compare_prices(text)
                    
                send_reply(chat_id, reply)
        except Exception as e:
            print(f"Error procesando update: {e}")
            
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot webhook activo y funcionando.")
