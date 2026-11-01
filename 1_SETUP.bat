@echo off
title NewsHub - One Time Setup
cd /d %~dp0
echo ============================================
echo   NewsHub Setup (sirf pehli baar chalana hai)
echo ============================================
python --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python nahi mila. Pehle python.org se Python 3.12 install karo
  echo aur install ke time "Add python.exe to PATH" tick karna mat bhoolna.
  pause
  exit /b 1
)
if not exist venv (
  echo Virtual environment ban raha hai...
  python -m venv venv
)
call venv\Scripts\activate.bat
echo Libraries install ho rahi hain, 2-3 minute lagenge...
pip install -r requirements.txt
if not exist .env (
  copy .env.pgadmin.example .env >nul
  echo.
  echo ============================================
  echo   ABHI .env file khulegi. Usme YOUR_PASSWORD
  echo   ki jagah apna pgAdmin/PostgreSQL password
  echo   likho, file SAVE karo, phir band karo.
  echo ============================================
  pause
  notepad .env
)
echo Database tables ban rahe hain (pgAdmin wala newshub database)...
python manage.py migrate
python manage.py seed_sources
echo.
echo ============================================
echo   Setup ho gaya! Ab apna admin account banao:
echo   neeche username, email, password dalo.
echo ============================================
python manage.py createsuperuser
echo.
echo Sab ready hai. Ab 2_RUN.bat chalao site start karne ke liye.
pause
