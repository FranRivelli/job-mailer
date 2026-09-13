# 📨 Job Mailer — Guía Completa de Configuración y Uso

> **Stack:** Python · Streamlit · Gmail API (OAuth 2.0) · Claude API (opcional)  
> **Uso:** 100% personal, sin servidores externos, credenciales solo en tu máquina.

---

## Arquitectura general

```
job-mailer/
├── app.py               ← Interfaz Streamlit (formulario + preview + envío)
├── gmail_service.py     ← Conexión con Gmail API, construcción y envío del email
├── email_composer.py    ← Redacción: IA (Claude) o plantilla fija
├── config_manager.py    ← Lectura/escritura de config local
├── auth_gmail.py        ← Script de autenticación OAuth (se ejecuta 1 sola vez)
├── requirements.txt
├── .gitignore
└── config/              ← Carpeta privada (en .gitignore)
    ├── credentials.json ← Descargado de Google Cloud Console  [PRIVADO]
    ├── token.json       ← Generado por auth_gmail.py           [PRIVADO]
    └── settings.json    ← Tu nombre, email, ruta del CV        [PRIVADO]
```

**Por qué OAuth 2.0 y no contraseña de aplicación (App Password):**

| | OAuth 2.0 ✅ | App Password |
|---|---|---|
| Seguridad | Alta — token revocable | Media — equivale a tu contraseña |
| Requiere 2FA | No | Sí |
| Caduca automáticamente | Sí (se renueva solo) | No |
| Acceso granular | Solo `gmail.send` | Acceso completo a Gmail |
| Recomendado por Google | ✅ Sí | Solo como fallback |

---

## PASO 1 — Instalar dependencias

```bash
# Cloná o copiá la carpeta job-mailer donde prefieras
cd job-mailer

# (Recomendado) Crear entorno virtual
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# Instalar librerías
pip install -r requirements.txt
```

---

## PASO 2 — Configurar Google Cloud Console (10 minutos, una sola vez)

### 2.1 Crear proyecto

1. Ingresá a **[console.cloud.google.com](https://console.cloud.google.com)**
2. Clic en el selector de proyectos (arriba a la izquierda) → **"Nuevo proyecto"**
3. Nombre: `job-mailer` → **Crear**

### 2.2 Habilitar la Gmail API

1. Menú → **APIs y servicios** → **Biblioteca**
2. Buscá **"Gmail API"** → clic → **Habilitar**

### 2.3 Configurar la pantalla de consentimiento OAuth

1. **APIs y servicios** → **Pantalla de consentimiento de OAuth**
2. Tipo de usuario: **Externo** → Crear
3. Completá:
   - Nombre de la app: `Job Mailer`
   - Correo de soporte: tu Gmail
   - Correo del desarrollador: tu Gmail
4. En **"Alcances (Scopes)"**: clic en **"Agregar o quitar alcances"** → buscá y marcá:
   ```
   https://www.googleapis.com/auth/gmail.send
   ```
5. En **"Usuarios de prueba"**: agregá **tu propio correo Gmail** (esto es clave para apps en modo "Testing")
6. Guardar y continuar hasta terminar.

> ⚠️ **No necesitás publicar la app** ni pasar por revisión de Google.  
> Como es uso personal y tu correo está como "usuario de prueba", funciona perfecto.

### 2.4 Crear credenciales OAuth 2.0

1. **APIs y servicios** → **Credenciales** → **+ Crear credenciales** → **ID de cliente OAuth**
2. Tipo de aplicación: **Aplicación de escritorio**
3. Nombre: `job-mailer-desktop` → **Crear**
4. Clic en **"Descargar JSON"**
5. Renombrá el archivo descargado a `credentials.json`
6. Moveldo a la carpeta `config/` del proyecto:
   ```
   job-mailer/config/credentials.json   ✅
   ```

---

## PASO 3 — Autenticarse con Gmail (una sola vez)

```bash
# Desde la carpeta job-mailer, con el entorno virtual activado:
python auth_gmail.py
```

Esto va a:
1. Abrir tu navegador en la pantalla de autorización de Google
2. Pedirte que elijas tu cuenta Gmail y aceptes el permiso de envío
3. Guardar el token en `config/token.json`

**La primera vez puede aparecer una advertencia "Esta app no está verificada".**  
Es normal porque la app está en modo Testing. Hacé clic en **"Avanzado" → "Ir a job-mailer (no seguro)"**.  
(Solo aparece porque vos mismo sos el desarrollador y el único usuario).

---

## PASO 4 — (Opcional) API Key de Claude para redacción con IA

1. Ingresá a **[console.anthropic.com](https://console.anthropic.com)**
2. **API Keys** → **Create Key** → copiá la clave
3. En la barra lateral de la app, pegá la clave en el campo **"Anthropic API Key"**

Si no querés usar IA, seleccioná **"Plantilla fija"** en la configuración — funciona sin ninguna API externa.

---

## PASO 5 — Ejecutar la aplicación

```bash
# Desde la carpeta job-mailer:
streamlit run app.py
```

La app se abre automáticamente en `http://localhost:8501`

### Flujo de uso

```
1. Barra lateral → Completá tu nombre, Gmail y ruta del CV → Guardar
2. Formulario    → Empresa, Puesto, Email de destino, descripción
3. "Generar preview" → Revisá y editá el cuerpo del correo
4. "Enviar postulación" → ¡Listo!
```

---

## Seguridad y privacidad

| Qué | Dónde se guarda | ¿Sale de tu máquina? |
|---|---|---|
| `credentials.json` | `config/` local | ❌ No |
| `token.json` | `config/` local | ❌ No |
| Tu API Key de Claude | `config/settings.json` | Solo para llamar a la API de Anthropic |
| Tu CV | Ruta local que elegís | Solo como adjunto en el correo que vos enviás |
| Historial de envíos | `config/sent_log.json` | ❌ No |

**Todos los archivos de `config/` están en `.gitignore`**. Si usás git, nunca se suben.

---

## Solución de problemas frecuentes

### ❌ "No hay credenciales válidas"
→ Ejecutá `python auth_gmail.py` de nuevo.

### ❌ "CV no encontrado"
→ Verificá la ruta en la barra lateral. En Windows usá barras invertidas: `C:\Users\fran\CV.pdf`

### ❌ El correo llega a spam
→ Esto es raro enviando desde la Gmail API con tu propia cuenta. Si pasa:
- Usá un asunto no genérico (la app ya personaliza el asunto)
- Evitá palabras como "urgente", "gratis", etc. en el cuerpo

### ❌ Error 403 en Gmail API
→ Verificá que tu correo esté en la lista de "usuarios de prueba" en Google Cloud Console (Paso 2.3).

### ❌ "This app isn't verified" en el navegador
→ Clic en "Advanced" → "Go to job-mailer (unsafe)". Es seguro porque la app la creaste vos.

---

## Extensiones futuras (ideas)

- 📊 **Dashboard de postulaciones**: visualizar estado de cada aplicación (enviada, respondida, etc.)
- 📁 **CV desde Google Drive**: seleccionar el CV directamente desde tu Drive
- 📅 **Recordatorios**: avisar si no recibiste respuesta en X días
- 📧 **Múltiples plantillas**: una plantilla por tipo de empresa o industria
