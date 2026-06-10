#!/usr/bin/env python3
"""
WC 2026 Analysis Agent — Core runner
Executes all 3 automated cycles + 4 notification types.
Each cycle calls the Claude API with pre-built prompts + live API data.
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import requests

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent

# Load .env
_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())
SCRIPTS = ROOT / "scripts"
LOGS = ROOT / "logs"
PROMPTS = Path(__file__).parent / "prompts"
LOGS.mkdir(exist_ok=True)

sys.path.insert(0, str(SCRIPTS / "api"))
from rapidapi import fetch_match_data, get_today_matches, get_lineups, get_live_score, get_match_stats

# Telegram — optional, only if configured
def _tg_send(cycle: str, match: str, content: str):
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        return
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from telegram_bot import send_analysis
        ok = send_analysis(cycle, match, content)
        if ok:
            log(f"Telegram: sent {cycle} for {match}")
        else:
            log(f"Telegram: send failed for {cycle}/{match}", "WARN")
    except Exception as e:
        log(f"Telegram: error — {e}", "WARN")

# ── Logging ──────────────────────────────────────────────────────────────────
def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    with open(LOGS / "agent.log", "a") as f:
        f.write(line + "\n")

def save_output(cycle: str, match: str, content: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_match = match.replace(" ", "_").replace("/", "-")
    path = LOGS / f"{cycle}_{safe_match}_{ts}.md"
    path.write_text(content)
    log(f"Output saved: {path.name}")
    return path

# ── Claude CLI runner ─────────────────────────────────────────────────────────
def run_claude(prompt: str, context: str = "") -> str:
    """
    Runs Claude Code CLI with a prompt and returns the output.
    The context (API data) is injected into the prompt.
    """
    full_prompt = prompt
    if context:
        full_prompt = f"{prompt}\n\n---\n## LIVE API DATA (fetched now):\n```json\n{context}\n```"

    try:
        result = subprocess.run(
            ["claude", "--print", full_prompt],
            capture_output=True, text=True, timeout=300,
            cwd=str(ROOT)
        )
        if result.returncode != 0:
            log(f"Claude CLI error: {result.stderr[:200]}", "ERROR")
            return result.stdout or result.stderr
        return result.stdout
    except FileNotFoundError:
        log("Claude CLI not found — running in standalone mode", "WARN")
        return f"[STANDALONE MODE — Claude CLI not available]\nPrompt would be:\n{full_prompt[:500]}..."
    except subprocess.TimeoutExpired:
        log("Claude CLI timed out", "ERROR")
        return "[TIMEOUT]"

# ── Prompt templates ─────────────────────────────────────────────────────────
def load_system_prompt() -> str:
    sp = ROOT / "system-prompt" / "WC_Analysis_Agent_EN.md"
    return sp.read_text() if sp.exists() else ""

CYCLE1_TEMPLATE = """
You are the WC 2026 Analysis Agent running CYCLE 1 — MORNING DAILY ANALYSIS.

Today is {date}. The following matches are scheduled today:
{matches}

Execute the full morning analysis workflow:
1. Apply the 5-layer model (DNA → Club Form → Tactics → Situation → Market) to EACH match
2. Build full Poisson probability distribution for each match
3. Generate all tips with: type + odds + probability % + value % + reason
4. Build the daily tips table and 4 combinations (Safe / Balanced / Bold / Player Scorer)
5. Select Top Pick of the Day + Surprise of the Day (odds 2.80+)
6. Output daily risk profile + bankroll recommendations

Use the live API data provided below. Where API data shows SUBSCRIPTION_REQUIRED, note it and use web search context instead.
"""

CYCLE2_TEMPLATE = """
You are the WC 2026 Analysis Agent running CYCLE 2 — PRE-MATCH REFRESH.
Match: {match}
Kick-off: {kickoff} ({kickoff_cet} CET)
Time to kick-off: ~{minutes_to_ko} minutes

Check what has changed since the morning analysis:
- Lineup confirmed? Any changes vs morning expectation?
- Odds movement since morning? (0.3+ = sharp money signal)
- Any injury updates in last 2 hours?
- Weather at the stadium?

