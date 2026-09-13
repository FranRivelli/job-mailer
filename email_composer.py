"""
email_composer.py
─────────────────
Dos estrategias de redacción del cuerpo del correo:

  1. compose_email_with_ai()       → llama a Groq (Llama 3, gratis)
  2. compose_email_with_template() → plantilla fija, sin APIs externas
"""

from groq import Groq
import pdfplumber
from pathlib import Path


# ── Extracción de texto del CV ────────────────────────────────────────────────

def extract_cv_text(cv_path: str) -> str:
    """Extrae el texto del CV en PDF. Retorna cadena vacía si falla."""
    try:
        path = Path(cv_path)
        if not path.exists():
            return ""
        with pdfplumber.open(str(path)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages).strip()[:3000]
    except Exception:
        return ""


# ── Estrategia 1: IA (Groq / Llama 3) ───────────────────────────────────────

def compose_email_with_ai(
    user_name: str,
    company: str,
    position: str,
    recruiter: str = "",
    recruiter_gender: str = "desconocido",
    job_description: str = "",
    cv_text: str = "",
    api_key: str = "",
) -> str:
    """Usa Groq + Llama 3 para redactar un correo personalizado basado en el CV."""

    # ── Salutación ────────────────────────────────────────────────────────────
    if recruiter:
        if recruiter_gender == "femenino":
            salutation = f"Estimada {recruiter},"
        elif recruiter_gender == "masculino":
            salutation = f"Estimado {recruiter},"
        else:
            salutation = f"Estimado/a {recruiter},"
    else:
        salutation = "Estimado/a equipo de Recursos Humanos,"

    # ── Sección del CV ────────────────────────────────────────────────────────
    cv_section = f"""
Currículum Vitae del candidato (usalo para personalizar el correo con datos reales):
---
{cv_text}
---""" if cv_text else "\n(No se proporcionó CV; redactá de forma general.)"

    prompt = f"""Eres un experto en redacción de correos de postulación laboral en español rioplatense.
Tu tarea tiene DOS pasos internos antes de escribir:

PASO 1 — ANÁLISIS (no lo escribas, solo pensalo):
- Leé el aviso y extraé las 2 o 3 habilidades o requisitos MÁS importantes que pide el puesto.
- Leé el CV y encontrá la experiencia o habilidad que mejor matchea con ESOS requisitos específicos.
- Elegí UNA sola cosa del CV para mencionar — la más relevante para ESE puesto puntual, no la más genérica.

PASO 2 — REDACCIÓN:
{cv_section}

Vacante:
- Empresa: {company}
- Puesto: {position}
- Aviso (solo contexto interno, NO lo copies): {job_description or "Sin detalles."}

Primera línea: salutación con solo el primer nombre normalizado (ej: "Estimada María," no "Estimada GARCIA MARIA,"). Base: {salutation}

Estructura:
1. PRESENTACIÓN: "Mi nombre es {user_name} y me dirijo a usted para postularme al puesto de [puesto] en [empresa]."
2. VALOR: 1 párrafo de 2 oraciones máximo. Mencioná la habilidad o experiencia del CV que más aplica a LOS REQUISITOS ESPECÍFICOS de este puesto. Que sea diferente para cada puesto.
3. CIERRE: una oración ofreciendo una entrevista para demostrar tu aporte.

Prohibido usar:
- "me apasiona", "soy proactivo", "considero esencial", "considero relevante", "aprender más sobre el puesto", "equipo que valora"
- Frases genéricas que sirvan para cualquier puesto
- "abordar con confianza las responsabilidades del puesto", "base sólida para", "me permite abordar", "me permite entender la importancia", "tarea clave en el puesto", "comprender los procesos de", "creo que se ajusta a los requisitos", "se ajusta a los requisitos del puesto", "que se ajusta a"
- No describas las tareas del puesto como si las estuvieras explicando al reclutador — él ya las conoce.
- Copiar textualmente frases del CV o del aviso

Terminar con: "Saludos cordiales,\n{user_name}"
- Ortografía: usá "e" en lugar de "y" cuando la palabra siguiente empieza con "i" o "hi" (ej: "datos e informes", "padre e hijo").
Solo el cuerpo. Sin encabezados ni aclaraciones.

Correo:"""

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# ── Estrategia 2: Plantilla fija ─────────────────────────────────────────────

def compose_email_with_template(
    user_name: str,
    company: str,
    position: str,
    recruiter: str = "",
    recruiter_gender: str = "desconocido",
    job_description: str = "",
    cv_text: str = "",
) -> str:
    """Plantilla estática sin IA."""
    if recruiter:
        if recruiter_gender == "femenino":
            salutation = f"Estimada {recruiter},"
        elif recruiter_gender == "masculino":
            salutation = f"Estimado {recruiter},"
        else:
            salutation = f"Estimado/a {recruiter},"
    else:
        salutation = "Estimado/a equipo de Recursos Humanos,"

    return f"""{salutation}

Mi nombre es {user_name} y me dirijo a usted para expresar mi interés en la posición de \
{position} en {company}. Adjunto a este correo mi Currículum Vitae actualizado para su consideración.

Cuento con formación y experiencia relevante para este puesto, y me entusiasma la posibilidad de \
contribuir al equipo de {company}. Estoy completamente disponible para una entrevista o conversación \
en el horario que mejor le convenga.

Quedo a disposición ante cualquier consulta. Muchas gracias por su tiempo y consideración.

Saludos cordiales,
{user_name}"""


# ── Extracción de datos del aviso ─────────────────────────────────────────────

def extract_job_data(job_description: str, api_key: str) -> dict:
    """
    Usa Groq para extraer campos clave del texto de un aviso laboral.
    Retorna un dict con: company, position, recruiter, email.
    """
    prompt = f"""Analizá el siguiente aviso laboral y extraé estos datos en formato JSON:
- "company": nombre de la empresa (string, vacío si no se encuentra)
- "position": nombre del puesto ofrecido (string, vacío si no se encuentra)
- "recruiter": nombre del responsable de RRHH o reclutador (string, vacío si no se encuentra)
- "email": email de contacto (string, vacío si no se encuentra)

Reglas:
- Respondé SOLO con el JSON, sin explicaciones ni markdown.
- Si un dato no está en el aviso, dejá el campo como string vacío "".
- No inventes datos que no estén explícitamente en el texto.

Aviso:
---
{job_description[:3000]}
---

JSON:"""

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0,
    )

    import json
    try:
        text = response.choices[0].message.content.strip()
        # Limpiar posibles backticks
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return {"company": "", "position": "", "recruiter": "", "email": ""}
