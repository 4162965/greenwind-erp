@echo off
chcp 65001 >nul
title 绿风管理软件启动器
echo 正在启动绿风管理软件，请稍候...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-all.ps1"
if errorlevel 1 (
  echo.
  echo 启动失败，请把 logs 文件夹中的日志发给开发人员。
  pause
)
