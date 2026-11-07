# Oferta Supermercado 🛒

Pequeña aplicación automatizada que revisa a diario las ofertas y bajadas de precio en **Mercadona**, **Lidl** y **Eroski**, las cruza con los productos que sueles comprar y te avisa por **Telegram** solo cuando hay una coincidencia.

## Tiendas configuradas
- **Mercadona:** Almacén Elgoibar (CP 20870, Almacén `4338`). Consulta directa a la API oficial de precios.
- **Lidl:** Azcoitia (CP 20720). Consulta de ofertas locales vía Tiendeo.
- **Eroski:** Azcoitia (CP 20720). Consulta de ofertas y promociones locales vía Tiendeo.

---

## Cómo funciona
1. **GitHub Actions** ejecuta automáticamente el script cada mañana a las 07:00 UTC (08:00 / 09:00 peninsular).
2. Descarga concurrentemente el catálogo de ofertas y productos con precio rebajado en las 3 cadenas.
3. Cruza los resultados con tu lista de `productos_habituales.json` (usando búsqueda por palabras clave normalizadas y exclusiones para evitar falsos positivos).
4. Comprueba `avisos_enviados.json` para no enviar el mismo aviso repetidas veces.
5. Si hay ofertas relevantes nuevas, envía un mensaje estructurado y directo a tu bot de Telegram.

---

## Estructura del proyecto

```text
oferta-supermercado/
├── .github/workflows/
│   └── daily.yml                # Tarea programada en GitHub Actions
├── src/
│   ├── mercadona.py             # Extractor de precios y bajadas de Mercadona
│   ├── lidl.py                  # Extractor de ofertas de Lidl Azcoitia
│   ├── eroski.py                # Extractor de ofertas de Eroski Azcoitia
│   ├── matcher.py               # Algoritmo de cruce inteligente y deduplicación
│   └── notifier.py              # Formateo y envío de alertas a Telegram
├── productos_habituales.json     # Catálogo de tus productos habituales
├── avisos_enviados.json         # Historial para no repetir avisos
├── main.py                      # Orquestador del pipeline
└── README.md
```

---

## Cómo personalizar tu lista de productos

Puedes editar `productos_habituales.json` directamente desde GitHub para añadir o quitar productos:

```json
{
  "id": "aceite_oliva",
  "nombre": "Aceite de oliva virgen extra",
  "keywords": ["aceite de oliva virgen", "virgen extra"],
  "exclude_keywords": ["suave", "intenso"],
  "cadenas": ["mercadona", "lidl", "eroski"],
  "categoria": "aceites"
}
```

- `keywords`: Frases o palabras que deben coincidir (insensible a mayúsculas y tildes).
- `exclude_keywords`: Palabras para descartar falsos positivos (por ejemplo, descartar "bebida" o "yogur" si el producto es "fresas").
- `cadenas`: Cadenas en las que buscar este producto (`["mercadona", "lidl", "eroski"]`).

---

## Secretos requeridos en el repositorio

En **Settings > Secrets and variables > Actions**:

| Secreto | Descripción |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token generado con `@BotFather` (ej: `9034938601:AAF6...`) |
| `TELEGRAM_CHAT_ID` | Tu ID numérico personal de usuario de Telegram (obtenido con `@userinfobot`) |

---

## Ejecución manual

Puedes disparar una comprobación en cualquier momento:
1. En GitHub, ve a la pestaña **Actions**.
2. Selecciona **Revision Diaria de Ofertas**.
3. Pulsa en **Run workflow**.
