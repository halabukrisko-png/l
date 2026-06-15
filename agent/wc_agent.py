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
import tempfile
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
    Writes prompt to a temp file to avoid CLI stdin size limits.
    """
    full_prompt = prompt
    if context:
        full_prompt = f"{prompt}\n\n---\n## LIVE API DATA (fetched now):\n```json\n{context}\n```"

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(full_prompt)
            tmp = f.name

        result = subprocess.run(
            ["claude", "--print", f"@{tmp}"],
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
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass

# ── Prompt templates ─────────────────────────────────────────────────────────
def load_system_prompt() -> str:
    sp = ROOT / "system-prompt" / "WC_Analysis_Agent_EN.md"
    return sp.read_text() if sp.exists() else ""

CYCLE1_TEMPLATE = """
You are the WC 2026 Analysis Agent running CYCLE 1 — MORNING DAILY ANALYSIS.
You are a PROFESSIONAL AI football match analyst specialising in FIFA World Cup 2026.

Today is {date}. The following matches are scheduled today:
{matches}

MANDATORY: Search the internet NOW for fresh data before writing anything:
- For EACH match search: "[TEAM1] vs [TEAM2] preview {date}", "[TEAM1] injury news", "[TEAM2] injury news", "[TEAM1] vs [TEAM2] prediction", "[TEAM1] vs [TEAM2] odds", "[TEAM1] expected lineup", "[TEAM2] expected lineup"
- Also search: "[TEAM1] vs [TEAM2] {date} World Cup" on ESPN, BBC Sport, The Athletic, Goal.com
- Collect current bookmaker odds from at least 3 sources

=== MANDATORY OUTPUT FORMAT ===

# 🌅 WC 2026 — MORNING ANALYSIS | {date}

---

For EACH match, produce this COMPLETE structure:

## 🏟️ MATCH N: [TEAM1] vs [TEAM2]
⏰ Kick-off: [local time + city] | [CET equivalent]
📍 Stadium: [name, city]
🏆 Stage: [Group X — Match day X]

### 📋 BASIC INFO
- H2H record (last 5–10 meetings): [results]
- Last 5 matches TEAM1: [W/D/L W/D/L W/D/L W/D/L W/D/L with scores]
- Last 5 matches TEAM2: [W/D/L W/D/L W/D/L W/D/L W/D/L with scores]
- Tournament form so far (if applicable)
- 🌡️ Weather: [temperature, conditions, humidity at stadium city]

### 🔍 LAYER 1 — DNA & IDENTITY
- Confederation & qualification path
- Playing style: possession/counter/pressing/direct — with specific %
- Historical WC performance (last 3 tournaments)
- Key motivation & psychological factors
- EPI (Elite Player Index): Key players, their form, injury status
  → Name (position) — club form — WC form — injury status
- Disciplinary profile: avg yellow cards, suspensions risk

### 📊 LAYER 2 — CLUB FORM vs NATIONAL TEAM FORM
- Club form of key players (last 6 weeks at their clubs)
- National team form: last 5 competitive matches with scores
- fatigue level (travel, days between matches, squad rotation signals)
- Key players in form: [name] — [club] — [recent goals/assists/xG]
- Key players out of form or injured: [name] — [issue]

### 🎯 LAYER 3 — TACTICS & xG MODEL
**Expected starting XI TEAM1:** [4-3-3 or other formation]
GK: [name] | DEF: [names] | MID: [names] | FWD: [names]

**Expected starting XI TEAM2:** [formation]
GK: [name] | DEF: [names] | MID: [names] | FWD: [names]

**Tactical key points:**
→ [TEAM1] attacking approach: [specific]
→ [TEAM2] defensive setup: [specific]
→ Key tactical duel: [player vs player, position vs position]
→ Set piece threat: [who takes, who targets]

**xG estimate:**
- TEAM1 xG: X.X (based on: [reasons])
- TEAM2 xG: X.X (based on: [reasons])
- Implied home/away advantage: [%]

### 🌍 LAYER 4 — SITUATIONAL & CONTEXTUAL
- Group table context: what each team needs from this match
- Motivation asymmetry: [who needs points more urgently]
- Rotation signals: [any hints of squad rotation?]
- Travel fatigue: [distance from last match, days between]
- Referee profile (if known): [cards per match avg, style]
- Media pressure & psychological load

### 📈 LAYER 5 — MARKET INTELLIGENCE
Current odds (from multiple sources):
| Outcome | Odds | Implied % | True % | Value |
|---------|------|-----------|--------|-------|
| TEAM1 Win | X.XX | XX% | XX% | +/-X% |
| Draw | X.XX | XX% | XX% | +/-X% |
| TEAM2 Win | X.XX | XX% | XX% | +/-X% |

- Odds movement: [opening odds → current odds, direction of movement]
- Sharp money signals: [any significant line movement?]
- Asian handicap line: [what it implies about bookmaker view]
- Total goals line: [O/U X.5 at what odds]
- Value bets identified: [specific markets with +EV]

