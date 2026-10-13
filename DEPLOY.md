# Despliegue gratuito: Render + Neon

Un solo servicio en Render sirve la API **y** el frontend (mismo dominio), y Neon guarda la base de datos.
Así las cookies de sesión funcionan en iPhone/Safari y no hay CORS ni proxy que configurar.

> Los planes gratuitos cambian seguido. Los datos de abajo se revisaron en octubre de 2026;
> confírmalos en [render.com/pricing](https://render.com/pricing) y [neon.com/pricing](https://neon.com/pricing).

| Pieza | Servicio | Qué incluye el plan gratis (verificado oct. 2026) | Ojo |
| :--- | :--- | :--- | :--- |
| API + frontend | Render Web Service | 750 h/mes; HTTPS automático | Se duerme a los 15 min sin tráfico; despertar tarda ~1 min |
| Base de datos | Neon Postgres | 0,5 GB, sin tarjeta | Se pausa tras 5 min sin uso (el primer acceso tarda unos segundos); historial de solo 6 h |

**No uses Render Postgres gratis:** expira a los 30 días.

## 1. Base de datos (Neon)
1. Crea una cuenta en neon.com y un proyecto nuevo (región cercana, p. ej. `us-east`).
2. Copia la **connection string** (empieza con `postgresql://` y termina con `?sslmode=require`).

## 2. Servicio (Render)
1. En render.com: **New → Blueprint** y elige tu repositorio de GitHub (usa `render.yaml`).
2. Cuando pida `DATABASE_URL`, pega la cadena de Neon. `SECRET_KEY` se genera sola.
3. Espera el primer despliegue (compila el frontend y corre las migraciones al arrancar).
4. Abre la URL `https://finanzas-xxxx.onrender.com`, toca **Primera vez: crear usuario** y registra el tuyo.
   Después el registro se cierra solo.

Variables (todas en el panel de Render):

| Variable | Valor |
| :--- | :--- |
| `DATABASE_URL` | cadena de Neon |
| `SECRET_KEY` | aleatoria y larga (la genera Render). Si la cambias, todas las sesiones se cierran |
| `COOKIE_SECURE` | `true` (la app **se niega a arrancar** en producción con la clave de ejemplo) |

## 3. Instalar en el celular
- **Android (Chrome):** menú ⋮ → *Instalar app*, o el botón en **Más → Instalar app**.
- **iPhone:** abre la URL en **Safari** → Compartir → *Agregar a pantalla de inicio*. Solo se puede desde Safari.

La interfaz queda guardada en el teléfono: abre al instante aunque el servidor esté dormido; los datos
aparecen cuando el servidor despierta (~1 min la primera vez tras un rato sin usarlo).

## 4. Evitar que se duerma (opcional)
Un monitor gratuito (p. ej. UptimeRobot) que consulte `https://TU-URL/api/health` cada 5 minutos lo mantiene despierto.
Un servicio encendido todo el mes gasta ~730 de las 750 horas gratuitas, así que solo cabe **un** servicio así.

## 5. Respaldos (importante)
Neon gratis guarda solo 6 horas de historial. Entra a **Más → Respaldo y exportación** y descarga el
**respaldo JSON** de vez en cuando (por ejemplo, el día 1 de cada mes). Se restaura desde la misma pantalla.
El CSV es para abrir en Excel.

## Probar la imagen en tu PC (opcional, requiere Docker)
```bash
docker build -t finanzas .
docker run --rm -p 8000:8000 -e DATABASE_URL=sqlite:////tmp/f.db finanzas
```
