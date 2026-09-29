#!/usr/bin/env bash
# Instala stream-tv-full en una VM Ubuntu (probado pensando en Oracle Cloud Always Free, VM.Standard.A1.Flex):
#   - scraper (gen_dual_playlist_v2_no_cache_web_system.py --single) cada 3 h vía systemd timer
#   - Apache como proxy inverso de los streams y servidor de la lista generada
#
# Uso (en la VM, como usuario normal con sudo):
#   git clone https://github.com/Feliipe93/tv_latin.git && cd tv_latin/vm
#   DOMINIO=IP-PUBLICA-O-DNS ./instalar.sh
# Variables opcionales:
#   REPO      repo de stream-tv-full (por defecto el de GitHub; si es privado, clónalo antes en $DESTINO)
#   DESTINO   carpeta de instalación (por defecto /opt/stream-tv-full)
#   INTERVALO cada cuánto regenerar la lista (systemd OnUnitActiveSec, por defecto 3h)
set -euo pipefail

REPO="${REPO:-https://github.com/Feliipe93/stream-tv-full.git}"
DESTINO="${DESTINO:-/opt/stream-tv-full}"
INTERVALO="${INTERVALO:-3h}"
DOMINIO="${DOMINIO:-$(curl -fsS https://ifconfig.me || true)}"
[ -n "$DOMINIO" ] || { echo "Define DOMINIO=IP-o-dominio de esta VM"; exit 1; }

AQUI="$(cd "$(dirname "$0")" && pwd)"
SCRAPER_DIR="$DESTINO/python_scrapper_system/scrapper_master"
OUTPUT_DIR="$DESTINO/python_scrapper_system/output"
GEN="$SCRAPER_DIR/gen_dual_playlist_v2_no_cache_web_system.py"
USUARIO="$(id -un)"

echo "== 1/6 Paquetes del sistema"
sudo apt-get update -qq
sudo apt-get install -y -qq git curl python3 python3-venv python3-pip apache2 iptables-persistent

echo "== 2/6 Código de stream-tv-full en $DESTINO"
if [ ! -d "$DESTINO/.git" ]; then
  sudo mkdir -p "$DESTINO" && sudo chown "$USUARIO" "$DESTINO"
  git clone "$REPO" "$DESTINO"
fi
mkdir -p "$OUTPUT_DIR"

echo "== 3/6 Entorno Python + Playwright (Chromium)"
python3 -m venv "$DESTINO/.venv"
"$DESTINO/.venv/bin/pip" install -q --upgrade pip
"$DESTINO/.venv/bin/pip" install -q aiohttp requests psutil playwright beautifulsoup4 urllib3
"$DESTINO/.venv/bin/playwright" install --with-deps chromium

echo "== 4/6 Apuntar el scraper al proxy de esta VM ($DOMINIO, http)"
sed -i "s|^PROXY_DOMAIN = .*|PROXY_DOMAIN = '$DOMINIO'|" "$GEN"
sed -i 's|f"https://{PROXY_DOMAIN}/|f"http://{PROXY_DOMAIN}/|' "$GEN"

echo "== 5/6 Apache: proxy inverso + /listas/"
sudo a2enmod -q proxy proxy_http ssl headers >/dev/null
sudo a2dissite -q 000-default >/dev/null || true
sed -e "s|__DOMINIO__|$DOMINIO|g" -e "s|__OUTPUT__|$OUTPUT_DIR|g" "$AQUI/apache-tv-latin.conf" \
  | sudo tee /etc/apache2/sites-available/tv-latin.conf >/dev/null
sudo a2ensite -q tv-latin >/dev/null
sudo apachectl configtest
sudo systemctl restart apache2
# Oracle Ubuntu trae iptables cerrado: abrir el 80 (además abre el 80 en la Security List de la consola de Oracle)
if ! sudo iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null; then
  sudo iptables -I INPUT 5 -p tcp --dport 80 -m conntrack --ctstate NEW -j ACCEPT
  sudo netfilter-persistent save >/dev/null
fi

echo "== 6/6 systemd: regenerar la lista cada $INTERVALO"
sed -e "s|__USUARIO__|$USUARIO|g" -e "s|__DESTINO__|$DESTINO|g" -e "s|__SCRAPER_DIR__|$SCRAPER_DIR|g" \
  "$AQUI/tv-latin-scraper.service" | sudo tee /etc/systemd/system/tv-latin-scraper.service >/dev/null
sed -e "s|__INTERVALO__|$INTERVALO|g" "$AQUI/tv-latin-scraper.timer" \
  | sudo tee /etc/systemd/system/tv-latin-scraper.timer >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now tv-latin-scraper.timer
sudo systemctl start tv-latin-scraper.service || true

echo
echo "Listo. Lista generada por la VM:  http://$DOMINIO/listas/main_proxy.m3u"
echo "Añade esta línea en [fuentes_extra] de canales.txt (repo tv_latin):"
echo "  http://$DOMINIO/listas/main_proxy.m3u | | pipe"
echo
echo "Ver estado:  systemctl status tv-latin-scraper.timer   |   journalctl -u tv-latin-scraper -f"
