"""
config_manager.py
─────────────────
Lee y escribe la configuración del usuario en config/settings.json.
Las credenciales sensibles (API key) se guardan solo en ese archivo local,
que debe estar en .gitignore si usás control de versiones.
"""

import json
from pathlib import Path

CONFIG_PATH = Path("config/settings.json")

DEFAULTS = {
    "user_name": "",
    "user_email": "",
    "cv_path": str(Path.home() / "CV.pdf"),
    "compose_method": "ai",
    "anthropic_key": "",
}


def load_config() -> dict:
    """Carga la configuración desde disco. Retorna defaults si no existe."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # Completar con defaults para claves faltantes
        return {**DEFAULTS, **data}
    return DEFAULTS.copy()


def save_config(config: dict) -> None:
    """Persiste la configuración en disco."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
