/**
 * Cloudflare Worker para el bot de Telegram @Ofertakbot
 * Responde en tiempo real a consultas de precios y comparativas de supermercados.
 */

const TELEGRAM_BOT_TOKEN = "9034938601:AAF6FJMFaUCiClMvUfwFafxPhCIdTt40Fso";

// Credenciales públicas de la API de Mercadona
const MERCADONA_APP_ID = "7UZJKL1DJ0";
const MERCADONA_API_KEY = "9d8f2e39e90df472b4f2e559a116fe17";
const MERCADONA_WAREHOUSE = "4338"; // Elgoibar

async function searchMercadona(query) {
  const url = "https://7uzjkl1dj0-dsn.algolia.net/1/indexes/*/queries";
  const indexName = `products_prod_${MERCADONA_WAREHOUSE}_es`;
  
  const payload = {
    requests: [
      {
        indexName: indexName,
        params: `query=${encodeURIComponent(query)}&hitsPerPage=4`
      }
    ]
  };

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "X-Algolia-Application-Id": MERCADONA_APP_ID,
        "X-Algolia-API-Key": MERCADONA_API_KEY,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
    
    const data = await res.json();
    const hits = (data.results && data.results[0] && data.results[0].hits) || [];
    
    return hits.map(h => {
      const pi = h.price_instructions || {};
      const unitPrice = parseFloat(pi.unit_price) || null;
      const refPrice = parseFloat(pi.reference_price) || null;
      const refFormat = pi.reference_format || "ud";
      
      return {
        cadena: "Mercadona",
        nombre: h.display_name,
        precio: unitPrice,
        precio_referencia: refPrice,
        formato: refFormat,
        precio_kg_l: refPrice ? `${refPrice.toFixed(2)} €/${refFormat}` : ""
      };
    });
  } catch (err) {
    console.error("Error buscando en Mercadona:", err);
    return [];
  }
}

async function searchLidl(query) {
  const url = "https://www.lidl.es/c/store/ofertas-semanales/a10089449";
  try {
    const res = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
      }
    });
    const html = await res.text();
    const regex = /data-grid-data="([^"]+)"/g;
    let match;
    const items = [];
    const qLower = query.toLowerCase().trim();

    while ((match = regex.exec(html)) !== null) {
      try {
        const decoded = match[1].replace(/&quot;/g, '"').replace(/&amp;/g, '&');
        const data = JSON.parse(decoded);
        const title = (data.fullTitle || data.title || "").toLowerCase();
        
        if (title.includes(qLower) || qLower.split(" ").some(w => w.length > 2 && title.includes(w))) {
          const priceInfo = data.price || {};
          const p = parseFloat(priceInfo.price);
          const disc = priceInfo.discount || {};
          const oldP = parseFloat(disc.deletedPrice);
          const pct = disc.percentageDiscount;
          const refStr = (priceInfo.basePrice && priceInfo.basePrice.formattedBasePrice) || "";
          
          let refNum = null;
          const mRef = refStr.match(/(\d+[,\.]\d+)\s*€\s*\/\s*(kg|l|ud)/i);
          if (mRef) {
            refNum = parseFloat(mRef[1].replace(",", "."));
          }

          items.push({
            cadena: "Lidl",
            nombre: data.fullTitle || data.title,
            precio: p,
            precio_anterior: oldP,
            descuento: pct,
            precio_referencia: refNum,
            formato: refStr.toLowerCase().includes("kg") ? "kg" : "ud",
            precio_kg_l: refStr
          });
        }
      } catch (e) {}
    }
    return items.slice(0, 4);
  } catch (err) {
    console.error("Error buscando en Lidl:", err);
    return [];
  }
}

async function buildComparison(query) {
  let cleanQ = query.trim();
  if (cleanQ.startsWith("/")) {
    cleanQ = cleanQ.split(" ").slice(1).join(" ").trim();
  }
  
  if (!cleanQ) {
    return "Escribe el nombre del producto que quieres buscar. Ejemplo: `salmon`, `banana` o `yogur natural`.";
  }

  const [merca, lidl] = await Promise.all([
    searchMercadona(cleanQ),
    searchLidl(cleanQ)
  ]);

  if (!merca.length && !lidl.length) {
    return `🔍 No he encontrado resultados para *${cleanQ}* en los supermercados.`;
  }

  const lines = [`🔍 *Comparativa de precios para:* _${cleanQ}_\n`];

  if (merca.length) {
    lines.push("🟢 *Mercadona (Elgoibar)*");
    for (const p of merca) {
      const ref = p.precio_kg_l ? ` (${p.precio_kg_l})` : "";
      lines.push(`• *${p.nombre}*: ${p.precio ? p.precio.toFixed(2) + " €" : ""}${ref}`);
    }
    lines.push("");
  }

  if (lidl.length) {
    lines.push("🟡 *Lidl (Azcoitia)*");
    for (const p of lidl) {
      const desc = p.descuento ? ` *[-${p.descuento}%]*` : "";
      const ant = p.precio_anterior ? ` (antes ${p.precio_anterior.toFixed(2)} €)` : "";
      const ref = p.precio_kg_l ? ` _${p.precio_kg_l}_` : "";
      lines.push(`• *${p.nombre}*: ${p.precio ? p.precio.toFixed(2) + " €" : ""}${ant}${desc}${ref}`);
    }
    lines.push("");
  }

  // Comparar precio por kg
  const comparables = [...merca, ...lidl].filter(p => p.precio_referencia && ["kg", "l"].includes(p.formato));
  if (comparables.length > 0) {
    comparables.sort((a, b) => a.precio_referencia - b.precio_referencia);
    const best = comparables[0];
    lines.push(`🏆 *Opción más económica por ${best.formato}:*`);
    lines.push(`${best.cadena} ➔ *${best.nombre}* a *${best.precio_referencia.toFixed(2)} €/${best.formato}*`);
  }

  return lines.join("\n");
}

async function sendTelegramMessage(chatId, text) {
  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
  await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: text,
      parse_mode: "Markdown",
      disable_web_page_preview: true
    })
  });
}

export default {
  async fetch(request) {
    if (request.method === "POST") {
      try {
        const update = await request.json();
        const message = update.message;
        if (message && message.chat && message.text) {
          const text = message.text.trim();
          let reply;
          if (text === "/start" || text === "/help") {
            reply = "👋 ¡Hola! Pregúntame cualquier producto (ej: `salmon`, `banana`, `yogur natural`, `huevos`) y te diré precios en Mercadona y Lidl con comparativa de dónde está más barato.";
          } else {
            reply = await buildComparison(text);
          }
          await sendTelegramMessage(message.chat.id, reply);
        }
      } catch (e) {
        console.error("Error en webhook:", e);
      }
      return new Response(JSON.stringify({ status: "ok" }), {
        headers: { "Content-Type": "application/json" }
      });
    }

    return new Response("Bot de Telegram activo y listo para webhook.");
  }
};