### 🎲 POISSON PROBABILITY DISTRIBUTION
Based on xG: TEAM1 = X.X | TEAM2 = X.X

Most likely scorelines:
| Score | Probability |
|-------|-------------|
| 1:0 | X.X% |
| 0:0 | X.X% |
| 1:1 | X.X% |
| 2:0 | X.X% |
| 2:1 | X.X% |
| 0:1 | X.X% |
| 1:2 | X.X% |
| 0:2 | X.X% |
[continue to cover ~15 most likely scorelines]

Aggregated from Poisson:
- TEAM1 wins: XX% | Draw: XX% | TEAM2 wins: XX%
- Both teams score (BTTS): XX%
- Over 2.5 goals: XX%
- Over 1.5 goals: XX%

### 🌐 5-SOURCE CONSENSUS TABLE
| Source | TEAM1 | Draw | TEAM2 | Top tip |
|--------|-------|------|-------|---------|
| ESPN | X.X% | X.X% | X.X% | [tip] |
| BBC Sport | X.X% | X.X% | X.X% | [tip] |
| The Athletic | X.X% | X.X% | X.X% | [tip] |
| Goal.com | X.X% | X.X% | X.X% | [tip] |
| Betfair/Odds Portal | X.X% | X.X% | X.X% | [tip] |
| **CONSENSUS** | **X.X%** | **X.X%** | **X.X%** | **[tip]** |

---

## 📊 BLOCK A — TIPS FOR MATCH N: [TEAM1] vs [TEAM2]

For each tip:
→ [Category emoji] TIP TYPE: [specific bet description]
   Odds: X.XX | Probability: XX% | Value: +XX% | Confidence: HIGH/MED/LOW
   Reason: [2–3 sentences — specific data-backed reasons]

Minimum 3–5 tips per match covering: match result, goals market, handicap, BTTS, player-specific.

Categories: 🔒 Safe (65%+ prob) | 💚 Value (35-64% + positive EV) | ⚡ Bold (25-34%) | 🎰 Gamble (<25%)

---

## 📋 BLOCK B — DAILY TIPS TABLE (all matches)

| # | Match | Tip | Odds | Prob% | Value% | Category |
|---|-------|-----|------|-------|--------|----------|
| 1 | ... | ... | X.XX | XX% | +XX% | 🔒 |
[all tips from all matches]

---

## 🎯 BLOCK C — COMBINATIONS & TOP PICKS

### 4 COMBINATIONS:
🔒 **SAFE COMBINATION** (2–3 legs, all 🔒 tips, target odds 1.80–2.50):
→ Leg 1: [match] — [tip] @ X.XX
→ Leg 2: [match] — [tip] @ X.XX
→ Combined odds: X.XX | Combined probability: XX%
⚠️ Rule: max 1 tip per match

💚 **BALANCED COMBINATION** (3 legs, mix 🔒+💚, target odds 3.00–5.00):
→ Leg 1: [match] — [tip] @ X.XX
→ Leg 2: [match] — [tip] @ X.XX
→ Leg 3: [match] — [tip] @ X.XX
→ Combined odds: X.XX | Combined probability: XX%

⚡ **BOLD COMBINATION** (3–4 legs, includes ⚡ tips, target odds 6.00–12.00):
→ [legs]
→ Combined odds: X.XX | Combined probability: XX%

⚽ **PLAYER SCORER COMBINATION** (correct scores / first scorer / anytime scorer):
→ [tips focused on individual player performance]

### 🏆 TOP PICK OF THE DAY:
[Category emoji] **[Specific bet description]**
Match: [TEAM1] vs [TEAM2]
Odds: X.XX | Probability: XX% | Value: +XX%
Reason: [3–4 sentences — strongest argument, why this is the best tip today]

### 😲 SURPRISE OF THE DAY (odds 2.80+):
[Category emoji] **[Specific surprise bet]**
Odds: X.XX | Probability: XX% | Value: +XX%
Reason: [2–3 sentences — why this underdog/surprise bet has merit]

---

## 📉 DAILY RISK PROFILE & BANKROLL

- Overall market confidence today: HIGH / MEDIUM / LOW
- Recommended unit stake: X% of bankroll per tip
- Max exposure today: X% of total bankroll
- Highest value bet today: [tip + value%]
- Safest bet today: [tip + probability%]

---

## 🔍 SOURCES USED
[List all sources searched and found — URLs or site names]

IMPORTANT RULES:
- Search the internet for EVERY piece of data — do not write from memory alone
- Every single tip must have: type + odds + probability% + value% + 2-sentence reason
- Never combine two tips from the same match in one combination
- If you cannot find odds, state it clearly and note confidence is lower
- Probabilities for win/draw/loss must add up to ~100%
- If a match has no clear signal, say so — do not fabricate tips
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
