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