For each morning tip decide: NO CHANGE ✅ / UPDATED ⚠️ / CANCELLED ❌ / NEW TIP 🆕

Output the PRE-MATCH REFRESH report in exact format from the system prompt.
"""

CYCLE3_TEMPLATE = """
You are the WC 2026 Analysis Agent running CYCLE 3 — LAST MINUTE TIP.
Match: {match}
Kick-off: {kickoff} — 30 MINUTES TO GO

Official lineups should now be confirmed. Check:
- Any surprise starters / non-starters vs expectation?
- Odds movement in LAST HOUR (most reliable sharp money signal)
- Real-time weather at the stadium?

Output the LAST MINUTE TIP report in exact format from the system prompt.
All morning tips must be marked: STILL VALID ✅ or CANCELLED ❌
"""

NOTIFY_LINEUP_TEMPLATE = """
You are the WC 2026 Analysis Agent sending a TYPE B — LINEUP CONFIRMATION notification.
Match: {match} | Kick-off: {kickoff}

Official lineups have just been published. Analyse:
1. List both XIs with formation
2. Flag any changes vs expectation (NOT STARTING / SURPRISE STARTER)
3. Assess impact on all existing tips: STILL VALID ✅ / CANCELLED ❌ / NEW TIP

Output in the confirmed lineup notification format from the system prompt.
"""

NOTIFY_POSTMATCH_TEMPLATE = """
You are the WC 2026 Analysis Agent sending a TYPE D — POST-MATCH REPORT.
Match: {match} | Final score: {score}

Generate the complete post-match report including:
- Full match statistics table
- Goal-by-goal with scorers and assists
- Match summary (who played better, key moments)
- Man of the Match + Worst Player ratings
- Substitutions and their impact
- Tournament context (group table update)
- Tip results: each morning tip WON ✅ or LOST ❌

