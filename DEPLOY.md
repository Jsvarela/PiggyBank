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
| `DATABASE_URL` | cadena de Neon del rol restringido `finanzas_app` (sección 2b) |
| `MIGRATION_DATABASE_URL` | cadena de Neon del dueño (`neondb_owner`); solo la usan las migraciones |
| `SECRET_KEY` | aleatoria y larga (la genera Render). Si la cambias, todas las sesiones se cierran |
| `COOKIE_SECURE` | `true` (la app **se niega a arrancar** en producción con la clave de ejemplo) |
| `SMTP_*`, `ANALYTICS_URL` | opcionales, ver secciones 6 y 8 |

## 2b. Aislamiento en la base de datos (RLS)
Además del filtro de la app, Postgres impide por sí mismo que alguien lea filas de otro usuario (Row Level
Security, migración `d4e8a1b7c203`). **RLS no se aplica al rol por defecto de Neon** (`neondb_owner` se salta
las políticas), así que la app debe conectarse con otro rol. En el **SQL Editor** de Neon, una sola vez
(cambia la contraseña) y **después** del primer despliegue con esta migración:

```sql
CREATE ROLE finanzas_app LOGIN PASSWORD 'una-clave-larga-y-distinta';
GRANT USAGE ON SCHEMA public TO finanzas_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO finanzas_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO finanzas_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO finanzas_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO finanzas_app;
```

Luego en Render: `MIGRATION_DATABASE_URL` = la cadena actual (dueño) y `DATABASE_URL` = la misma cadena pero con
usuario `finanzas_app` y su contraseña. Si la app sigue conectada como dueño, arranca igual pero escribe en el
log `RLS NO está protegiendo` (búscalo en los logs de Render tras desplegar).

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

**Respaldo automático (opcional).** El flujo `.github/workflows/backup.yml` descarga el respaldo cada
domingo y lo guarda 90 días como *artifact* del repositorio. Para activarlo, en GitHub →
*Settings → Secrets and variables → Actions* crea: `APP_URL` (tu URL de Render), `BACKUP_EMAIL` y
`BACKUP_PASSWORD` (tu usuario). Requisitos: el repositorio debe ser **privado** (el archivo contiene tus datos)
y debes aceptar guardar tu contraseña como secreto de GitHub. Para probarlo: *Actions → Respaldo semanal → Run workflow*.

## 6. Correo: recuperar contraseña y verificar correo (opcional pero recomendado)
Sin correo configurado la app funciona, pero **no se puede recuperar la contraseña por correo** (ver sección 7).
Cualquier servicio SMTP sirve; opciones con plan gratuito (verifica el plan vigente):

| Servicio | `SMTP_HOST` | Notas |
| :--- | :--- | :--- |
| Brevo | `smtp-relay.brevo.com` | Plan gratis con tope diario; usa tu clave SMTP, no la de la cuenta |
| Gmail | `smtp.gmail.com` | Requiere verificación en dos pasos y una «contraseña de aplicación» |

Variables en Render (todas opcionales; basta con `SMTP_HOST` para activar la función):

| Variable | Valor |
| :--- | :--- |
| `SMTP_HOST` | servidor SMTP |
| `SMTP_PORT` | `587` (STARTTLS, por defecto) |
| `SMTP_USER` / `SMTP_PASSWORD` | credenciales SMTP |
| `SMTP_FROM` | remitente, p. ej. `Finanzas <tucorreo@gmail.com>` |
| `APP_URL` | solo si usas dominio propio; en Render se toma sola |

## 7. Olvidé mi contraseña y no tengo correo configurado
Desde tu computador, apuntando a la base de datos de Neon (la misma `DATABASE_URL` de Render):
```bash
cd backend
DATABASE_URL="postgresql://..." uv run python -m app.reset_password
```
Pide la contraseña nueva y cierra todas las sesiones abiertas.

## 8. Errores y estadísticas
- **Errores:** los de la API quedan en el log de Render (*Logs*). Los del navegador (pantalla en blanco, fallos de JavaScript)
  se envían a `/api/client-errors` y aparecen en el mismo log con el prefijo `finanzas.client`. No hay alertas ni agrupación:
  para eso existe Sentry (plan gratis), que se podría conectar después.
- **Estadísticas (apagadas por defecto):** crea una cuenta gratis en goatcounter.com (uso personal) y define
  `ANALYTICS_URL=https://TU-CODIGO.goatcounter.com/count`. Solo cuenta qué pantalla se visita; no usa cookies ni envía montos.

## Probar la imagen en tu PC (opcional, requiere Docker)
```bash
docker build -t finanzas .
docker run --rm -p 8000:8000 -e DATABASE_URL=sqlite:////tmp/f.db finanzas
```

## Varias personas (multiusuario)
- **Antes de desplegar la migración multiusuario, descarga un respaldo JSON** (Más → Respaldo). La migración asigna todos los datos existentes al primer usuario, que pasa a ser admin.
- Invitar: Más → Invitar (solo admin). Cada enlace sirve una vez y vence en 7 días.
- Contraseña olvidada sin correo configurado: `uv run python -m app.reset_password <correo>` (ahora hay varios usuarios).
- Volver al código anterior después de migrar exige `alembic downgrade f2e66f436831` (las columnas `user_id` son NOT NULL).
- Capacidad: ~10 personas caben en Render + Neon gratis; el límite de login es por IP, así que una casa con la misma red podría rozarlo.
