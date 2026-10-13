# App de finanzas personales: plan y prompt para Claude Code

## Parte 1: Decisiones tomadas

| Tema | Decisión | Por qué |
| :---- | :---- | :---- |
| Plataforma | PWA (app web instalable) | Un solo código sirve en el celular (se instala desde el navegador) y en el PC. No requiere Play Store. |
| Frontend | React \+ TypeScript \+ Vite \+ vite-plugin-pwa | Es el ecosistema PWA mejor documentado y Claude Code lo maneja muy bien. |
| Backend | Python \+ FastAPI \+ SQLAlchemy 2 \+ Alembic \+ Pydantic v2 | Ya sabes Python. FastAPI genera la documentación de la API sola (`/docs`). |
| Base de datos | SQLite en desarrollo, PostgreSQL en producción | SQLite no necesita instalar nada. Postgres es lo que ofrecen los hostings gratuitos. |
| Uso | Personal real, un solo usuario | Simplifica permisos, pero igual necesita login porque va a estar en internet. |
| Funciones v1 | Cuentas, categorías, ingresos, gastos, transferencias, presupuestos con alertas, recurrentes y metas de ahorro | Lo que elegiste. |

## Parte 2: Lo que hay que tener en cuenta (antes de escribir código)

### 1\. El dinero no se guarda en `float`

`0.1 + 0.2 != 0.3`. Guarda los montos como **enteros** (pesos colombianos sin decimales, o centavos si algún día usas USD) o como `Decimal`/`NUMERIC` en la base de datos. Esta es la regla número uno de cualquier app financiera.

### 2\. Los saldos se calculan, no se escriben a mano

El saldo de una cuenta \= saldo inicial \+ ingresos − gastos ± transferencias. Si guardas el saldo en una columna aparte, tarde o temprano se desincroniza. Calcúlalo con una consulta (con índices es rápido para miles de movimientos).

### 3\. Una transferencia no es un gasto

Pasar plata de Bancolombia a Nequi no es un gasto. Debe ser un tipo `transfer` con cuenta origen y destino, y debe quedar fuera de los reportes de gastos. Pagar la tarjeta de crédito también es una transferencia (de la cuenta bancaria a la tarjeta), y la compra con tarjeta es el gasto.

### 4\. Las tarjetas de crédito tienen saldo negativo

Modela la tarjeta como una cuenta cuyo saldo es deuda. Así el "patrimonio neto" (suma de todas las cuentas) sale correcto solo.

### 5\. Los recurrentes en hosting gratuito

Los servidores gratuitos se "duermen" cuando nadie los usa, así que un cron a medianoche puede no correr. La solución robusta es la **generación perezosa (catch-up)**: cada vez que abres la app, el backend revisa qué recurrentes debieron ejecutarse desde la última vez y los crea. Así no dependes de un proceso en segundo plano.

### 6\. Fechas y zona horaria

Guarda la fecha del movimiento como `date` (el día en que gastaste), no como timestamp UTC, o un gasto de las 9 p. m. puede aparecer al día siguiente. Usa `America/Bogota` para decidir el "hoy" y el mes actual.

### 7\. Seguridad mínima

- Contraseña con hash **argon2** o bcrypt, nunca en texto plano.  
- Token de sesión en cookie `httpOnly` \+ `Secure` \+ `SameSite`.  
- Limita los intentos de login.  
- HTTPS obligatorio (además, las PWA solo se instalan con HTTPS).  
- Secretos en variables de entorno (`.env` dentro del `.gitignore`).  
- **Nunca** guardes contraseñas de banco ni números completos de tarjeta. Si algún día importas extractos, que sea desde un CSV descargado por ti.

### 8\. Respaldos

Es tu información financiera real: exporta a CSV/JSON desde la app y programa un respaldo de la base de datos. Revisa si tu hosting gratuito borra la base de datos después de un tiempo; algunos lo hacen.

### 9\. PWA en el celular

- Android/Chrome: botón "Instalar app". Funciona muy bien.  
- iPhone: solo se instala desde Safari con "Agregar a pantalla de inicio". Las notificaciones push solo funcionan si está instalada (iOS 16.4+).  
- Para la v1, las alertas de presupuesto pueden mostrarse **dentro de la app** (banner o badge). Deja las notificaciones push para después.

### 10\. Modo sin conexión

Registrar un gasto en la tienda sin señal es un caso real. Hacerlo bien (cola offline \+ sincronización) es lo más complejo del proyecto, así que va en una fase aparte, al final.

### 11\. Hosting (verifica los planes gratuitos al momento de desplegar, cambian seguido)

