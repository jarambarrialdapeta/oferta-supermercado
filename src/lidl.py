import urllib.request
import json
import re
import logging

logger = logging.getLogger(__name__)

TIENDEO_LIDL_URL = "https://www.tiendeo.com/azkoitia/lidl"

def parse_price(val):
    if not val:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    val = str(val).replace("€", "").strip().replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return None

def fetch_lidl_deals() -> list:
    """Extrae las ofertas de Lidl Azkoitia publicadas en Tiendeo."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    req = urllib.request.Request(TIENDEO_LIDL_URL, headers=headers)
    deals = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            
        scripts = re.findall(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not scripts:
            logger.warning("No se encontró __NEXT_DATA__ en la página de Lidl de Tiendeo")
            return deals
            
        data = json.loads(scripts[0])
        api_res = data.get("props", {}).get("pageProps", {}).get("apiResources", {})
        top_offers = api_res.get("topOffers", [])
        
        for item in top_offers:
            settings = item.get("settings", {})
            title = item.get("title") or settings.get("shared_category") or ""
            price_val = parse_price(settings.get("price"))
            starting_price_val = parse_price(settings.get("starting_price", {}).get("digits"))
            sale_str = settings.get("sale")
            ocr_text = settings.get("google_vision_text", "")
            
            descuento = None
            if sale_str and "%" in sale_str:
                try:
                    descuento = abs(int(float(sale_str.replace("%", "").strip())))
                except Exception:
                    pass
            elif starting_price_val and price_val and starting_price_val > price_val:
                descuento = round((1 - price_val / starting_price_val) * 100)
                
            deals.append({
                "cadena": "Lidl",
                "id": str(item.get("id")),
                "nombre": title,
                "precio": price_val,
                "precio_anterior": starting_price_val,
                "descuento": descuento,
                "descripcion": ocr_text[:120] if ocr_text else item.get("description", ""),
                "url": "https://www.tiendeo.com/azkoitia/lidl",
                "formato": ""
            })
    except Exception as e:
        logger.error(f"Error consultando ofertas de Lidl en Tiendeo: {e}")
        
    return deals

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Buscando ofertas en Lidl (Azkoitia)...", flush=True)
    deals = fetch_lidl_deals()
    print(f"Total ofertas detectadas en Lidl: {len(deals)}", flush=True)
    for d in deals[:10]:
        print(f"  • {d['nombre']} -> {d['precio']} € (antes {d['precio_anterior']} €, -{d['descuento']}%)", flush=True)
