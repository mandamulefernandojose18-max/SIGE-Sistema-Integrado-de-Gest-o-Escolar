@echo off
title SIGE - Sistema Integrado de Gestao Escolar
echo =====================================================================
echo           SIGE - INICIANDO SISTEMA COMPLETO LOCALMENTE
echo =====================================================================
echo.

cd /d "%~dp0"

echo [*] Iniciando Backend Django (Waitress WSGI na porta 8000)...
start "SIGE Backend (Porta 8000)" cmd /k "cd backend && venv\Scripts\python.exe run_production.py"

ping -n 3 127.0.0.1 >nul

echo [*] Iniciando Frontend SPA (Node.js na porta 5173)...
start "SIGE Frontend (Porta 5173)" cmd /k "cd frontend && node server.js"

echo.
echo =====================================================================
echo [OK] SIGE inicializado com sucesso!
echo      Frontend: http://localhost:5173
echo      Backend:  http://localhost:8000
echo =====================================================================
echo.
ping -n 3 127.0.0.1 >nul
start http://localhost:5173
