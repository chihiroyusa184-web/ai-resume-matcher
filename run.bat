@echo off
cd /d "%~dp0"
start "" http://localhost:8501
C:\Users\16720\AppData\Local\Programs\Python\Python313\Scripts\streamlit.exe run app.py
pause
