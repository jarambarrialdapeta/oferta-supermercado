import urllib.request
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

MERCADONA_BASE = "https://tienda.mercadona.es/api/v1_1"

def get_warehouse_for_postal_code(postal_code: str = "20870") -> str:
    """Obtiene el ID de almacén para un código postal."""
    url = f"{MERCADONA_BASE}/postal-codes/actions/change-pc/"
    payload = json.dumps({"new_postal_code": postal_code}).encode("utf-8")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            wh = resp.headers.get("X-Customer-Wh")
            if wh:
                return wh
    except Exception as e:
        logger.warning(f"Error deduciendo almacén para {postal_code}: {e}")
    return "4338"  # Fallback a Elgoibar

def fetch_category_deals(cat_id: int, warehouse: str, headers: dict) -> list:
    """Descarga los productos de una subcategoría y filtra los que tengan bajada o precio anterior."""
    url = f"{MERCADONA_BASE}/categories/{cat_id}/?wh={warehouse}"
    req = urllib.request.Request(url, headers=headers)
    deals = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for subcat in data.get("categories", []):
                for p in subcat.get("products", []):
                    pi = p.get("price_instructions", {})
                    prev_price_raw = pi.get("previous_unit_price")
                    unit_price_raw = pi.get("unit_price")
                    decreased = pi.get("price_decreased", False)

                    prev_price = float(prev_price_raw.strip()) if prev_price_raw else None
                    unit_price = float(unit_price_raw.strip()) if unit_price_raw else None

                    if decreased or (prev_price and unit_price and unit_price < prev_price):
                        deals.append({
                            "cadena": "Mercadona",
                            "id": str(p.get("id")),
                            "nombre": p.get("display_name"),
                            "precio": unit_price,
                            "precio_anterior": prev_price,
                            "descuento": round((1 - unit_price / prev_price) * 100) if prev_price and unit_price else None,
                            "url": f"https://tienda.mercadona.es/product/{p.get('id')}/",
                            "formato": f"{pi.get('reference_price')} €/{pi.get('reference_format')}" if pi.get('reference_price') else ""
                        })
    except Exception as e:
        logger.debug(f"Error consultando categoría {cat_id}: {e}")
    return deals

def fetch_all_mercadona_deals(postal_code: str = "20870") -> list:
    """Recorre concurrentemente las categorías de Mercadona y extrae todas las ofertas."""
    warehouse = get_warehouse_for_postal_code(postal_code)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    url = f"{MERCADONA_BASE}/categories/?wh={warehouse}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    
    subcat_ids = []
    for main_cat in data.get("results", []):
        for subcat in main_cat.get("categories", []):
            subcat_ids.append(subcat.get("id"))
    
    all_deals = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(fetch_category_deals, cid, warehouse, headers) for cid in subcat_ids]
        for f in as_completed(futures):
            res = f.result()
            if res:
                all_deals.extend(res)
                
    return all_deals

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Buscando ofertas en Mercadona (CP 20870)...", flush=True)
    deals = fetch_all_mercadona_deals("20870")
    print(f"Total ofertas / bajadas detectadas en Mercadona: {len(deals)}", flush=True)
    for d in deals[:10]:
        print(f"  • {d['nombre']} -> {d['precio']} € (antes {d['precio_anterior']} €, -{d['descuento']}%)", flush=True)
