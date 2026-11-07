import os
import json
import logging
from datetime import datetime, timedelta

from src.mercadona import fetch_all_mercadona_deals
from src.lidl import fetch_lidl_deals
from src.eroski import fetch_eroski_deals
from src.matcher import find_matches
from src.notifier import format_telegram_message, send_telegram_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("oferta_supermercado")

HABITUALES_FILE = "productos_habituales.json"
HISTORIAL_AVISOS_FILE = "avisos_enviados.json"

def load_json(filepath: str, default=None):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error leyendo {filepath}: {e}")
    return default if default is not None else []

def save_json(filepath: str, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def run():
    logger.info("Iniciando revisión diaria de ofertas...")
    
    # 1. Cargar productos habituales
    habituales = load_json(HABITUALES_FILE, default=[])
    if not habituales:
        logger.warning(f"No se han encontrado productos habituales en {HABITUALES_FILE}")
        return
    logger.info(f"Cargados {len(habituales)} productos habituales.")
    
    # 2. Cargar historial de avisos enviados
    historial = load_json(HISTORIAL_AVISOS_FILE, default={})
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Limpiar avisos con más de 14 días para que el archivo no crezca indefinidamente
    cutoff_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    historial = {k: v for k, v in historial.items() if v.get("fecha", "") >= cutoff_date}
    
    # 3. Recopilar ofertas de las tres cadenas
    all_deals = []
    
    # Mercadona (Elgoibar CP 20870)
    try:
        logger.info("Consultando Mercadona (Elgoibar)...")
        mercadona_deals = fetch_all_mercadona_deals(postal_code="20870")
        logger.info(f"Mercadona: {len(mercadona_deals)} ofertas/rebajas encontradas.")
        all_deals.extend(mercadona_deals)
    except Exception as e:
        logger.error(f"Fallo consultando Mercadona: {e}")
        
    # Lidl (Azcoitia CP 20720)
    try:
        logger.info("Consultando Lidl (Azcoitia)...")
        lidl_deals = fetch_lidl_deals()
        logger.info(f"Lidl: {len(lidl_deals)} ofertas encontradas.")
        all_deals.extend(lidl_deals)
    except Exception as e:
        logger.error(f"Fallo consultando Lidl: {e}")
        
    # Eroski (Azcoitia CP 20720)
    try:
        logger.info("Consultando Eroski (Azcoitia)...")
        eroski_deals = fetch_eroski_deals()
        logger.info(f"Eroski: {len(eroski_deals)} ofertas encontradas.")
        all_deals.extend(eroski_deals)
    except Exception as e:
        logger.error(f"Fallo consultando Eroski: {e}")
        
    # 4. Cruzar con productos habituales
    matches = find_matches(all_deals, habituales)
    logger.info(f"Total coincidencias encontradas con habituales: {len(matches)}")
    
    # 5. Filtrar ofertas ya avisadas en los últimos 5 días con el mismo precio
    new_matches = []
    for m in matches:
        key = f"{m['cadena']}_{m['habitual_id']}_{m.get('precio')}"
        last_sent = historial.get(key)
        if last_sent:
            # Si ya se avisó hace menos de 5 días, no repetimos
            last_date = datetime.strptime(last_sent["fecha"], "%Y-%m-%d")
            if (datetime.now() - last_date).days < 5:
                continue
                
        new_matches.append((key, m))
        
    if not new_matches:
        logger.info("No hay nuevas ofertas para notificar hoy (o ya fueron avisadas recientemente).")
        save_json(HISTORIAL_AVISOS_FILE, historial)
        return
        
    logger.info(f"Hay {len(new_matches)} ofertas nuevas para avisar por Telegram.")
    items_to_alert = [m for _, m in new_matches]
    
    # 6. Formatear y enviar mensaje
    message_text = format_telegram_message(items_to_alert)
    print("\n--- MENSAJE PARA TELEGRAM ---")
    print(message_text)
    print("-----------------------------\n")
    
    sent = send_telegram_alert(message_text)
    
    # 7. Si se envió (o si estamos probando sin token), registrar en historial
    for key, m in new_matches:
        historial[key] = {
            "fecha": today_str,
            "cadena": m["cadena"],
            "nombre": m["nombre"],
            "precio": m.get("precio"),
            "descuento": m.get("descuento")
        }
    save_json(HISTORIAL_AVISOS_FILE, historial)
    logger.info("Historial de avisos actualizado.")

if __name__ == "__main__":
    run()
