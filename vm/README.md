# VM (Oracle Cloud Always Free) para los canales de stream-tv-full

Los streams de `stream-tv-full` van atados a la IP que los pide, caducan en horas y exigen
cabeceras `Referer`/`Origin`; por eso necesitan una máquina encendida 24/7 que los renueve y
haga de proxy. Esta carpeta monta todo eso en una VM gratis de Oracle y publica una lista
`main_proxy.m3u` que `tv_latin` fusiona con el sufijo ` | pipe`.

## 1. Crear la VM (una vez)
1. https://www.oracle.com/cloud/free/ → *Start for free* (pide tarjeta solo para verificar).
2. Compute → Instances → *Create instance*:
   - Image: **Ubuntu 22.04 o 24.04**
   - Shape: **VM.Standard.A1.Flex** (Always Free; si dice "Out of capacity" reintenta otra hora u otro AD)
   - Descarga la **clave SSH privada** que ofrece.
3. En Networking → Virtual Cloud Network → Security List de la subred → *Add Ingress Rule*:
   `Source 0.0.0.0/0`, `TCP`, `Destination port 80`.
4. Anota la **IP pública** de la instancia.

## 2. Instalar
```bash
ssh -i clave.key ubuntu@IP-PUBLICA
git clone https://github.com/Feliipe93/tv_latin.git && cd tv_latin/vm
# si stream-tv-full es privado, clónalo antes tú mismo en /opt/stream-tv-full
DOMINIO=IP-PUBLICA ./instalar.sh
```
El script:
- clona `stream-tv-full` en `/opt/stream-tv-full`, crea un venv e instala Playwright + Chromium;
- cambia `PROXY_DOMAIN` del scraper a la IP/dominio de la VM (y `https://` → `http://`,
  porque la VM no tiene certificado; si luego pones un dominio con TLS, deshaz ese cambio);
- instala Apache con el proxy inverso (`/deportes1/ /deportes2/ /general/ /regionales/ /playlist/`)
  y publica `python_scrapper_system/output/` en `http://IP/listas/`;
- crea `tv-latin-scraper.timer`, que ejecuta el scraper con `--single` cada 3 h
  (cámbialo con `INTERVALO=6h ./instalar.sh`).

## 3. Conectar con tv_latin
En `canales.txt` del repo, dentro de `[fuentes_extra]`:
```
http://IP-PUBLICA/listas/main_proxy.m3u | | pipe
```
A partir de ahí el Worker (https://tv-latin.tvlatin.workers.dev) y `tv_latin.m3u` añaden esos
canales al final con el nombre `Canal X | pipe`. Si la VM está caída, la lista sigue saliendo
solo con los canales de iptv-org.

## Comprobar / mantener
```bash
systemctl status tv-latin-scraper.timer       # próxima ejecución
journalctl -u tv-latin-scraper -n 100 -f      # salida del scraper
curl -sI http://localhost/listas/main_proxy.m3u | head -1
sudo systemctl start tv-latin-scraper.service # regenerar ahora
```

## Limitaciones
- El scraper se usa tal cual está en `stream-tv-full`; si el sitio origen cambia su HTML o su
  protección, dejará de encontrar streams y habrá que repararlo allí (no aquí).
- La lista se sirve por `http://` (sin TLS). Para `https://` necesitarías un dominio propio y
  Certbot; después cambia `PROXY_DOMAIN`/esquema en el scraper y la línea de `[fuentes_extra]`.
- El scraper intenta avisar a `http://localhost/api/auto_sync_webhook.php`; en la VM no existe
  y solo genera un aviso en el log, no afecta a la lista.
