#!/usr/bin/env python3
"""
WC 2026 Analysis Agent — Automatic Scheduler
Runs all 3 cycles + 4 notification types at the correct times.

Usage:
  python3 scheduler.py                    # Start scheduler with today's matches
  python3 scheduler.py --matchday FILE    # Load match schedule from JSON file
  python3 scheduler.py --test             # Test mode (runs cycles immediately)
"""

import json
import sys
import time
import signal
import threading
from datetime import datetime, timedelta
from pathlib import Path
import schedule

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "agent"))
from wc_agent import (
    log, cycle1_morning, cycle2_prematch, cycle3_lastminute,
    notify_lineup_confirmed, notify_postmatch
)

# ── Match schedule ─────────────────────────────────────────────────────────────
# Each entry defines a match and when each cycle fires.
# Times are in LOCAL stadium time.
# Update this each match day or load from a JSON file.

MATCH_SCHEDULE = [
    # Format: team1, team2, kickoff_local (HH:MM), kickoff_cet (HH:MM), stadium_tz
    # Example for June 11, 2026 — Group A:
    {
        "team1": "Mexico",
        "team2": "South Africa",
        "kickoff_local": "15:00",
        "kickoff_cet": "22:00",
        "tz": "CT",
        "stadium": "Estadio Azteca, Mexico City",
        "match_id": None,
    },
    {
        "team1": "South Korea",
        "team2": "Czech Republic",
        "kickoff_local": "22:00",
        "kickoff_cet": "05:00+1",
        "tz": "CT",
        "stadium": "Estadio AKRON, Guadalajara",
        "match_id": None,
    },
]

# ── Time helpers ──────────────────────────────────────────────────────────────
def parse_time(time_str: str) -> datetime:
    """Parse HH:MM into today's datetime."""
    h, m = map(int, time_str.split(":"))
    now = datetime.now()
    return now.replace(hour=h, minute=m, second=0, microsecond=0)

def minutes_until(time_str: str) -> int:
    target = parse_time(time_str)
    now = datetime.now()
    diff = (target - now).total_seconds() / 60
    # Handle past times (next day)
    if diff < -60:
        diff += 24 * 60
    return int(diff)

def subtract_minutes(time_str: str, mins: int) -> str:
    """Return HH:MM that is `mins` minutes before time_str."""
    dt = parse_time(time_str) - timedelta(minutes=mins)
    return dt.strftime("%H:%M")

# ── Cycle runners (thread-safe) ───────────────────────────────────────────────
def run_morning_analysis():
    matches = [{"team1": m["team1"], "team2": m["team2"]} for m in MATCH_SCHEDULE]
    t = threading.Thread(target=cycle1_morning, args=(matches,))
    t.daemon = True
    t.start()

def run_prematch(match: dict):
    def _run():
        cycle2_prematch(
            match["team1"], match["team2"],
            match["kickoff_local"], match["kickoff_cet"]
        )
    t = threading.Thread(target=_run)
    t.daemon = True
    t.start()

def run_lastminute(match: dict):
    def _run():
        cycle3_lastminute(match["team1"], match["team2"], match["kickoff_local"])
    t = threading.Thread(target=_run)
    t.daemon = True
    t.start()

def run_lineup_notify(match: dict):
    def _run():
        notify_lineup_confirmed(
            match["team1"], match["team2"],
            match["kickoff_local"], match.get("match_id")
        )
    t = threading.Thread(target=_run)
    t.daemon = True
    t.start()

# ── Schedule builder ──────────────────────────────────────────────────────────
def build_schedule():
    """Register all jobs for today's match day."""
    log("Building daily schedule...")

    # CYCLE 1 — Morning analysis: first match kickoff - 2h = 08:00 local equivalent
    if MATCH_SCHEDULE:
        first_ko = MATCH_SCHEDULE[0]["kickoff_local"]
        morning_time = subtract_minutes(first_ko, 120)
        schedule.every().day.at(morning_time).do(run_morning_analysis).tag("cycle1")
        log(f"  📊 CYCLE 1 — Morning analysis: {morning_time}")

    # Per-match cycles
    for match in MATCH_SCHEDULE:
        ko = match["kickoff_local"]
        team1, team2 = match["team1"], match["team2"]
        label = f"{team1} vs {team2}"

        # CYCLE 2 — Pre-match refresh: 75 min before kick-off
        t_prematch = subtract_minutes(ko, 75)
        schedule.every().day.at(t_prematch).do(run_prematch, match).tag("cycle2", label)
        log(f"  ⚡ CYCLE 2 — Pre-match refresh [{label}]: {t_prematch}")

        # TYPE B — Lineup confirmation: 65 min before kick-off
        t_lineup = subtract_minutes(ko, 65)
        schedule.every().day.at(t_lineup).do(run_lineup_notify, match).tag("lineup", label)
        log(f"  📋 TYPE B — Lineup confirmed [{label}]: {t_lineup}")

        # CYCLE 3 — Last minute tip: 30 min before kick-off
        t_lastmin = subtract_minutes(ko, 30)
        schedule.every().day.at(t_lastmin).do(run_lastminute, match).tag("cycle3", label)
        log(f"  🔴 CYCLE 3 — Last minute tip [{label}]: {t_lastmin}")

    log(f"Schedule built. {len(schedule.jobs)} jobs registered.")
    print_schedule()

def print_schedule():
    print("\n" + "═" * 60)
    print("  WC 2026 AGENT — TODAY'S SCHEDULE")
    print("═" * 60)
    for job in sorted(schedule.jobs, key=lambda j: j.next_run or datetime.max):
        tags = list(job.tags)
        label = " | ".join(tags)
        next_run = job.next_run.strftime("%H:%M") if job.next_run else "?"
        print(f"  {next_run}  →  {label}")
    print("═" * 60 + "\n")

# ── Main loop ─────────────────────────────────────────────────────────────────
def run_scheduler():
    log("WC 2026 Analysis Agent STARTED")
    build_schedule()

    def shutdown(sig, frame):
        log("Scheduler shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    log("Scheduler running. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(15)

def run_test_mode():
    """Test mode: run all cycles immediately without waiting."""
    log("=== TEST MODE — Running all cycles immediately ===")
    if MATCH_SCHEDULE:
        m = MATCH_SCHEDULE[0]
        log("Running CYCLE 1...")
        cycle1_morning([{"team1": m["team1"], "team2": m["team2"]}])
        log("Running CYCLE 2...")
        cycle2_prematch(m["team1"], m["team2"], m["kickoff_local"], m["kickoff_cet"])
        log("Running CYCLE 3...")
        cycle3_lastminute(m["team1"], m["team2"], m["kickoff_local"])
    log("=== TEST MODE COMPLETE ===")

def load_schedule_from_file(filepath: str):
    global MATCH_SCHEDULE
    path = Path(filepath)
    if not path.exists():
        log(f"Schedule file not found: {filepath}", "ERROR")
        sys.exit(1)
    MATCH_SCHEDULE = json.loads(path.read_text())
    log(f"Loaded {len(MATCH_SCHEDULE)} matches from {filepath}")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--test" in sys.argv:
        run_test_mode()
    elif "--matchday" in sys.argv:
        idx = sys.argv.index("--matchday")
        load_schedule_from_file(sys.argv[idx + 1])
        run_scheduler()
    else:
        run_scheduler()
