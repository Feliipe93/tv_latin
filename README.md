# tv_latin

Lista IPTV filtrada a partir de [iptv-org](https://github.com/iptv-org/iptv) (`regions/lac.m3u`):
solo canales *Latin America*, *Pluto TV* y los chilenos (Mega, Meganoticias Ahora, Megatiempo,
T13 En Vivo, Canal 13, Chilevisión). Se mantiene sola, sin PC encendido ni servidor propio.

## URL de la lista (usa esta)

```
https://tv-latin.tvlatin.workers.dev
```

Pégala en VLC, TiviMate, IPTV Smarters, Kodi, etc. Es un Cloudflare Worker: cada vez que el
reproductor pide la lista, descarga `lac.m3u` de iptv-org en ese momento, la filtra con
`canales.txt` de este repo y la devuelve. Siempre está al día (los cambios en `canales.txt` se ven en pocos minutos).

### Lista de respaldo (si el Worker falla)

```
https://raw.githubusercontent.com/Feliipe93/tv_latin/main/tv_latin.m3u
```

Es una copia estática guardada en este repo, generada por GitHub Actions. Contiene los mismos
canales pero solo se actualiza cuando corre el workflow (ver más abajo). Si Actions está bloqueado
por facturación, el Worker sigue siendo la lista principal y se actualiza al solicitarla.

## Qué canales incluye

Lo define `canales.txt`:

- `[contiene]`: cualquier canal cuyo nombre o identificador `tvg-id` contenga el texto
  (ej. `Latin America`, `Pluto TV`). También se reconocen variantes sin espacios, como
  `TLCLatinAmerica`, para que los canales nuevos de iptv-org entren automáticamente.
- `[exactos]`: solo canales con ese nombre exacto (ej. `Mega (Chile)`, `T13 En Vivo`).
- `[excluir]`: canales a descartar aunque coincidan arriba.
- `[fuentes_extra]`: otras listas M3U que se añaden completas al final, con un sufijo en el
  nombre (`URL | sufijo`). Se usa para los canales de stream-tv-full servidos desde la VM
  (ver abajo). Si una fuente extra no responde, la lista sale igual sin ella.

Todas las entradas generadas incluyen `aspect-ratio="original"` en `#EXTINF`, para que los
reproductores compatibles respeten la proporción original del video en lugar de forzar 16:9.

Para agregar o quitar canales, edita `canales.txt` desde la web de GitHub y guarda.
El Worker toma el cambio solo (pocos minutos); la copia estática se regenera cuando corre Actions.

## Canales de stream-tv-full (VM Oracle, sufijo ` | pipe`)

Los streams de [stream-tv-full](https://github.com/Feliipe93/stream-tv-full) van atados a la IP,
caducan en horas y necesitan proxy, así que requieren una máquina encendida: una VM gratis de
Oracle Cloud. En [`vm/`](vm/README.md) está el instalador (`instalar.sh`) que monta el scraper
(cada 3 h), el proxy Apache y publica `http://IP-VM/listas/main_proxy.m3u`. Esa URL se añade en
`[fuentes_extra]` de `canales.txt` con el sufijo `| pipe`, y tanto el Worker como `tv_latin.m3u`
la fusionan al final: `ESPN Premium | pipe`, etc.

## Historia: por qué hay dos mecanismos

1. **Plan original: GitHub Actions.** `.github/workflows/actualizar.yml` ejecuta `filtrar.py`
   cada día a las 06:00 UTC, al editar `canales.txt` o manualmente (pestaña **Actions** →
   *Actualizar lista* → *Run workflow*), y hace commit de `tv_latin.m3u`.
   Al activarlo GitHub respondió *"The job was not started because your account is locked due to
   a billing issue"* (fallo de autorización de la tarjeta asociada a GitHub Pro). Para reactivarlo:
   actualizar la tarjeta en https://github.com/settings/billing/payment_information o escribir a
   https://support.github.com (Billing), y luego lanzar el workflow manualmente.
2. **Plan B (el que está en uso): Cloudflare Worker.** `worker/worker.js` hace el mismo filtrado
   al vuelo. Se desplegó con `wrangler` en la cuenta de Cloudflare del dueño del repo, en el
   subdominio `tvlatin.workers.dev`. Plan gratis: 100.000 peticiones/día, más que suficiente.

## Volver a desplegar el Worker

Solo hace falta si cambias `worker/worker.js` o quieres publicarlo en otra cuenta.
`canales.txt` NO requiere redesplegar.

Sin instalar nada:

1. https://dash.cloudflare.com → **Workers & Pages** → **tv-latin** (o **Create Worker** con ese nombre).
2. **Edit code** → borra todo, pega el contenido de [`worker/worker.js`](worker/worker.js) → **Deploy**.

Con terminal: `cd worker && npx wrangler deploy` (pide login de Cloudflare).

Si publicas en otra cuenta, cambia `CONFIG_URL` en `worker.js` si el repo también cambia de dueño.

## Si un canal se congela

Los streams son de terceros (iptv-org solo los recopila); si el servidor de origen va lento el
canal se congela sin importar la lista. Ayuda subir el buffer del reproductor
(VLC: Preferencias → Entrada/Códecs → *Caché de red* 3000–5000 ms; TiviMate: Ajustes → Reproductor →
Buffer) y evitar canales marcados `[Not 24/7]` o `[Geo-blocked]`. Un proxy intermedio no lo
arregla: recibiría el mismo stream lento.
