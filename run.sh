#!/bin/bash
# WC 2026 Analysis Agent — Quick launcher
# Run from project root: bash run.sh [command]

set -e
cd "$(dirname "$0")"

PYTHON=python3

print_help() {
cat << 'EOF'
⚽ WC 2026 Analysis Agent

USAGE:
  bash run.sh morning                          → CYCLE 1: Morning analysis (all matches)
  bash run.sh prematch TEAM1 TEAM2 HH:MM CET  → CYCLE 2: Pre-match refresh
  bash run.sh lastminute TEAM1 TEAM2 HH:MM    → CYCLE 3: Last minute tip
  bash run.sh lineup TEAM1 TEAM2 HH:MM        → TYPE B: Lineup confirmed notification
  bash run.sh postmatch TEAM1 TEAM2 SCORE     → TYPE D: Post-match report
  bash run.sh scheduler                        → Start automatic scheduler (all cycles)
  bash run.sh test                             → Test mode (run all cycles immediately)
  bash run.sh api matches                      → Fetch today's matches from API
  bash run.sh api match TEAM1 TEAM2           → Fetch full match data from all APIs
  bash run.sh logs                             → Show latest agent output

EXAMPLES:
  bash run.sh morning
  bash run.sh prematch Mexico "South Africa" 15:00 "22:00 CEST"
  bash run.sh lastminute Mexico "South Africa" 15:00
  bash run.sh lineup Mexico "South Africa" 15:00
  bash run.sh postmatch Mexico "South Africa" "2:0"
  bash run.sh scheduler --matchday agent/matchday.json
  bash run.sh telegram                           → Test Telegram bot connection

EOF
}

case "${1:-help}" in
  morning)
    echo "🌅 Starting CYCLE 1 — Morning Analysis..."
    $PYTHON agent/wc_agent.py morning
    ;;
  prematch)
    echo "⚡ Starting CYCLE 2 — Pre-Match Refresh: $2 vs $3 @ $4..."
    $PYTHON agent/wc_agent.py prematch "$2" "$3" "$4" "${5:-}"
    ;;
  lastminute)
    echo "🔴 Starting CYCLE 3 — Last Minute Tip: $2 vs $3 @ $4..."
    $PYTHON agent/wc_agent.py lastminute "$2" "$3" "$4"
    ;;
  lineup)
    echo "📋 Sending TYPE B — Lineup Confirmed: $2 vs $3..."
    $PYTHON agent/wc_agent.py lineup "$2" "$3" "$4"
    ;;
  postmatch)
    echo "🏁 Sending TYPE D — Post-Match Report: $2 vs $3 ($4)..."
    $PYTHON agent/wc_agent.py postmatch "$2" "$3" "$4"
    ;;
  scheduler)
    echo "🕐 Starting Automatic Scheduler..."
    shift
    $PYTHON agent/scheduler.py "$@"
    ;;
  test)
    echo "🧪 Running in TEST MODE..."
    $PYTHON agent/scheduler.py --test
    ;;
  api)
    shift
    $PYTHON scripts/api/rapidapi.py "$@"
    ;;
  telegram)
    echo "📱 Testing Telegram connection..."
    $PYTHON agent/telegram_bot.py --test
    ;;
  logs)
    echo "📋 Latest agent outputs:"
    ls -lt logs/*.md 2>/dev/null | head -10 || echo "No logs yet."
    if [ -f logs/agent.log ]; then
      echo ""
      echo "--- Last 20 log lines ---"
      tail -20 logs/agent.log
    fi
    ;;
  help|--help|-h)
    print_help
    ;;
  *)
    echo "Unknown command: $1"
    print_help
    exit 1
    ;;
esac
