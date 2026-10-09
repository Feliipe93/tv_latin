// Cloudflare Worker: devuelve la lista lac.m3u de iptv-org filtrada según canales.txt,
// más las [fuentes_extra] configuradas. No guarda nada: se genera al vuelo.

const SOURCE_URL = "https://iptv-org.github.io/iptv/regions/lac.m3u";
const CONFIG_URL = "https://raw.githubusercontent.com/Feliipe93/tv_latin/main/canales.txt";
const CACHE_SECONDS = 3600; // reutiliza el resultado hasta 1 hora para responder rápido

const SUFFIX_RE = /\s*(\(\d+p\)|\[[^\]]*\])/g;

export function leerConfig(texto) {
  const reglas = { contiene: [], exactos: [], excluir: [], fuentes_extra: [] };
  let seccion = null;
  for (let linea of texto.split(/\r?\n/)) {
    linea = linea.trim();
    if (!linea || linea.startsWith("#")) continue;
    if (linea.startsWith("[") && linea.endsWith("]")) {
      seccion = linea.slice(1, -1).toLowerCase();
      if (!(seccion in reglas)) throw new Error(`Sección desconocida: [${seccion}]`);
      continue;
    }
    if (!seccion) throw new Error(`Línea fuera de sección: ${linea}`);
    if (seccion === "fuentes_extra") {
      const idx = linea.indexOf("|");
      const url = (idx === -1 ? linea : linea.slice(0, idx)).trim();
      const sufijo = idx === -1 ? "" : linea.slice(idx + 1).trim();
      reglas.fuentes_extra.push({ url, sufijo });
    } else {
      reglas[seccion].push(linea.toLowerCase());
    }
  }
  return reglas;
}

function* bloques(m3u) {
  const lineas = m3u.split(/\r?\n/);
  let i = 0;
  while (i < lineas.length) {
    if (lineas[i].startsWith("#EXTINF")) {
      const bloque = [lineas[i++]];
      while (i < lineas.length && lineas[i].startsWith("#")) bloque.push(lineas[i++]);
      if (i < lineas.length) bloque.push(lineas[i++]);
      yield bloque;
    } else {
      i++;
    }
  }
}

function nombreLimpio(extinf) {
  const nombre = extinf.slice(extinf.lastIndexOf(",") + 1);
  return nombre.replace(SUFFIX_RE, "").trim().toLowerCase();
}

function compacto(texto) {
  return texto.toLowerCase().replace(/[^a-z0-9áéíóúüñ]+/g, "");
}

function coincide(nombre, extinf, reglas) {
  const busqueda = extinf.replace(SUFFIX_RE, "").trim().toLowerCase();
  const busquedaCompacta = compacto(busqueda);
  if (reglas.excluir.some((ex) => nombre.includes(ex) || busqueda.includes(ex))) return false;
  if (reglas.exactos.includes(nombre)) return true;
  return reglas.contiene.some(
    (kw) => busqueda.includes(kw) || busquedaCompacta.includes(compacto(kw)),
  );
}

function conSufijo(extinf, sufijo) {
  if (!sufijo) return extinf;
  const idx = extinf.lastIndexOf(",");
  return `${extinf.slice(0, idx)},${extinf.slice(idx + 1).trim()} ${sufijo}`;
}

function conAspectRatioOriginal(extinf) {
  if (/\baspect-ratio\s*=/i.test(extinf)) {
    return extinf.replace(/\baspect-ratio\s*=\s*"[^"]*"/i, 'aspect-ratio="original"');
  }
  const idx = extinf.lastIndexOf(",");
  return `${extinf.slice(0, idx)} aspect-ratio="original"${extinf.slice(idx)}`;
}

export function filtrar(m3u, reglas) {
  const salida = ["#EXTM3U"];
  let total = 0;
  for (const bloque of bloques(m3u)) {
    if (coincide(nombreLimpio(bloque[0]), bloque[0], reglas)) {
      bloque[0] = conAspectRatioOriginal(bloque[0]);
      salida.push(...bloque);
      total++;
    }
  }
  return { lineas: salida, total };
}

export function agregarExtra(salida, m3u, sufijo) {
  let total = 0;
  for (const bloque of bloques(m3u)) {
    if (bloque[bloque.length - 1].startsWith("#")) continue;
    salida.push(conAspectRatioOriginal(conSufijo(bloque[0], sufijo)), ...bloque.slice(1));
    total++;
  }
  return total;
}

async function descargar(url) {
  const resp = await fetch(url, { headers: { "user-agent": "tv_latin-worker" } });
  if (!resp.ok) throw new Error(`Error ${resp.status} al descargar ${url}`);
  return resp.text();
}

async function hash(texto) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(texto));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function generar(config) {
  const reglas = leerConfig(config);
  const { lineas, total } = filtrar(await descargar(SOURCE_URL), reglas);
  if (total === 0) throw new Error("Ningún canal coincidió con canales.txt");

  let totalExtra = 0;
  const extras = await Promise.allSettled(reglas.fuentes_extra.map((f) => descargar(f.url)));
  extras.forEach((r, i) => {
    if (r.status === "fulfilled") totalExtra += agregarExtra(lineas, r.value, reglas.fuentes_extra[i].sufijo);
  });

  return new Response(lineas.join("\n") + "\n", {
    headers: {
      "content-type": "audio/x-mpegurl; charset=utf-8",
      "content-disposition": 'inline; filename="tv_latin.m3u"',
      "cache-control": `public, max-age=${CACHE_SECONDS}`,
      "x-canales": String(total + totalExtra),
      "x-canales-extra": String(totalExtra),
    },
  });
}

export default {
  async fetch(request, env, ctx) {
    const cache = caches.default;
    try {
      // La clave de caché incluye el hash de canales.txt: al editarlo, la lista se regenera enseguida.
      const config = await descargar(CONFIG_URL);
      const origen = new URL(request.url).origin;
      const clave = new Request(`${origen}/tv_latin.m3u?v=${await hash(config)}`, { method: "GET" });
      const cacheado = await cache.match(clave);
      if (cacheado) return cacheado;

      const resp = await generar(config);
      ctx.waitUntil(cache.put(clave, resp.clone()));
      return resp;
    } catch (err) {
      return new Response(`Error generando la lista: ${err.message}\n`, {
        status: 502,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }
  },
};
