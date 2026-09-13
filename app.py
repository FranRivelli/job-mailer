"""
╔══════════════════════════════════════════════════════════╗
║          JOB MAILER — Automatizador de Postulaciones     ║
║          Autor: uso personal                             ║
║          Stack: Python + Streamlit + Gmail API           ║
╚══════════════════════════════════════════════════════════╝

Flujo:
  1. El usuario completa el formulario con datos de la vacante.
  2. La IA (o plantilla fija) redacta el cuerpo del correo.
  3. Se adjunta el CV desde ruta local.
  4. Se envía vía Gmail API (OAuth 2.0) desde tu propia cuenta.
"""

import streamlit as st
import os
import json
from pathlib import Path
from datetime import datetime
import time
import threading

# Módulos propios del proyecto
from gmail_service import GmailService
from email_composer import compose_email_with_ai, compose_email_with_template, extract_cv_text, extract_job_data
from config_manager import load_config, save_config


# ─── Historial de envíos (definida aquí para estar disponible en toda la app) ─
def _log_sent(company, position, to_email):
    """Guarda un registro local de postulaciones enviadas."""
    log_path = Path("config/sent_log.json")
    entry = {"date": datetime.now().isoformat(), "company": company,
             "position": position, "to": to_email}
    logs = []
    if log_path.exists():
        with open(log_path) as f:
            logs = json.load(f)
    logs.insert(0, entry)
    with open(log_path, "w") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