- Frontend: Vercel, Netlify o Cloudflare Pages.  
- Backend: Render, Railway, Fly.io o Koyeb.  
- Postgres: Neon o Supabase.  
- Alternativa sin nube: el backend corre en tu PC y el celular entra por **Tailscale**. Es gratis y privado, pero el PC tiene que estar prendido.

### 12\. Cómo trabajar con Claude Code

- Arranca en **modo plan** (Shift+Tab dos veces) y no aceptes código hasta que el plan te convenza.  
- Pide que cree un `CLAUDE.md` con las reglas del proyecto. Lo lee en cada sesión.  
- Una fase a la vez. Al final de cada fase: tests en verde, revisas, haces commit.  
- Pídele tests **antes** de la lógica de dinero (saldos, presupuestos, recurrentes). Ahí es donde un error cuesta.  
- Si una sesión se alarga mucho, usa `/clear` y continúa con "lee CLAUDE.md y sigue con la fase N".

---

## Parte 3: El prompt (cópialo tal cual en Claude Code)

Quiero construir una app de finanzas personales para uso propio (un solo usuario, yo).

Debe funcionar en mi celular y en mi computador. Antes de escribir código, entra en modo

plan, revisa este documento, hazme las preguntas que tengas y propón la estructura de

carpetas, el modelo de datos y los endpoints. Espera mi aprobación antes de implementar.

\#\# Stack

\- Frontend: PWA con React \+ TypeScript \+ Vite, vite-plugin-pwa, React Router,

  TanStack Query para datos del servidor, React Hook Form \+ Zod para formularios.

  Estilos con Tailwind. Mobile-first (pantalla de 360px), pero usable en escritorio.

\- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 (estilo tipado), Alembic, Pydantic v2.

\- BD: SQLite en desarrollo, PostgreSQL en producción (configurable por DATABASE\_URL).

\- Tests: pytest (backend) y Vitest (frontend). Linter/formato: ruff y eslint/prettier.

\- Monorepo: /backend y /frontend, con un README que explique cómo correr todo.

\- Gestión de dependencias del backend con uv (o pip \+ requirements.txt si uv no está).

\#\# Reglas no negociables

1\. El dinero NUNCA se guarda ni se calcula con float. Usa enteros (pesos COP, sin

   decimales) o Decimal/NUMERIC. Moneda por defecto: COP. Formato: \$ 1.234.567.

2\. Los saldos de cuentas se CALCULAN a partir de los movimientos; no hay columna de saldo.

3\. Las transferencias entre cuentas no cuentan como ingreso ni como gasto en los reportes.

