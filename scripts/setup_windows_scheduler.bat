@echo off
:: WC 2026 Agent — Windows Task Scheduler Setup
:: Run this script ONCE as Administrator to set up all automated tasks
:: Usage: Right-click -> "Run as Administrator"

echo ==========================================
echo  WC 2026 Agent - Windows Scheduler Setup
echo ==========================================
echo.

:: Set project path - change this to your actual path
set PROJECT_DIR=%USERPROFILE%\Documents\l
set PYTHON=python

:: Check if .env exists
if not exist "%PROJECT_DIR%\.env" (
    echo ERROR: .env file not found in %PROJECT_DIR%
    echo Create .env with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID first.
    pause
    exit /b 1
)

echo Project directory: %PROJECT_DIR%
echo.

:: ── TASK 1: Morning Analysis (08:00 daily) ────────────────────────────────
echo Creating TASK 1: Morning Analysis at 08:00...
schtasks /create /tn "WC2026_Morning_Analysis" ^
  /tr "cmd /c cd /d \"%PROJECT_DIR%\" && %PYTHON% agent\wc_agent.py morning >> logs\scheduler.log 2>&1" ^
  /sc daily /st 08:00 ^
  /ru "%USERNAME%" ^
  /f
echo   Done.

:: ── TASK 2: Test Telegram connection ──────────────────────────────────────
echo Creating TASK 2: Telegram test at startup...
schtasks /create /tn "WC2026_Telegram_Test" ^
  /tr "cmd /c cd /d \"%PROJECT_DIR%\" && %PYTHON% agent\telegram_bot.py --test >> logs\scheduler.log 2>&1" ^
  /sc onstart ^
  /ru "%USERNAME%" ^
  /f
echo   Done.

echo.
echo ==========================================
echo  Setup complete! Tasks created:
echo  - WC2026_Morning_Analysis  (daily 08:00)
echo  - WC2026_Telegram_Test     (on startup)
echo.
echo  To see tasks: schtasks /query /tn "WC2026*"
echo  To delete:    schtasks /delete /tn "WC2026_Morning_Analysis" /f
echo ==========================================
pause
