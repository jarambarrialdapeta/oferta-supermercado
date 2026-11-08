import urllib.request
import json
import re
import logging

logger = logging.getLogger(__name__)

TIENDEO_EROSKI_URL = "https://www.tiendeo.com/azkoitia/ofertas/eroski"

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

def fetch_eroski_deals() -> list:
    """Extrae las ofertas de Eroski Azkoitia publicadas en Tiendeo."""
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
    req = urllib.request.Request(TIENDEO_EROSKI_URL, headers=headers)
    deals = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            
        scripts = re.findall(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not scripts:
            logger.warning("No se encontró __NEXT_DATA__ en la página de Eroski de Tiendeo")
            return deals
            
        data = json.loads(scripts[0])
        api_res = data.get("props", {}).get("pageProps", {}).get("apiResources", {})
        
        raw_items = []
        ot = api_res.get("offersTable", {})
        raw_items.extend(ot.get("flyerGibs", []))
        
        fgd = api_res.get("flyerGibsData", {})
        raw_items.extend(fgd.get("flyerGibs", []))
        
        seen_ids = set()
        for item in raw_items:
            iid = str(item.get("id"))
            if iid in seen_ids:
                continue
            seen_ids.add(iid)
            
            settings = item.get("settings") or {}
            title = item.get("title") or ""
            nombre = re.sub(r"^Eroski\s*-\s*", "", title, flags=re.I).strip()
            
            price_val = parse_price(settings.get("price")) or parse_price(item.get("price"))
            starting_price_val = parse_price(settings.get("starting_price", {}).get("digits"))
            sale_str = settings.get("sale")
            
            descuento = None
            if sale_str and "%" in sale_str:
                try:
                    descuento = abs(int(float(sale_str.replace("%", "").strip())))
                except Exception:
                    pass
            elif starting_price_val and price_val and starting_price_val > price_val:
                descuento = round((1 - price_val / starting_price_val) * 100)
                
            deals.append({
                "cadena": "Eroski",
                "id": iid,
                "nombre": nombre,
                "precio": price_val,
                "precio_anterior": starting_price_val,
                "descuento": descuento,
                "descripcion": item.get("description", ""),
                "url": TIENDEO_EROSKI_URL,
                "formato": ""
            })
    except Exception as e:
        logger.error(f"Error consultando ofertas de Eroski en Tiendeo: {e}")
        
    return deals

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Buscando ofertas en Eroski (Azkoitia)...", flush=True)
    deals = fetch_eroski_deals()
    print(f"Total ofertas detectadas en Eroski: {len(deals)}", flush=True)
    for d in deals[:10]:
        print(f"  • {d['nombre']} -> {d['precio']} € (antes {d['precio_anterior']} €, -{d['descuento']}%)", flush=True)
