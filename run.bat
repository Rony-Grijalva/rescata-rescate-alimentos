@echo off
chcp 65001 >nul
title RESCATA - servidor
cd /d "%~dp0"
where py >nul 2>nul && (py -3 backend\server.py & goto :fin)
where python >nul 2>nul && (python backend\server.py & goto :fin)
echo No se encontro Python 3. Instalalo desde https://www.python.org/downloads/ (marca "Add python.exe to PATH") y vuelve a abrir este archivo.
pause
:fin
