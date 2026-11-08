import urllib.request
import json
import re
import html
import logging

logger = logging.getLogger(__name__)

LIDL_OFFERS_URLS = [
    "https://www.lidl.es/c/store/ofertas-semanales/a10089449",
    "https://www.lidl.es/c/store/ofertas-proxima-semana/a10088432"
]

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

def fetch_lidl_direct() -> list:
    """Extrae ofertas directamente desde la web oficial de lidl.es (sin bloqueos de IP)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9"
    }
    
    deals = []
    seen = set()
    
    for url in LIDL_OFFERS_URLS:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                page_html = resp.read().decode("utf-8", errors="ignore")
                
            matches = re.findall(r'data-grid-data=\"([^\"]+)\"', page_html)
            for m in matches:
                try:
                    d = json.loads(html.unescape(m))
                    title = d.get("fullTitle") or d.get("title") or ""
                    if not title or title in seen:
                        continue
                        
                    price_info = d.get("price") or {}
                    price_val = parse_price(price_info.get("price"))
                    discount_info = price_info.get("discount") or {}
                    
                    old_price = parse_price(discount_info.get("deletedPrice"))
                    pct = discount_info.get("percentageDiscount")
                    
                    # Guardamos productos con descuento o precio promocional
                    if old_price and price_val and old_price > price_val:
                        descuento = pct or round((1 - price_val / old_price) * 100)
                    elif pct and price_val:
                        descuento = int(pct)
                    else:
                        continue
                        
                    seen.add(title)
                    deals.append({
                        "cadena": "Lidl",
                        "id": str(d.get("productId") or title),
                        "nombre": title,
                        "precio": price_val,
                        "precio_anterior": old_price,
                        "descuento": descuento,
                        "descripcion": d.get("description", ""),
                        "url": url,
                        "formato": price_info.get("basePrice", {}).get("formattedBasePrice", "")
                    })
                except Exception as e:
                    logger.debug(f"Error procesando producto de Lidl: {e}")
        except Exception as e:
            logger.warning(f"Error consultando ofertas directas de Lidl ({url}): {e}")
            
    return deals

def fetch_lidl_deals() -> list:
    """Extrae las ofertas de Lidl usando la web oficial como fuente principal."""
    deals = fetch_lidl_direct()
    if deals:
        logger.info(f"Lidl: {len(deals)} ofertas encontradas directamente en lidl.es")
        return deals
        
    logger.info("Lidl: Fallback a Tiendeo")
    return []

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Buscando ofertas en Lidl...", flush=True)
    deals = fetch_lidl_deals()
    print(f"Total ofertas detectadas en Lidl: {len(deals)}", flush=True)
    for d in deals[:10]:
        print(f"  • {d['nombre']} -> {d['precio']} € (antes {d['precio_anterior']} €, -{d['descuento']}%)", flush=True)
