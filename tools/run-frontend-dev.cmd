@echo off
setlocal
set "ROOT=%~dp0.."
set "NPM=C:\Program Files\nodejs\npm.cmd"
cd /d "%ROOT%\frontend"
if not exist "%NPM%" set "NPM=npm.cmd"
call "%NPM%" run dev -- --host 0.0.0.0
pause
