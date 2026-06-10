# WC 2026 Agent — PowerShell Scheduler Setup
# Run in PowerShell as Administrator:
# Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
# .\scripts\setup_scheduler.ps1

param(
    [string]$ProjectDir = "$env:USERPROFILE\Documents\l",
    [string]$Python = "python"
)

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " WC 2026 Agent - PowerShell Scheduler Setup" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project: $ProjectDir"

# Verify project exists
if (-not (Test-Path "$ProjectDir\.env")) {
    Write-Host "ERROR: .env not found in $ProjectDir" -ForegroundColor Red
    Write-Host "Create .env with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
    exit 1
}

# ── Morning Analysis — every day at 08:00 ────────────────────────────────────
$morningAction = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c cd /d `"$ProjectDir`" && $Python agent\wc_agent.py morning >> logs\scheduler.log 2>&1" `
    -WorkingDirectory $ProjectDir

$morningTrigger = New-ScheduledTaskTrigger -Daily -At "08:00"

Register-ScheduledTask `
    -TaskName "WC2026_Morning_Analysis" `
    -Action $morningAction `
    -Trigger $morningTrigger `
    -Description "WC 2026 Morning Analysis — runs daily at 08:00" `
    -RunLevel Highest `
    -Force

Write-Host "[OK] WC2026_Morning_Analysis — daily 08:00" -ForegroundColor Green

# ── Scheduler (all cycles auto-timed) — runs at logon ────────────────────────
$schedulerAction = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c cd /d `"$ProjectDir`" && $Python agent\scheduler.py --matchday agent\matchday.json >> logs\scheduler.log 2>&1" `
    -WorkingDirectory $ProjectDir

$schedulerTrigger = New-ScheduledTaskTrigger -AtLogOn

Register-ScheduledTask `
    -TaskName "WC2026_Scheduler" `
    -Action $schedulerAction `
    -Trigger $schedulerTrigger `
    -Description "WC 2026 Full Scheduler — starts at Windows logon" `
    -RunLevel Highest `
    -Force

Write-Host "[OK] WC2026_Scheduler — starts at logon" -ForegroundColor Green

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " Tasks created:" -ForegroundColor Cyan
Write-Host "  WC2026_Morning_Analysis  -> daily 08:00" -ForegroundColor White
Write-Host "  WC2026_Scheduler         -> at Windows logon" -ForegroundColor White
Write-Host ""
Write-Host " Commands:" -ForegroundColor Cyan
Write-Host "  See tasks:   Get-ScheduledTask -TaskName 'WC2026*'" -ForegroundColor White
Write-Host "  Run now:     Start-ScheduledTask 'WC2026_Morning_Analysis'" -ForegroundColor White
Write-Host "  Delete:      Unregister-ScheduledTask -TaskName 'WC2026_Morning_Analysis'" -ForegroundColor White
Write-Host "===========================================" -ForegroundColor Cyan