# ─── Configuración de página ────────────────────────────────────────────────
st.set_page_config(
    page_title="Job Mailer",
    page_icon="📨",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ─── CSS personalizado ───────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Fuente y fondo general */
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    /* Encabezado principal */
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
        color: white;
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        border-left: 5px solid #3b82f6;
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; font-weight: 600; }
    .main-header p  { margin: 0.4rem 0 0; opacity: 0.7; font-size: 0.95rem; }

    /* Sección de formulario */
    .section-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
    }
    .section-title {
        font-family: 'DM Mono', monospace;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #64748b;
        margin-bottom: 1rem;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 0.5rem;
    }

    /* Preview del correo */
    .email-preview {
        background: white;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 1.5rem;
        font-family: 'DM Mono', monospace;
        font-size: 0.85rem;
        line-height: 1.7;
        white-space: pre-wrap;
        color: #334155;
        max-height: 420px;
        overflow-y: auto;
    }

    /* Badge de estado */
    .status-ok  { color: #16a34a; font-weight: 600; }
    .status-err { color: #dc2626; font-weight: 600; }

    /* Botón principal */
    .stButton > button {
        background: #1e3a5f;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        width: 100%;
        transition: background 0.2s;
    }
    .stButton > button:hover { background: #3b82f6; }
</style>
""", unsafe_allow_html=True)


# ─── Encabezado ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📨 Job Mailer</h1>
    <p>Automatizador de postulaciones laborales · Uso personal</p>
</div>
""", unsafe_allow_html=True)


# ─── Barra lateral: configuración ────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    config = load_config()

    st.markdown("**Tu nombre completo**")
    user_name = st.text_input("Nombre", value=config.get("user_name", ""), label_visibility="collapsed")

    st.markdown("**Tu correo Gmail**")
    user_email = st.text_input("Gmail", value=config.get("user_email", ""), label_visibility="collapsed")

    st.markdown("**Ruta local del CV (PDF)**")
    cv_path_input = st.text_input(
        "CV path",
        value=config.get("cv_path", str(Path.home() / "CV.pdf")),
        label_visibility="collapsed",
        placeholder="/home/usuario/MiCV.pdf",
    )

    st.markdown("**Método de redacción**")
    compose_method = st.radio(
        "Método",
        ["🤖 IA (Claude API)", "📝 Plantilla fija"],
        index=0 if config.get("compose_method", "ai") == "ai" else 1,
        label_visibility="collapsed",
    )

    if "IA" in compose_method:
        st.markdown("**Groq API Key**")
        groq_key = st.text_input(
            "API Key",
            value=config.get("groq_key", ""),
            type="password",
            label_visibility="collapsed",
            help="Obtené tu clave gratis en console.groq.com",
        )
    else:
        groq_key = ""

    st.divider()

    if st.button("💾 Guardar configuración"):
        save_config({
            "user_name": user_name,
            "user_email": user_email,
            "cv_path": cv_path_input,
            "compose_method": "ai" if "IA" in compose_method else "template",
            "groq_key": groq_key,
        })
        st.success("Configuración guardada.")

    # Estado de autenticación Gmail
    st.divider()
    st.markdown("### 🔐 Gmail API")
    token_path = Path("config/token.json")
    if token_path.exists():
        st.markdown('<span class="status-ok">✔ Autenticado</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-err">✘ Sin autenticar</span>', unsafe_allow_html=True)
        st.caption("Ejecutá `python auth_gmail.py` en la terminal para autenticarte.")

    # Verificación del CV
    cv_ok = cv_path_input and Path(cv_path_input).exists()
    st.markdown("### 📄 CV")
    if cv_ok:
        size_kb = Path(cv_path_input).stat().st_size // 1024
        st.markdown(f'<span class="status-ok">✔ Encontrado ({size_kb} KB)</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-err">✘ No encontrado</span>', unsafe_allow_html=True)


# ─── Formulario principal ────────────────────────────────────────────────────
st.markdown('<div class="section-title">01 · Datos de la vacante</div>', unsafe_allow_html=True)

# Inicializar session_state para los campos extraíbles
for key, default in [("extracted_company", ""), ("extracted_position", ""),
                     ("extracted_recruiter", ""), ("extracted_email", "")]:
    if key not in st.session_state:
        st.session_state[key] = default

job_description = st.text_area(
    "📋 Descripción de la oferta / Notas",
    placeholder="Pegá aquí el aviso completo y presioná 'Extraer datos' para completar los campos automáticamente...",
    height=150,
)

cfg_tmp = load_config()
if job_description.strip() and cfg_tmp.get("groq_key"):
    if st.button("🔍 Extraer datos del aviso"):
        with st.spinner("Analizando el aviso..."):
            extracted = extract_job_data(job_description, cfg_tmp.get("groq_key"))
            if extracted.get("company"):   st.session_state["extracted_company"]   = extracted["company"]
            if extracted.get("position"):  st.session_state["extracted_position"]  = extracted["position"]
            if extracted.get("recruiter"): st.session_state["extracted_recruiter"] = extracted["recruiter"]
            if extracted.get("email"):     st.session_state["extracted_email"]     = extracted["email"]
        st.success("✔ Datos extraídos. Revisá y corregí si es necesario.")

col1, col2 = st.columns(2)
with col1:
    company  = st.text_input("🏢 Empresa *", value=st.session_state["extracted_company"], placeholder="Ej: Mercado Libre")
    position = st.text_input("💼 Puesto *",  value=st.session_state["extracted_position"], placeholder="Ej: Backend Developer Jr.")
with col2:
    recruiter = st.text_input("👤 Nombre del reclutador", value=st.session_state["extracted_recruiter"], placeholder="Ej: María González (opcional)")
    to_email  = st.text_input("📧 Email de destino *", value=st.session_state["extracted_email"], placeholder="rrhh@empresa.com")

# Selector de género (solo visible si hay nombre de reclutador)
if recruiter.strip():
    recruiter_gender = st.radio(
        "Género del reclutador",
        ["desconocido", "femenino", "masculino"],
        format_func=lambda x: {"desconocido": "🤷 No sé / Neutro", "femenino": "👩 Femenino", "masculino": "👨 Masculino"}[x],
        horizontal=True,
        index=0,
    )
else:
    recruiter_gender = "desconocido"

# Aviso si no hay email de destino
if not to_email.strip():
    st.info("💡 Si el anuncio no tiene email, buscá el contacto en LinkedIn o en el formulario web de la empresa. Esta app solo puede enviar correos directos.")


# ─── Asunto personalizable ───────────────────────────────────────────────────
st.markdown('<div class="section-title">02 · Asunto del correo</div>', unsafe_allow_html=True)

subject_template = "Postulación para el puesto de {position} — {name}"
default_subject = subject_template.format(
    position=position or "[Puesto]",
    name=config.get("user_name", "[Tu nombre]"),
)
email_subject = st.text_input("Asunto", value=default_subject, label_visibility="collapsed")


# ─── Preview y envío ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">03 · Preview y envío</div>', unsafe_allow_html=True)

col_preview, col_send = st.columns([3, 1])

with col_preview:
    if st.button("👁️ Generar preview del correo"):
        if not company or not position or not to_email:
            st.warning("Completá al menos: empresa, puesto y email de destino.")
        else:
            with st.spinner("Analizando CV y redactando correo..."):
                cfg = load_config()

                # Extraer texto del CV para personalizar el correo
                cv_text = extract_cv_text(cfg.get("cv_path", ""))
                if cv_text:
                    st.session_state["cv_text"] = cv_text
                elif "cv_text" not in st.session_state:
                    st.session_state["cv_text"] = ""

                if "ai" in cfg.get("compose_method", "ai") and cfg.get("groq_key"):
                    body = compose_email_with_ai(
                        user_name=cfg.get("user_name", ""),
                        company=company,
                        position=position,
                        recruiter=recruiter,
                        recruiter_gender=recruiter_gender,
                        job_description=job_description,
                        cv_text=st.session_state.get("cv_text", ""),
                        api_key=cfg.get("groq_key"),
                    )
                else:
                    body = compose_email_with_template(
                        user_name=cfg.get("user_name", ""),
                        company=company,
                        position=position,
                        recruiter=recruiter,
                        recruiter_gender=recruiter_gender,
                        job_description=job_description,
                        cv_text=st.session_state.get("cv_text", ""),
                    )
                st.session_state["email_body"] = body

                if cv_text:
                    st.caption("✔ CV analizado correctamente.")
                else:
                    st.caption("⚠ No se pudo leer el CV; el correo se redactó de forma general.")
            st.success("Correo generado.")

if "email_body" in st.session_state:
    editable_body = st.text_area(
        "Cuerpo del correo (editable)",
        value=st.session_state["email_body"],
        height=300,
        label_visibility="collapsed",
    )
    st.session_state["email_body"] = editable_body



# ─── Botón de envío ─────────────────────────────────────────────────────────
st.divider()

# ─── Envío programado ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">04 · Programar envío</div>', unsafe_allow_html=True)

schedule_col1, schedule_col2 = st.columns(2)
with schedule_col1:
    send_now = st.toggle("Enviar ahora", value=True)
with schedule_col2:
    if not send_now:
        scheduled_date = st.date_input("Fecha de envío", value=datetime.now().date())
        scheduled_time = st.time_input("Hora de envío", value=datetime.now().replace(second=0, microsecond=0).time())
    else:
        scheduled_date = None
        scheduled_time = None

st.divider()

if st.button("🚀 Enviar postulación"):
    # Validaciones
    errors = []
    cfg = load_config()

    if not company:    errors.append("Falta el nombre de la empresa.")
    if not position:   errors.append("Falta el puesto.")
    if not to_email:   errors.append("Falta el email de destino.")
    if not cfg.get("user_name"):  errors.append("Falta tu nombre (Configuración).")
    if not cfg.get("user_email"): errors.append("Falta tu Gmail (Configuración).")
    if not token_path.exists():   errors.append("No estás autenticado con Gmail. Ejecutá auth_gmail.py.")
    if not cv_ok:                 errors.append(f"No se encontró el CV en: {cv_path_input}")
    if "email_body" not in st.session_state:
        errors.append("Generá el preview del correo antes de enviar.")

    if errors:
        for e in errors:
            st.error(f"⚠️ {e}")
    else:
        service = GmailService(credentials_path="config/credentials.json",
                               token_path="config/token.json")

        if send_now:
            # ── Envío inmediato ───────────────────────────────────────────
            with st.spinner("Enviando correo..."):
                try:
                    msg_id = service.send_email(
                        sender=cfg["user_email"],
                        to=to_email,
                        subject=email_subject,
                        body=st.session_state["email_body"],
                        attachment_path=cfg["cv_path"],
                    )
                    st.success(f"✅ Correo enviado exitosamente. ID: `{msg_id}`")
                    _log_sent(company, position, to_email)
                except Exception as ex:
                    st.error(f"❌ Error al enviar: {ex}")
        else:
            # ── Envío programado (Programador de tareas de Windows) ───────
            scheduled_dt = datetime.combine(scheduled_date, scheduled_time)
            now = datetime.now()

            if scheduled_dt <= now:
                st.error("⚠️ La fecha y hora programada ya pasó. Elegí un momento futuro.")
            else:
                import subprocess
                from pathlib import Path as P

                time_str = scheduled_dt.strftime("%d/%m/%Y a las %H:%M")
                app_dir  = P(__file__).parent.resolve()
                pending_path = app_dir / "config" / "pending.json"
                script_path  = app_dir / "send_scheduled.py"
                py_path      = app_dir / "venv" / "Scripts" / "python.exe"

                # 1. Guardar correo pendiente en disco
                pending_data = {
                    "to_email"  : to_email,
                    "subject"   : email_subject,
                    "body"      : st.session_state["email_body"],
                    "company"   : company,
                    "position"  : position,
                    "scheduled" : scheduled_dt.isoformat(),
                }
                pending_path.parent.mkdir(parents=True, exist_ok=True)
                with open(pending_path, "w", encoding="utf-8") as f:
                    json.dump(pending_data, f, indent=2, ensure_ascii=False)

                # 2. Registrar tarea en el Programador de Windows
                task_name  = "JobMailer_SendScheduled"
                date_str   = scheduled_dt.strftime("%Y-%m-%dT%H:%M:%S")

                # Eliminar tarea previa si existe
                subprocess.run(
                    ["schtasks", "/delete", "/tn", task_name, "/f"],
                    capture_output=True
                )

                # Crear nueva tarea
                result = subprocess.run([
                    "schtasks", "/create",
                    "/tn",  task_name,
                    "/tr",  f'"{py_path}" "{script_path}"',
                    "/sc",  "once",
                    "/st",  scheduled_dt.strftime("%H:%M"),
                    "/sd",  scheduled_dt.strftime("%m/%d/%Y"),
                    "/f",
                ], capture_output=True, text=True)

                if result.returncode != 0:
                    st.error(f"❌ No se pudo registrar la tarea: {result.stderr}")
                else:
                    # 3. Enviar recordatorio con .ics
                    try:
                        service.send_reminder(
                            sender=cfg["user_email"],
                            scheduled_time=scheduled_dt.strftime("%H:%M del %d/%m/%Y"),
                            company=company,
                            position=position,
                            scheduled_dt=scheduled_dt,
                        )
                    except Exception as ex:
                        st.warning(f"No se pudo enviar el recordatorio: {ex}")

                    _log_sent(company, position, to_email)
                    st.success(f"📅 Envío programado para el {time_str}.")
                    st.info("✅ Podés cerrar la app. Windows enviará el correo automáticamente a la hora indicada y recibirás una confirmación en tu Gmail.")

                    # Botón para cancelar
                    if st.button("🚫 Cancelar envío programado"):
                        subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], capture_output=True)
                        if pending_path.exists():
                            pending_path.unlink()
                        st.warning("🚫 Envío cancelado. La tarea fue eliminada.")



with st.expander("📋 Historial de postulaciones enviadas"):
    log_path = Path("config/sent_log.json")
    if log_path.exists():
        with open(log_path) as f:
            logs = json.load(f)
        if logs:
            for entry in logs[:20]:
                date_str = entry["date"][:10]
                st.markdown(f"- `{date_str}` · **{entry['company']}** — {entry['position']} → `{entry['to']}`")
        else:
            st.caption("Aún no enviaste ninguna postulación.")
    else:
        st.caption("Aún no enviaste ninguna postulación.")
