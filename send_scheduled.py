"""
send_scheduled.py
─────────────────
Script liviano ejecutado automáticamente por el Programador de tareas de Windows
a la hora indicada. Lee config/pending.json, envía el correo y limpia el archivo.

NO es necesario que la app esté abierta para que esto funcione.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Asegurarse de que el script corra desde su propia carpeta
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from gmail_service import GmailService
from config_manager import load_config

PENDING_PATH = script_dir / "config" / "pending.json"
LOG_PATH     = script_dir / "config" / "scheduler_log.txt"


def log(msg: str):
    """Escribe en el log con timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")


def main():
    log("send_scheduled.py iniciado.")

    if not PENDING_PATH.exists():
        log("No hay correo pendiente. Saliendo.")
        return

    # Leer correo pendiente
    with open(PENDING_PATH, encoding="utf-8") as f:
        pending = json.load(f)

    log(f"Correo pendiente encontrado: {pending.get('company')} — {pending.get('position')}")

    cfg = load_config()

    try:
        service = GmailService(
            credentials_path=str(script_dir / "config" / "credentials.json"),
            token_path=str(script_dir / "config" / "token.json"),
        )

        msg_id = service.send_email(
            sender=cfg["user_email"],
            to=pending["to_email"],
            subject=pending["subject"],
            body=pending["body"],
            attachment_path=cfg["cv_path"],
        )
        log(f"✅ Correo enviado exitosamente. ID: {msg_id}")

        # Notificar al usuario que el correo fue enviado
        service.send_confirmation(
            sender=cfg["user_email"],
            company=pending["company"],
            position=pending["position"],
            to_email=pending["to_email"],
        )
        log("✅ Confirmación enviada al usuario.")

    except Exception as e:
        log(f"❌ Error al enviar: {e}")
        return

    # Limpiar el archivo pendiente
    PENDING_PATH.unlink()
    log("Archivo pending.json eliminado. Tarea completada.")


if __name__ == "__main__":
    main()
