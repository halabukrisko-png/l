@echo off
:: WC 2026 Agent — Daily runner
:: This script runs automatically via Windows Task Scheduler
:: Can also be run manually: double-click run_daily.bat

cd /d "%~dp0.."
set PYTHON=python
set LOGFILE=logs\scheduler.log

echo [%date% %time%] === WC 2026 DAILY ROUTINE START === >> %LOGFILE%

:: 1. Test Telegram
echo [%date% %time%] Testing Telegram... >> %LOGFILE%
%PYTHON% agent\telegram_bot.py --test >> %LOGFILE% 2>&1

:: 2. Morning Analysis
echo [%date% %time%] Running Morning Analysis... >> %LOGFILE%
%PYTHON% agent\wc_agent.py morning >> %LOGFILE% 2>&1

echo [%date% %time%] === DONE === >> %LOGFILE%
