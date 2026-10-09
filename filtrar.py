"""Genera tv_latin.m3u filtrando la lista lac.m3u de iptv-org según canales.txt
y añadiendo, si están configuradas, las fuentes extra ([fuentes_extra])."""

import re
import sys
import urllib.request

SOURCE_URL = "https://iptv-org.github.io/iptv/regions/lac.m3u"
CONFIG_FILE = "canales.txt"
OUTPUT_FILE = "tv_latin.m3u"

SUFFIX_RE = re.compile(r"\s*(\(\d+p\)|\[[^\]]*\])")


def leer_config(path):
    reglas = {"contiene": [], "exactos": [], "excluir": [], "fuentes_extra": []}
    seccion = None
    with open(path, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if linea.startswith("[") and linea.endswith("]"):
                seccion = linea[1:-1].lower()
                if seccion not in reglas:
                    sys.exit(f"Sección desconocida en {path}: [{seccion}]")
                continue
            if seccion is None:
                sys.exit(f"Línea fuera de sección en {path}: {linea}")
            if seccion == "fuentes_extra":
                url, _, sufijo = linea.partition("|")
                reglas[seccion].append((url.strip(), sufijo.strip()))
            else:
                reglas[seccion].append(linea.lower())
    return reglas


def descargar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "tv_latin"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def bloques(m3u):
    """Devuelve cada canal como lista de líneas: #EXTINF, extras (#EXTVLCOPT...) y URL."""
    lineas = m3u.splitlines()
    i = 0
    while i < len(lineas):
        if lineas[i].startswith("#EXTINF"):
            bloque = [lineas[i]]
            i += 1
            while i < len(lineas) and lineas[i].startswith("#"):
                bloque.append(lineas[i])
                i += 1
            if i < len(lineas):
                bloque.append(lineas[i])
                i += 1
            yield bloque
        else:
            i += 1


def nombre_limpio(extinf):
    nombre = extinf.rsplit(",", 1)[-1]
    return SUFFIX_RE.sub("", nombre).strip().lower()


def texto_busqueda(extinf):
    """Incluye nombre y metadatos para detectar altas nuevas de iptv-org."""
    return SUFFIX_RE.sub("", extinf).strip().lower()


def compacto(texto):
    return re.sub(r"[^a-z0-9áéíóúüñ]+", "", texto.lower())


def coincide(nombre, extinf, reglas):
    busqueda = texto_busqueda(extinf)
    busqueda_compacta = compacto(busqueda)
    if any(ex in nombre or ex in busqueda for ex in reglas["excluir"]):
        return False
    if nombre in reglas["exactos"]:
        return True
    return any(
        kw in busqueda or compacto(kw) in busqueda_compacta
        for kw in reglas["contiene"]
    )


def con_sufijo(extinf, sufijo):
    if not sufijo:
        return extinf
    attrs, _, nombre = extinf.rpartition(",")
    return f"{attrs},{nombre.strip()} {sufijo}"


def main():
    reglas = leer_config(CONFIG_FILE)
    salida = ["#EXTM3U"]

    total = 0
    for bloque in bloques(descargar(SOURCE_URL)):
        if coincide(nombre_limpio(bloque[0]), bloque[0], reglas):
            salida.extend(bloque)
            total += 1
    if total == 0:
        sys.exit("Ningún canal coincidió; no se sobrescribe la lista.")
    print(f"iptv-org: {total} canales")

    for url, sufijo in reglas["fuentes_extra"]:
        try:
            extra = 0
            for bloque in bloques(descargar(url)):
                if bloque[-1].startswith("#"):
                    continue
                salida.append(con_sufijo(bloque[0], sufijo))
                salida.extend(bloque[1:])
                extra += 1
            print(f"{url}: {extra} canales")
            total += extra
        except Exception as e:
            print(f"AVISO: no se pudo leer {url}: {e}", file=sys.stderr)

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(salida) + "\n")
    print(f"{total} canales guardados en {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
