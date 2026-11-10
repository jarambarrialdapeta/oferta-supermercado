import urllib.request
import json
import logging
import unicodedata
import re

try:
    from src.lidl import fetch_lidl_deals
except ImportError:
    try:
        from lidl import fetch_lidl_deals
    except ImportError:
        fetch_lidl_deals = lambda: []

logger = logging.getLogger(__name__)

MERCADONA_ALGOLIA_URL = "https://7uzjkl1dj0-dsn.algolia.net/1/indexes/*/queries"
MERCADONA_HEADERS = {
    "X-Algolia-Application-Id": "7UZJKL1DJ0",
    "X-Algolia-API-Key": "9d8f2e39e90df472b4f2e559a116fe17",
    "Content-Type": "application/json"
}

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return text.strip()

def search_mercadona(query: str, warehouse: str = "4338", limit: int = 4) -> list:
    """Busca productos en Mercadona en tiempo real usando el índice Algolia del almacén."""
    index_name = f"products_prod_{warehouse}_es"
    payload = json.dumps({
        "requests": [
            {
                "indexName": index_name,
                "params": f"query={urllib.parse.quote(query)}&hitsPerPage={limit}"
            }
        ]
    }).encode("utf-8")
    
    products = []
    try:
        req = urllib.request.Request(MERCADONA_ALGOLIA_URL, data=payload, headers=MERCADONA_HEADERS, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            hits = data.get("results", [{}])[0].get("hits", [])
            for h in hits:
                pi = h.get("price_instructions", {})
                unit_price = float(pi.get("unit_price")) if pi.get("unit_price") else None
                ref_price = float(pi.get("reference_price")) if pi.get("reference_price") else None
                ref_format = pi.get("reference_format") or "ud"
                
                products.append({
                    "cadena": "Mercadona",
                    "nombre": h.get("display_name"),
                    "precio": unit_price,
                    "precio_referencia": ref_price,
                    "formato": ref_format,
                    "precio_kg_l": f"{ref_price:.2f} €/{ref_format}" if ref_price else "",
                    "url": f"https://tienda.mercadona.es/product/{h.get('id')}/"
                })
    except Exception as e:
        logger.error(f"Error buscando en Mercadona: {e}")
        
    return products

def search_lidl(query: str) -> list:
    """Busca productos coincidentes en las ofertas de Lidl."""
    norm_q = normalize_text(query)
    all_lidl = fetch_lidl_deals()
    results = []
    
    for item in all_lidl:
        norm_name = normalize_text(item.get("nombre", ""))
        norm_desc = normalize_text(item.get("descripcion", ""))
        if norm_q in norm_name or norm_q in norm_desc or any(w in norm_name for w in norm_q.split()):
            ref_str = item.get("formato") or ""
            ref_num = None
            m = re.search(r"(\d+[\,\.]\d+)\s*€\s*\/\s*(kg|l|ud)", ref_str, re.I)
            if m:
                try:
                    ref_num = float(m.group(1).replace(",", "."))
                except Exception:
                    pass
            results.append({
                "cadena": "Lidl",
                "nombre": item.get("nombre"),
                "precio": item.get("precio"),
                "precio_anterior": item.get("precio_anterior"),
                "descuento": item.get("descuento"),
                "precio_referencia": ref_num,
                "formato": "kg" if "kg" in ref_str.lower() else "ud",
                "precio_kg_l": ref_str,
                "url": item.get("url")
            })
    return results[:4]

def compare_prices(query: str) -> str:
    """Compara precios en tiempo real entre supermercados para una consulta del usuario."""
    clean_q = query.strip()
    if clean_q.startswith("/"):
        parts = clean_q.split(maxsplit=1)
        clean_q = parts[1] if len(parts) > 1 else ""
        
    if not clean_q:
        return "Escribe el producto que quieres buscar. Ejemplo: `salmon`, `banana` o `yogur`."
        
    merca = search_mercadona(clean_q)
    lidl = search_lidl(clean_q)
    
    if not merca and not lidl:
        return f"🔍 No he encontrado resultados para *{clean_q}* en las tiendas."
        
    lines = [f"🔍 *Comparativa de precios para:* _{clean_q}_\n"]
    
    if merca:
        lines.append("🟢 *Mercadona (Elgoibar)*")
        for p in merca:
            ref = f" ({p['precio_kg_l']})" if p.get("precio_kg_l") else ""
            lines.append(f"• *{p['nombre']}*: {p['precio']:.2f} €{ref}")
        lines.append("")
        
    if lidl:
        lines.append("🟡 *Lidl (Azcoitia)*")
        for p in lidl:
            desc = f" *[-{p['descuento']}%]*" if p.get("descuento") else ""
            ant = f" (antes {p['precio_anterior']:.2f} €)" if p.get("precio_anterior") else ""
            ref = f" _{p['precio_kg_l']}_" if p.get("precio_kg_l") else ""
            lines.append(f"• *{p['nombre']}*: {p['precio']:.2f} €{ant}{desc}{ref}")
        lines.append("")
        
    comparables = []
    for p in merca + lidl:
        if p.get("precio_referencia") and p.get("formato") in ["kg", "l"]:
            comparables.append((p["precio_referencia"], p["cadena"], p["nombre"], p["formato"]))
            
    if comparables:
        comparables.sort(key=lambda x: x[0])
        best_price, best_store, best_name, unit = comparables[0]
        lines.append(f"🏆 *Opción más económica por {unit}:*")
        lines.append(f"{best_store} ➔ *{best_name}* a *{best_price:.2f} €/{unit}*")
        
    return "\n".join(lines)

if __name__ == "__main__":
    for item in ["salmon", "banana", "yogur"]:
        print("="*40)
        print(compare_prices(item))