4\. Las fechas de los movimientos son \`date\`. "Hoy" y "mes actual" se calculan en

   America/Bogota.

5\. Seguridad: hash argon2, sesión con JWT en cookie httpOnly/Secure/SameSite, rate

   limit en el login, CORS restringido al dominio del frontend, secretos en .env

   (y .env.example en el repo).

6\. Toda la lógica de negocio (saldos, presupuestos, recurrentes, metas) va en una capa

   de servicios separada de las rutas, con tests unitarios escritos ANTES de la

   implementación.

7\. Interfaz en español.

\#\# Modelo de datos (propuesta: ajústala si ves algo mejor y explícame por qué)

\- User: id, email, password\_hash, created\_at.

\- Account: id, name, type (cash | bank | digital\_wallet | credit\_card | savings),

  initial\_balance, color, icon, archived, created\_at.

  Ejemplos: Efectivo, Bancolombia, Nequi, Daviplata, Tarjeta de crédito.

  Las tarjetas de crédito llevan saldo negativo (deuda).

\- Category: id, name, kind (income | expense), parent\_id (subcategorías, 1 nivel),

  color, icon, archived. Sembrar categorías por defecto (Comida, Transporte,

  Vivienda, Servicios, Universidad, Ocio, Salud, Suscripciones, Salario, Freelance,

  Regalos, Otros).

\- Transaction: id, type (income | expense | transfer), amount (\>0), date,

  account\_id, to\_account\_id (solo transfer), category\_id (null en transfer),

  description, tags, recurring\_rule\_id (nullable), goal\_id (nullable), created\_at.

\- Budget: id, category\_id, month (YYYY-MM) o is\_default, limit\_amount,

  alert\_threshold (por defecto 80%).

\- RecurringRule: id, plantilla del movimiento (type, amount, account, category,

  description), frequency (daily | weekly | biweekly | monthly | yearly),

  start\_date, end\_date nullable, next\_run\_date, active.

\- SavingsGoal: id, name, target\_amount, deadline nullable, account\_id opcional,

  created\_at. El progreso se calcula sumando los aportes (movimientos con goal\_id).

\#\# Funcionalidades por fases (haz commit al terminar cada fase)

\#\#\# Fase 0: Esqueleto

Monorepo, configuración, CLAUDE.md con estas reglas, health check, CI básica

(GitHub Actions corriendo tests y linters), seed de datos de ejemplo.

\#\#\# Fase 1: Núcleo

\- Registro (solo se permite crear el primer usuario; después se desactiva), login

  y logout.

\- CRUD de cuentas, categorías y movimientos.

\- Registro rápido: desde la pantalla principal, botón "+" y en menos de 3 toques

  quedan monto, categoría y cuenta. Fecha por defecto: hoy; la última cuenta

  usada queda preseleccionada.

\- Lista de movimientos con filtros (rango de fechas, cuenta, categoría, tipo,

  texto) y paginación.

\- Inicio: saldo por cuenta, patrimonio total, ingresos y gastos del mes y

  últimos movimientos.

\#\#\# Fase 2: Presupuestos y alertas

\- Presupuesto mensual por categoría (con opción de repetirlo cada mes).

\- Barra de progreso por categoría: gastado / límite, días restantes del mes.

\- Alertas dentro de la app al pasar el umbral (80%) y al superar el 100%.

\- Resumen mensual: gasto por categoría y comparación con el mes anterior.

\#\#\# Fase 3: Recurrentes y metas

\- Reglas recurrentes (arriendo, Netflix, salario, etc.).

\- Generación perezosa: en cada petición autenticada (o en un endpoint /sync que el

  frontend llama al abrir), crear los movimientos pendientes desde next\_run\_date

  hasta hoy y avanzar next\_run\_date. Debe ser idempotente (sin duplicados si se

  llama dos veces). Ojo con los fines de mes (una regla del 31 en febrero).

\- Lista de "próximos pagos" de los siguientes 30 días.

\- Metas de ahorro: progreso, monto mensual sugerido para llegar a la fecha y

  botón para aportar (crea una transferencia hacia la cuenta de ahorro).

\#\#\# Fase 4: PWA y despliegue

\- Manifest, íconos, service worker (cache del app shell), instalable en Android

  e iOS. Pantalla de "instalar app".

\- Exportar movimientos a CSV y respaldo completo a JSON (y restaurar desde JSON).

\- Despliegue: Dockerfile para el backend y guía paso a paso para desplegar

  frontend, backend y Postgres en servicios con plan gratuito. Variables de

  entorno documentadas. HTTPS.

\#\#\# Fase 5 (opcional, después): Offline y extras

\- Cola offline de movimientos con IndexedDB (Dexie) que se sincroniza al volver

  la conexión, con IDs generados en el cliente (UUID) para evitar duplicados.

\- Importar extractos bancarios en CSV con mapeo de columnas.

\- Notificaciones push de presupuestos.

\- Modo oscuro.

\#\# Tests mínimos obligatorios

\- Saldo de cuenta con ingresos, gastos y transferencias en ambas direcciones.

\- La transferencia no aparece en los totales de ingresos/gastos.

\- El presupuesto se calcula solo con gastos del mes en America/Bogota.

\- Recurrentes: idempotencia, varias ejecuciones atrasadas, fin de mes,

  end\_date respetado.

\- Metas: progreso y monto mensual sugerido.

\- Auth: rutas protegidas devuelven 401 sin sesión; no se puede registrar un

  segundo usuario.

\#\# Forma de trabajo

\- Empieza en modo plan. No escribas código hasta que apruebe el plan de la fase.

\- Trabaja una fase a la vez. Al terminarla: tests en verde, linters limpios,

  resumen de lo hecho y de cómo probarlo a mano, y commit con mensaje claro.

\- Si una decisión no está en este documento, pregúntame en vez de suponer.

\- Explícame brevemente las decisiones de arquitectura importantes: quiero

  entender el código, no solo tenerlo.

---

## Parte 4: Orden sugerido para arrancar

1. Instala Python 3.12+, Node 20+, Git y Claude Code.  
2. Crea una carpeta vacía, `git init`, abre Claude Code ahí.  
3. Pega el prompt de la Parte 3\.  
4. Revisa el plan que te proponga (sobre todo el modelo de datos) antes de aprobarlo.  
5. Avanza fase por fase. Empieza a usar la app con datos reales desde la Fase 1 (aunque sea en local); así descubres qué te falta de verdad.