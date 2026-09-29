"""Genera tv_latin.m3u filtrando la lista lac.m3u de iptv-org según canales.txt."""

import re
import sys
import urllib.request

SOURCE_URL = "https://iptv-org.github.io/iptv/regions/lac.m3u"
CONFIG_FILE = "canales.txt"
OUTPUT_FILE = "tv_latin.m3u"

SUFFIX_RE = re.compile(r"\s*(\(\d+p\)|\[[^\]]*\])")


def leer_config(path):
    reglas = {"contiene": [], "exactos": [], "excluir": []}
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
            reglas[seccion].append(linea.lower())
    return reglas


def nombre_limpio(extinf):
    nombre = extinf.rsplit(",", 1)[-1]
    return SUFFIX_RE.sub("", nombre).strip().lower()


def coincide(nombre, reglas):
    if any(ex in nombre for ex in reglas["excluir"]):
        return False
    if nombre in reglas["exactos"]:
        return True
    return any(kw in nombre for kw in reglas["contiene"])


def main():
    reglas = leer_config(CONFIG_FILE)
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as resp:
        lineas = resp.read().decode("utf-8").splitlines()

    salida = ["#EXTM3U"]
    total = 0
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        if linea.startswith("#EXTINF"):
            bloque = [linea]
            i += 1
            while i < len(lineas) and lineas[i].startswith("#"):
                bloque.append(lineas[i])
                i += 1
            if i < len(lineas):
                bloque.append(lineas[i])
                i += 1
            if coincide(nombre_limpio(linea), reglas):
                salida.extend(bloque)
                total += 1
        else:
            i += 1

    if total == 0:
        sys.exit("Ningún canal coincidió; no se sobrescribe la lista.")

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(salida) + "\n")
    print(f"{total} canales guardados en {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
