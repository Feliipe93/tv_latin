# tv_latin

Lista IPTV filtrada a partir de [iptv-org](https://github.com/iptv-org/iptv) (`regions/lac.m3u`),
actualizada automáticamente todos los días con GitHub Actions. No necesita PC ni servidor.

## URL de la lista

```
https://raw.githubusercontent.com/Feliipe93/tv_latin/main/tv_latin.m3u
```

```
Para desbloquear:

Ve a https://github.com/settings/billing/payment_information y actualiza/vuelve a agregar la tarjeta (o prueba otra).
Si sigue bloqueada, escribe a https://support.github.com (categoría Billing) — suelen desbloquear rápido.
Cuando se desbloquee, ve a https://github.com/Feliipe93/tv_latin/actions/workflows/actualizar.yml → "Run workflow"; si corre en verde, ya queda automático.
```

Pégala en VLC, TiviMate, IPTV Smarters, Kodi, etc.

## Qué canales incluye

Lo define `canales.txt`:

- `[contiene]`: cualquier canal cuyo nombre contenga el texto (ej. `Latin America`, `Pluto TV`).
- `[exactos]`: solo canales con ese nombre exacto (ej. `Mega (Chile)`, `T13 En Vivo`).
- `[excluir]`: canales a descartar aunque coincidan arriba.

Para agregar o quitar canales, edita `canales.txt` desde la web de GitHub y guarda:
el workflow se ejecuta al instante y regenera `tv_latin.m3u`.

## Cómo funciona

`.github/workflows/actualizar.yml` corre `filtrar.py` cada día a las 06:00 UTC (y también
al editar `canales.txt` o manualmente desde la pestaña **Actions** → *Actualizar lista* → *Run workflow*).
El script descarga `lac.m3u`, conserva solo los canales configurados y hace commit de `tv_latin.m3u`.

## Plan B: Cloudflare Worker (sin GitHub Actions)

Si Actions no está disponible, `worker/worker.js` genera la misma lista al vuelo: cada vez que
el reproductor pide la URL, el Worker descarga `lac.m3u`, la filtra con el `canales.txt` de este
repo y la devuelve. Siempre actualizada, gratis (100.000 peticiones/día) y sin servidor propio.

Pasos (5 minutos, sin instalar nada):

1. Crea una cuenta gratis en https://dash.cloudflare.com/sign-up.
2. En el panel: **Workers & Pages** → **Create** → **Create Worker**.
3. Ponle de nombre `tv-latin` y pulsa **Deploy**.
4. Pulsa **Edit code**, borra todo el código de ejemplo, pega el contenido de
   [`worker/worker.js`](worker/worker.js) y pulsa **Deploy**.
5. Tu lista queda en `https://tv-latin.<tu-subdominio>.workers.dev` (la URL aparece en el panel).

Para cambiar canales sigue editando `canales.txt` en GitHub: el Worker lo lee de ahí
(los cambios se ven en máximo 1 hora por la caché).

Si prefieres la terminal: `cd worker && npx wrangler deploy`.
