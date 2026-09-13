"""
auth_gmail.py
─────────────
Script de autenticación OAuth 2.0 con Gmail.
Solo necesitás ejecutarlo UNA VEZ (o cuando el token expire sin refresh token).

Uso:
    python auth_gmail.py

Qué hace:
  1. Lee config/credentials.json (descargado de Google Cloud Console).
  2. Abre el navegador para que autorices el acceso a tu cuenta Gmail.
  3. Guarda el token en config/token.json para que la app lo use sin pedir
     autorización cada vez.

IMPORTANTE: config/credentials.json y config/token.json son PRIVADOS.
  → Agregalos al .gitignore si usás git.
  → Nunca los compartas ni subas a repositorios públicos.
"""

from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDENTIALS_PATH = Path("config/credentials.json")
TOKEN_PATH = Path("config/token.json")


def main():
    print("=" * 55)
    print("  Job Mailer — Autenticación con Gmail API")
    print("=" * 55)

    # Verificar que credentials.json existe
    if not CREDENTIALS_PATH.exists():
        print(f"\n❌  No se encontró: {CREDENTIALS_PATH}")
        print("\nPasos para obtenerlo:")
        print("  1. Ingresá a https://console.cloud.google.com")
        print("  2. Creá un proyecto → APIs → Gmail API → Habilitar")
        print("  3. Credenciales → OAuth 2.0 → Aplicación de escritorio")
        print("  4. Descargá el JSON y guardalo como config/credentials.json")
        return

    print("\n✔  credentials.json encontrado.")
    print("   Se abrirá el navegador para que autorices el acceso...")
    print("   (Elegí tu cuenta Gmail personal y aceptá el permiso de envío)\n")

    # Iniciar flujo OAuth — abre el navegador automáticamente
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_PATH), SCOPES
    )
    creds: Credentials = flow.run_local_server(
        port=0,  # puerto libre automático
        prompt="consent",           # forzar pantalla de consentimiento
        access_type="offline",      # obtener refresh_token para renovación automática
    )

    # Guardar token
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    print(f"\n✅  Token guardado en: {TOKEN_PATH}")
    print("   Ya podés usar la app sin volver a autenticarte.")
    print("   El token se renueva automáticamente cuando expire.\n")


if __name__ == "__main__":
    main()