Use the live statistics data provided.
"""

# ── Cycle 1 — Morning Analysis ───────────────────────────────────────────────
def cycle1_morning(matches: list = None):
    log("=== CYCLE 1 — MORNING ANALYSIS STARTED ===")

    raw_matches = get_today_matches()
    if "error" in raw_matches:
        log(f"Live API unavailable: {raw_matches.get('message', raw_matches['error'])}", "WARN")
        matches_text = "Live API data unavailable — use web search for today's WC 2026 schedule."
    else:
        matches_text = json.dumps(raw_matches, indent=2)

    all_data = {}
    if matches:
        for m in matches:
            t1, t2 = m["team1"], m["team2"]
            log(f"Fetching data for {t1} vs {t2}...")
            all_data[f"{t1}_vs_{t2}"] = fetch_match_data(t1, t2)

    context = json.dumps(all_data, indent=2) if all_data else matches_text

    prompt = CYCLE1_TEMPLATE.format(
        date=datetime.now().strftime("%A, %B %d %Y"),
        matches=matches_text,
    )

    output = run_claude(prompt, context)
    path = save_output("cycle1_morning", "all_matches", output)
    _tg_send("morning", "WC 2026 — All Matches", output)
    log(f"=== CYCLE 1 COMPLETE — output: {path} ===")
    return output

# ── Cycle 2 — Pre-Match Refresh ──────────────────────────────────────────────
def cycle2_prematch(team1: str, team2: str, kickoff_local: str, kickoff_cet: str):
    match = f"{team1} vs {team2}"
    log(f"=== CYCLE 2 — PRE-MATCH REFRESH: {match} ===")

    ko_dt = datetime.strptime(kickoff_local, "%H:%M")
    now = datetime.now()
    diff = (ko_dt.replace(year=now.year, month=now.month, day=now.day) - now)
    minutes_to_ko = max(0, int(diff.total_seconds() / 60))

    api_data = fetch_match_data(team1, team2)
    context = json.dumps(api_data, indent=2)

    prompt = CYCLE2_TEMPLATE.format(
        match=match,
        kickoff=kickoff_local,
        kickoff_cet=kickoff_cet,
        minutes_to_ko=minutes_to_ko,
    )

    output = run_claude(prompt, context)
    path = save_output("cycle2_prematch", match, output)
    _tg_send("prematch", match, output)
    log(f"=== CYCLE 2 COMPLETE — output: {path} ===")
    return output

# ── Cycle 3 — Last Minute Tip ────────────────────────────────────────────────
def cycle3_lastminute(team1: str, team2: str, kickoff_local: str):
    match = f"{team1} vs {team2}"
    log(f"=== CYCLE 3 — LAST MINUTE TIP: {match} ===")

    api_data = fetch_match_data(team1, team2)
    context = json.dumps(api_data, indent=2)

    prompt = CYCLE3_TEMPLATE.format(match=match, kickoff=kickoff_local)

    output = run_claude(prompt, context)
    path = save_output("cycle3_lastminute", match, output)
    _tg_send("lastminute", match, output)
    log(f"=== CYCLE 3 COMPLETE — output: {path} ===")
    return output

# ── Notification: Lineup Confirmed ───────────────────────────────────────────
def notify_lineup_confirmed(team1: str, team2: str, kickoff: str, match_id: str = None):
    match = f"{team1} vs {team2}"
    log(f"=== NOTIFICATION B — LINEUP CONFIRMED: {match} ===")

    lineup_data = get_lineups(match_id) if match_id else {"error": "no_match_id"}
    context = json.dumps(lineup_data, indent=2)

    prompt = NOTIFY_LINEUP_TEMPLATE.format(match=match, kickoff=kickoff)

    output = run_claude(prompt, context)
    path = save_output("notify_lineup", match, output)
    _tg_send("lineup", match, output)
    log(f"=== LINEUP NOTIFICATION COMPLETE — output: {path} ===")
    return output

# ── Notification: Post-Match Report ─────────────────────────────────────────
def notify_postmatch(team1: str, team2: str, score: str, match_id: str = None):
    match = f"{team1} vs {team2}"
    log(f"=== NOTIFICATION D — POST-MATCH REPORT: {match} {score} ===")

    stats = get_match_stats(match_id) if match_id else {"error": "no_match_id"}
    context = json.dumps(stats, indent=2)

    prompt = NOTIFY_POSTMATCH_TEMPLATE.format(match=match, score=score)

    output = run_claude(prompt, context)
    path = save_output("notify_postmatch", match, output)
    _tg_send("postmatch", match, output)
    log(f"=== POST-MATCH REPORT COMPLETE — output: {path} ===")
    return output

# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "morning":
        cycle1_morning()
    elif cmd == "prematch" and len(sys.argv) >= 5:
        cycle2_prematch(sys.argv[2], sys.argv[3], sys.argv[4],
                        sys.argv[5] if len(sys.argv) > 5 else "??:?? CET")
    elif cmd == "lastminute" and len(sys.argv) >= 5:
        cycle3_lastminute(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "lineup" and len(sys.argv) >= 5:
        notify_lineup_confirmed(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "postmatch" and len(sys.argv) >= 5:
        notify_postmatch(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print("""
WC 2026 Analysis Agent — Usage:

  python3 wc_agent.py morning
    → Run CYCLE 1: full morning analysis for all today's matches

  python3 wc_agent.py prematch TEAM1 TEAM2 HH:MM [CET]
    → Run CYCLE 2: pre-match refresh 60-90 min before kick-off
    → Example: python3 wc_agent.py prematch Mexico "South Africa" 15:00 22:00

  python3 wc_agent.py lastminute TEAM1 TEAM2 HH:MM
    → Run CYCLE 3: last minute tip 30 min before kick-off

  python3 wc_agent.py lineup TEAM1 TEAM2 HH:MM
    → Send TYPE B notification: lineup confirmed

  python3 wc_agent.py postmatch TEAM1 TEAM2 SCORE
    → Send TYPE D notification: post-match report
    → Example: python3 wc_agent.py postmatch Mexico "South Africa" "2:0"
""")
