@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "VIRTUAL_ENV=%~dp0env"
set "PATH=%VIRTUAL_ENV%;%VIRTUAL_ENV%\Scripts;%PATH%"
set "PROMPT=(cnAgentos) %PROMPT%"
echo.
echo [cnAgentos] 虚拟环境已激活（便携式，路径相对项目目录）
echo   Python: %VIRTUAL_ENV%python.exe
echo   启动项目: python app.py
echo   退出环境: deactivate
echo.
cmd /k
