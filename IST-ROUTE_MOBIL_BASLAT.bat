@echo off
title Ist-Route Mobil Baslatiliyor...
echo Ist-Route MOBIL arayuzu baslatiliyor...
echo Tarayici birkac saniye icinde http://localhost:8501/?view=mobile adresini acacak.
echo Telefonda acmak icin: ayni Wi-Fi'da http://BILGISAYAR-IP:8501/?view=mobile
cd /d "%~dp0"
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
start "" cmd /c "timeout /t 6 /nobreak >nul & start http://localhost:8501/?view=mobile"
"%PY%" -m streamlit run app.py --server.headless=true --server.port=8501 --browser.gatherUsageStats=false
pause
