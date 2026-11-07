import unicodedata
import re

def normalize_text(text: str) -> str:
    """Normaliza texto: minúsculas, sin tildes ni caracteres especiales."""
    if not text:
        return ""
    text = text.lower()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]", " ", text)
    return " ".join(text.split())

def matches_product(deal_name: str, deal_desc: str, habit: dict) -> bool:
    """Verifica si la oferta encaja con alguno de los keywords del producto habitual y no contiene exclusiones."""
    norm_deal = normalize_text(f"{deal_name} {deal_desc}")
    keywords = habit.get("keywords", [])
    excludes = habit.get("exclude_keywords", [])
    
    # Comprobar exclusiones
    for ex in excludes:
        norm_ex = normalize_text(ex)
        ex_parts = norm_ex.split()
        if all(re.search(r"\b" + re.escape(p), norm_deal) for p in ex_parts):
            return False
            
    # Comprobar inclusiones
    for kw in keywords:
        norm_kw = normalize_text(kw)
        kw_parts = norm_kw.split()
        if all(re.search(r"\b" + re.escape(part), norm_deal) for part in kw_parts):
            return True
            
    return False

def find_matches(all_deals: list, habituales: list) -> list:
    """Cruza todas las ofertas con la lista de productos habituales deduplicando por (cadena, habitual_id)."""
    matched = []
    seen = set()
    
    for deal in all_deals:
        cadena = deal.get("cadena", "").lower()
        deal_name = deal.get("nombre", "")
        deal_desc = deal.get("descripcion", "")
        
        for habit in habituales:
            allowed_cadenas = [c.lower() for c in habit.get("cadenas", [])]
            if allowed_cadenas and cadena not in allowed_cadenas:
                continue
                
            if matches_product(deal_name, deal_desc, habit):
                # Clave única para evitar duplicados en el mismo aviso
                key = (deal.get("cadena"), habit.get("id"))
                if key not in seen:
                    seen.add(key)
                    matched.append({
                        "habitual_id": habit.get("id"),
                        "habitual_nombre": habit.get("nombre"),
                        "categoria": habit.get("categoria"),
                        **deal
                    })
                break
                
    return matched
