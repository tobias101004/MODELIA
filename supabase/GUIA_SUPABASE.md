# Guia paso a paso — configuracion de Supabase y Railway para MODELIA

Esta guia te explica que tienes que tocar tu en el panel de Supabase y en
Railway. Yo (Claude) ya he dejado todo el codigo listo en el repo; estos
son los pasos manuales que no se pueden hacer desde codigo.

Sigue el orden de los pasos. **No te saltes ninguno**, sobre todo el del
SQL: sin esa migracion, la base de datos no esta segura.


## 1. Confirmar plan Pro de Supabase

1. Entra en https://supabase.com/dashboard.
2. Selecciona el proyecto `pntipdspiivffvxfyshg`.
3. Arriba a la izquierda, junto al nombre del proyecto, comprueba que
   pone **Pro** (no Free). Si pone Free, ve a **Settings → Billing** y
   pasate al plan Pro. Esto es lo que evita que el proyecto se congele
   por inactividad.


## 2. Configurar el envio de codigos por email (OTP)

En el panel de Supabase, ve a **Authentication → Providers → Email** y
deja los toggles asi:

| Opcion | Valor |
|---|---|
| Enable Email provider | **ON** |
| Confirm email | **OFF** (con OTP no hace falta, lo confirma el propio codigo) |
| Secure email change | **ON** |
| Secure password change | (da igual, no usamos password) |
| Enable Email Signup | **ON** (lo necesitamos para auto-crear cuentas la primera vez) |

Guarda.

A continuacion, abre **Authentication → Email Templates → Magic Link**
y personaliza el asunto/cuerpo del email para que se vea profesional. El
codigo se envia en la variable `{{ .Token }}`. Sugerencia:

- **Subject:** `Tu codigo de acceso — Cardenas Portal IA`
- **Body (HTML):**
  ```html
  <h2>Tu codigo de acceso</h2>
  <p>Hola,</p>
  <p>Has solicitado iniciar sesion en el Portal IA de Cardenas. Tu
  codigo de acceso es:</p>
  <p style="font-size:28px;font-weight:bold;letter-spacing:6px;
            background:#f5f5f7;padding:14px 24px;border-radius:8px;
            display:inline-block;">{{ .Token }}</p>
  <p>El codigo caduca en 60 minutos.</p>
  <p style="color:#888;font-size:12px;">Si no has solicitado este
  codigo, ignora este mensaje.</p>
  ```


## 3. Anadir la URL de Railway como Site URL

Ve a **Authentication → URL Configuration** y pon:

- **Site URL:** la URL publica de tu app en Railway (ej.
  `https://modelia.up.railway.app`). Si no la sabes, ve a Railway,
  selecciona el servicio, pestana **Settings → Networking** y copia la
  Public Domain.
- **Redirect URLs:** anade esa misma URL.

(Si no la tienes desplegada todavia, esto se puede dejar para despues.
El login por OTP no usa redirect, asi que funcionara igual en local.)


## 4. Ejecutar la migracion SQL

Esto es **lo mas importante**. Sin esto, cualquiera con la anon key
podria leer la base de datos.

1. Abre el fichero `supabase/policies.sql` del repo (lo he creado yo).
2. Copia todo el contenido.
3. En Supabase, ve a **SQL Editor → New Query**.
4. Pega el SQL completo y pulsa **Run**.

Si todo va bien veras "Success. No rows returned". Si te da error de
que alguna tabla no existe (`audit_sessions`, `leads`, etc.), me
avisas y ajustamos.

> **Aviso:** el trigger del paso SQL **bloquea altas con emails que no
> sean @cardenas-grancanaria.com**. Si por accidente ya tienes algun
> usuario de prueba con gmail/otro dominio, no podras "loguear" como el
> (el verificador del backend tambien lo rechaza). Borralo desde
> **Authentication → Users**.


## 5. Conseguir las claves de Supabase

Ve a **Settings → API** y copia:

- **Project URL:** algo como `https://pntipdspiivffvxfyshg.supabase.co`
- **Project API keys → anon (public):** un JWT largo. Es publica, se
  puede exponer en el frontend.
- **Project API keys → service_role (secret):** otro JWT largo.
  **NUNCA** la subas al frontend ni al repo. Solo va en variables de
  entorno del servidor.


## 6. Anadir las variables de entorno en Railway

En Railway, abre tu servicio MODELIA y ve a **Variables**. Anade
estas tres (las dos que ya tienes las dejas igual):

| Variable | Valor |
|---|---|
| `SUPABASE_URL` | `https://pntipdspiivffvxfyshg.supabase.co` |
| `SUPABASE_ANON_KEY` | la anon key del paso anterior |
| `SUPABASE_SERVICE_ROLE_KEY` | la service_role key del paso anterior |
| `ALLOWED_EMAIL_DOMAIN` | `cardenas-grancanaria.com` |

Las otras que ya tenias (`OPENAI_API_KEY`, etc.) NO las toques.

Railway redespliega automaticamente al guardar variables. Espera a
que el deploy termine (1-2 min).


## 7. Probar que todo funciona

Abre la URL publica de Railway en una pestana **incognita** (importante,
para no usar sesion vieja):

1. Veras la nueva pantalla de login: solo pide email.
2. Mete tu email `@cardenas-grancanaria.com`.
3. Pulsa **Enviar codigo**.
4. Mira tu correo. Llegara un email con un codigo de 6 digitos.
5. Pega el codigo en la app y pulsa **Verificar y entrar**.
6. Deberias entrar al dashboard.

**Pruebas de seguridad que deberian fallar (esto es lo bueno):**

- Mete un email gmail.com y pulsa **Enviar codigo**: deberia decirte
  "Solo se aceptan correos @cardenas-grancanaria.com".
- Tras entrar, refresca la pagina (F5): debe quedarte logueado sin
  pedirte codigo otra vez (la sesion dura 1 hora y se renueva sola).
- Pulsa **Cerrar sesion**: vuelve a la pantalla de login.
- Cierra el navegador y vuelve a entrar: la sesion sigue activa (porque
  Supabase guarda el refresh token en localStorage). Si quieres que
  caduque al cerrar el navegador, dimelo y lo cambiamos.


## 8. Repaso final

- Cada empleado se hace su cuenta entrando con su email corporativo y
  metiendo el codigo. No hace falta que admin cree nada.
- Si un empleado se va, ve a **Authentication → Users** y borralo. Al
  siguiente intento de login se le rechazara.
- Los datos de la auditoria (sesiones, checks, PDFs en Storage) ya
  estan protegidos por RLS: solo usuarios autenticados pueden tocarlos.
- Los endpoints del backend (Modelo 211, comprobacion, auditoria,
  chatbot) ya estan protegidos: cualquier llamada sin token JWT valido
  devuelve 401.

Cualquier cosa que no encaje, me dices y lo ajustamos.
