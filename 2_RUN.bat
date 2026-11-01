@echo off
title NewsHub - Local Server (band karne ke liye Ctrl+C)
cd /d %~dp0
call venv\Scripts\activate.bat
echo Latest news fetch ho rahi hai (1-2 minute)...
python manage.py fetch_news
echo Auto-fetch shuru ho raha hai - har 30 min me nayi news khud aati rahegi.
echo (Ek dusri chhoti window khulegi - use band mat karna, wahi dynamic fetch hai.)
start "NewsHub Auto-Fetch - band mat karna" cmd /k "call venv\Scripts\activate.bat && python manage.py fetch_loop --minutes 30"
echo.
echo ============================================
echo   Site chal gayi hai!
echo   Isi PC par:      http://127.0.0.1:8000/
echo   Admin panel:     http://127.0.0.1:8000/admin/
echo   Mobile (same WiFi): neeche wala IPv4 address
echo   apne PC ke IP ke saath: http://PC-IP:8000/
echo   Server band karne: Ctrl + C
echo ============================================
ipconfig | findstr IPv4
python manage.py runserver 0.0.0.0:8000
pause
