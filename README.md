# 📨 Job Mailer

Automatizador de postulaciones laborales: redacta, adjunta el CV y envía (o programa) el correo de postulación desde tu propia cuenta de Gmail, sin depender de servidores externos. Nació de la necesidad de dejar de repetir manualmente el mismo proceso —redactar, adjuntar CV, enviar— cada vez que aplicaba a un puesto.

## Stack

- **Python 3** + **Streamlit** (interfaz web local)
- **Gmail API** (OAuth 2.0) para el envío de correos
- **Groq (Llama 3)** para la redacción automática del cuerpo del correo, personalizada según el CV y el aviso
- **Programador de tareas de Windows** para los envíos programados

## Instalación y uso

```bash
git clone https://github.com/FranRivelli/job-mailer.git
cd job-mailer
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

1. Creá un proyecto en [Google Cloud Console](https://console.cloud.google.com), habilitá la **Gmail API** y generá credenciales OAuth de tipo "Aplicación de escritorio". Descargá el JSON como `config/credentials.json`.
2. Autenticate una sola vez:
   ```bash
   python auth_gmail.py
   ```
3. (Opcional) Conseguí una API key gratis en [console.groq.com](https://console.groq.com) para habilitar la redacción con IA.
4. Corré la app:
   ```bash
   streamlit run app.py
   ```
   Completá tus datos en la barra lateral y ya podés generar y enviar postulaciones.

> Guía detallada paso a paso en [GUIA.md](GUIA.md).

## Capturas de pantalla

<img width="1889" height="912" alt="image" src="https://github.com/user-attachments/assets/b7457b45-18c7-4965-9acc-be6bb9e658ed" />
<img width="1107" height="656" alt="image" src="https://github.com/user-attachments/assets/64d11d7b-1ef8-4b7a-abbe-a9f49b92f0e2" />

<!-- Pegá acá tus capturas: formulario, preview del correo, envío programado, etc. -->

## Qué aprendí / qué le falta

Aprendí a integrar OAuth 2.0 de extremo a extremo (en vez de usar contraseñas de aplicación), a manejar tareas programadas del sistema operativo desde Python, y a diseñar prompts que devuelven contenido consistente y sin frases genéricas.

Falta: persistir el historial en algo más robusto que un JSON local, agregar tests automatizados, y un dashboard de seguimiento del estado de cada postulación (enviada / respondida / rechazada).
