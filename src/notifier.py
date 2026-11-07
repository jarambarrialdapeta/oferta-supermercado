import os
import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger(__name__)

def format_telegram_message(matches: list) -> str:
    """Formatea la lista de ofertas coincidentes en un mensaje claro para Telegram."""
    if not matches:
        return ""
        
    lines = [
        "🛒 *¡Ofertas encontradas para tus compras habituales!*",
        f"📅 _{len(matches)} producto(s) en oferta hoy:_\n"
    ]
    
    # Agrupar por cadena
    by_cadena = {}
    for m in matches:
        by_cadena.setdefault(m["cadena"], []).append(m)
        
    emoji_store = {
        "Mercadona": "🟢",
        "Lidl": "🟡",
        "Eroski": "🔴"
    }
    
    for cadena, items in by_cadena.items():
        icon = emoji_store.get(cadena, "🏬")
        lines.append(f"{icon} *{cadena}*")
        for it in items:
            nombre = it["nombre"]
            precio = f"{it['precio']:.2f} €" if it.get("precio") is not None else "En oferta"
            anterior = f" (antes {it['precio_anterior']:.2f} €)" if it.get("precio_anterior") else ""
            descuento = f" *[-{it['descuento']}%]*" if it.get("descuento") else ""
            formato = f" _{it['formato']}_" if it.get("formato") else ""
            
            lines.append(f"• *{nombre}*: {precio}{anterior}{descuento}{formato}")
        lines.append("")
        
    lines.append("Buen ahorro 💪")
    return "\n".join(lines)

def send_telegram_alert(text: str, bot_token: str = None, chat_id: str = None) -> bool:
    """Envía un mensaje a Telegram a través del Bot API."""
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not cid:
        logger.error("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en las variables de entorno.")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": cid,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }).encode("utf-8")
    
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                logger.info("Alerta de Telegram enviada con éxito.")
                return True
            else:
                logger.error(f"Error en respuesta de Telegram: {data}")
    except Exception as e:
        logger.error(f"Error enviando mensaje a Telegram: {e}")
        
    return False
