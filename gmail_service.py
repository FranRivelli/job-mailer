"""
gmail_service.py
────────────────
Encapsula toda la lógica de autenticación y envío con la Gmail API v1.
Usa OAuth 2.0 con token guardado localmente (no se necesita contraseña
de aplicación ni SMTP; el token se renueva automáticamente).
"""

import base64
from datetime import datetime
import mimetypes
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Scopes mínimos necesarios: solo envío de correo
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GmailService:
    """
    Wrapper sobre la Gmail API.

    Parámetros
    ----------
    credentials_path : str
        Ruta al archivo credentials.json descargado de Google Cloud Console.
    token_path : str
        Ruta donde se guarda (y renueva) el token OAuth después del primer login.
    """

    def __init__(self, credentials_path: str = "config/credentials.json",
                 token_path: str = "config/token.json"):
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.service = self._build_service()

    # ── Autenticación ────────────────────────────────────────────────────────
    def _build_service(self):
        """Carga credenciales y construye el servicio de la Gmail API."""
        creds = None

        # Si ya existe un token guardado, lo cargamos
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        # Si el token expiró o no existe, lo refrescamos
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_token(creds)

        if not creds or not creds.valid:
            raise RuntimeError(
                "No hay credenciales válidas. "
                "Ejecutá 'python auth_gmail.py' para autenticarte."
            )

        return build("gmail", "v1", credentials=creds)

    def _save_token(self, creds: Credentials):
        """Persiste el token actualizado en disco."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w") as f:
            f.write(creds.to_json())

    # ── Construcción del mensaje ─────────────────────────────────────────────
    @staticmethod
    def _text_to_html(text: str) -> str:
        """
        Convierte texto plano a HTML preservando párrafos.
        Cada línea en blanco separa párrafos; los saltos simples se unen.
        Así el cliente de correo renderiza el texto fluido sin cortes.
        """
        import html as html_lib
        paragraphs = text.split("\n\n")
        html_parts = []
        for para in paragraphs:
            # Escapar caracteres especiales
            escaped = html_lib.escape(para.strip())
            # Unir líneas del mismo párrafo con espacio (evita cortes forzados)
            lines = [l.strip() for l in escaped.splitlines() if l.strip()]
            html_parts.append("<p>" + " ".join(lines) + "</p>")
        return f"""<html><body style="font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:#222;">
{"".join(html_parts)}
</body></html>"""

    def _build_message(self, sender: str, to: str, subject: str,
                       body: str, attachment_path: str | None = None) -> dict:
        """
        Construye el mensaje MIME con texto HTML y adjunto opcional.
        Retorna el dict listo para la API { 'raw': '...' }.
        """
        if attachment_path:
            # Con adjunto: usar MIMEMultipart
            msg = MIMEMultipart("mixed")
            msg["From"]    = sender
            msg["To"]      = to
            msg["Subject"] = subject

            # Parte HTML del cuerpo
            html_body = self._text_to_html(body)
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            # Adjunto
            path = Path(attachment_path)
            if not path.exists():
                raise FileNotFoundError(f"CV no encontrado en: {attachment_path}")

            with open(path, "rb") as f:
                file_data = f.read()

            part = MIMEBase("application", "octet-stream")
            part.set_payload(file_data)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{path.name}"')
            msg.attach(part)

        else:
            # Sin adjunto: mensaje simple HTML
            msg = MIMEMultipart("alternative")
            msg["From"]    = sender
            msg["To"]      = to
            msg["Subject"] = subject
            html_body = self._text_to_html(body)
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Codificar en base64 URL-safe (requerido por la API)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        return {"raw": raw}

    # ── Envío ────────────────────────────────────────────────────────────────
    def send_email(self, sender: str, to: str, subject: str,
                   body: str, attachment_path: str | None = None) -> str:
        """
        Envía el correo y retorna el message_id asignado por Gmail.

        Parámetros
        ----------
        sender          : Tu dirección Gmail (debe coincidir con la cuenta autenticada).
        to              : Correo de destino.
        subject         : Asunto.
        body            : Cuerpo en texto plano.
        attachment_path : Ruta local al PDF del CV (opcional, pero recomendado).

        Retorna
        -------
        str : ID del mensaje enviado.
        """
        try:
            message_dict = self._build_message(sender, to, subject, body, attachment_path)
            result = (
                self.service.users()
                    .messages()
                    .send(userId="me", body=message_dict)
                    .execute()
            )
            return result.get("id", "—")
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}") from e

    @staticmethod
    def _build_ics(scheduled_dt, company: str, position: str) -> str:
        """
        Genera el contenido de un archivo .ics con el evento del envío programado.
        Incluye una alarma 30 minutos antes.
        """
        from datetime import timezone, timedelta
        import uuid

        # Convertir a UTC para el .ics
        dt_utc = scheduled_dt.astimezone(timezone.utc)
        dt_end = dt_utc + timedelta(minutes=30)

        fmt = "%Y%m%dT%H%M%SZ"
        now_utc = datetime.utcnow().strftime(fmt)

        return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Job Mailer//ES
BEGIN:VEVENT
UID:{uuid.uuid4()}@jobmailer
DTSTAMP:{now_utc}
DTSTART:{dt_utc.strftime(fmt)}
DTEND:{dt_end.strftime(fmt)}
SUMMARY:📨 Envío postulación: {position} en {company}
DESCRIPTION:Job Mailer enviará tu correo de postulación automáticamente.\nMantené la app abierta.\n\nEmpresa: {company}\nPuesto: {position}
BEGIN:VALARM
TRIGGER:-PT30M
ACTION:DISPLAY
DESCRIPTION:⚠️ En 30 minutos se envía tu postulación a {company}. ¡Mantené la app abierta!
END:VALARM
END:VEVENT
END:VCALENDAR"""

    def send_reminder(self, sender: str, scheduled_time: str,
                      company: str, position: str,
                      scheduled_dt=None) -> str:
        """
        Envía un recordatorio con evento .ics adjunto para agendar en Google Calendar.
        Incluye alarma 30 minutos antes del envío programado.
        """
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders

        subject = f"⏰ Recordatorio: envío programado para {scheduled_time}"

        html_body = f"""<html><body style="font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:#222;">
<p>Hola,</p>
<p>Este es un recordatorio automático de <strong>Job Mailer</strong>.</p>
<p>Tenés un correo de postulación programado para enviarse el <strong>{scheduled_time}</strong>.</p>
<table style="border-collapse:collapse;margin:12px 0;">
  <tr><td style="padding:4px 16px 4px 0;color:#64748b;">Empresa</td><td><strong>{company}</strong></td></tr>
  <tr><td style="padding:4px 16px 4px 0;color:#64748b;">Puesto</td><td><strong>{position}</strong></td></tr>
</table>
<p style="background:#dcfce7;border-left:4px solid #16a34a;padding:10px 14px;border-radius:4px;">
  ✅ <strong>Podés cerrar la app.</strong> Windows enviará el correo automáticamente a la hora indicada.<br>
  Solo asegurate de que la PC esté encendida a esa hora.
</p>
<p style="color:#64748b;font-size:12px;">— Job Mailer</p>
</body></html>"""

        # Construir mensaje multipart/mixed con .ics adjunto
        msg = MIMEMultipart("mixed")
        msg["From"]    = sender
        msg["To"]      = sender
        msg["Subject"] = subject

        # Parte HTML
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Adjuntar el .ics
        if scheduled_dt:
            ics_content = self._build_ics(scheduled_dt, company, position)
            # El .ics debe ir como text/calendar SIN encode_base64 para que Gmail lo reconozca
            ics_part = MIMEText(ics_content, "calendar", "utf-8")
            ics_part.add_header("Content-Disposition", 'attachment; filename="postulacion.ics"')
            msg.attach(ics_part)

        try:
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            result = (
                self.service.users()
                    .messages()
                    .send(userId="me", body={"raw": raw})
                    .execute()
            )
            return result.get("id", "—")
        except HttpError as e:
            raise RuntimeError(f"Error al enviar recordatorio: {e}") from e

    def send_confirmation(self, sender: str, company: str,
                          position: str, to_email: str) -> str:
        """
        Envía una notificación al usuario confirmando que el correo
        programado fue enviado exitosamente.
        """
        subject = f"✅ Postulación enviada: {position} en {company}"
        html_body = f"""<html><body style="font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:#222;">
<p>Hola,</p>
<p>Tu correo de postulación fue enviado exitosamente por <strong>Job Mailer</strong>.</p>
<table style="border-collapse:collapse;margin:12px 0;">
  <tr><td style="padding:4px 16px 4px 0;color:#64748b;">Empresa</td><td><strong>{company}</strong></td></tr>
  <tr><td style="padding:4px 16px 4px 0;color:#64748b;">Puesto</td><td><strong>{position}</strong></td></tr>
  <tr><td style="padding:4px 16px 4px 0;color:#64748b;">Enviado a</td><td><strong>{to_email}</strong></td></tr>
</table>
<p style="background:#dcfce7;border-left:4px solid #16a34a;padding:10px 14px;border-radius:4px;">
  ✅ El correo fue entregado correctamente. ¡Mucha suerte!
</p>
<p style="color:#64748b;font-size:12px;">— Job Mailer</p>
</body></html>"""

        try:
            message_dict = self._build_message(sender, sender, subject, html_body)
            result = (
                self.service.users()
                    .messages()
                    .send(userId="me", body=message_dict)
                    .execute()
            )
            return result.get("id", "—")
        except HttpError as e:
            raise RuntimeError(f"Error al enviar confirmación: {e}") from e

