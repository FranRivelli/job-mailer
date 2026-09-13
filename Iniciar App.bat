@echo off
cd /d "%~dp0"
call venv\Scripts\activate
py -m streamlit run app.py
pause
