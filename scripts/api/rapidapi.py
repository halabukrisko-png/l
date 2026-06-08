#!/usr/bin/env python3
"""
WC 2026 Analysis Agent — RapidAPI wrapper
Handles all 5 MCP data sources via direct HTTP calls.
Falls back gracefully when APIs are unavailable (subscription needed).
"""

import requests
import json
import sys
from datetime import datetime

RAPIDAPI_KEY = "afc1c06083mshc8653b5fb32977cp14e319jsn4a3f60aa7fd8"

APIS = {
    "live":        "world-cup-2026-live-api.p.rapidapi.com",
    "predictions": "football-prediction-world-cup-2026-match-predictions.p.rapidapi.com",
    "odds":        "sports-odds-intelligence-api.p.rapidapi.com",
    "travel":      "worldcuptraveldealsapi.p.rapidapi.com",
    "zafronix":    "zafronix-fifa-world-cup-api.p.rapidapi.com",
}

def call(api_name: str, path: str, params: dict = None) -> dict:
    host = APIS[api_name]
    url = f"https://{host}{path}"
    headers = {
        "x-rapidapi-host": host,
        "x-rapidapi-key": RAPIDAPI_KEY,
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 403:
            return {"error": "SUBSCRIPTION_REQUIRED", "api": api_name,
                    "message": f"Subscribe to '{api_name}' on RapidAPI to activate this data source."}
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "api": api_name}

# ── Live match data ──────────────────────────────────────────────────────────

def get_today_matches():
    """CYCLE 1: All matches today with kick-off times and venues."""
    today = datetime.now().strftime("%Y-%m-%d")
    return call("live", "/matches", {"date": today})

def get_live_score(match_id: str):
    """CYCLE 4C: Live score and events for a running match."""
    return call("live", f"/matches/{match_id}/live")

def get_lineups(match_id: str):
    """CYCLE 4B: Official confirmed lineups."""
    return call("live", f"/matches/{match_id}/lineups")

def get_match_stats(match_id: str):
    """CYCLE 4D: Full post-match statistics."""
    return call("live", f"/matches/{match_id}/statistics")

# ── Predictions ──────────────────────────────────────────────────────────────

def get_match_prediction(team1: str, team2: str):
    """LAYER 5: AI match prediction with win/draw/loss probabilities."""
    return call("predictions", "/predictions", {"home": team1, "away": team2})

def get_group_standings(group: str):
    """Tournament context: current group table."""
    return call("predictions", "/standings", {"group": group})

# ── Odds ─────────────────────────────────────────────────────────────────────

def get_current_odds(team1: str, team2: str):
    """LAYER 5: Live odds from multiple bookmakers + movement."""
    return call("odds", "/odds", {"home": team1, "away": team2, "tournament": "FIFA World Cup 2026"})

def get_odds_movement(team1: str, team2: str):
    """Sharp money detection: opening vs current odds."""
    return call("odds", "/odds/movement", {"home": team1, "away": team2})

def get_value_bets(team1: str, team2: str):
    """Automatic value bet detection across all markets."""
    return call("odds", "/value-bets", {"home": team1, "away": team2})

# ── Zafronix FIFA data ───────────────────────────────────────────────────────

def get_wc_schedule():
    """Full WC 2026 tournament schedule."""
    return call("zafronix", "/schedule")

def get_team_info(team: str):
    """LAYER 1+2: Team profile, squad, form, history."""
    return call("zafronix", "/team", {"name": team})

def get_player_stats(player: str):
    """LAYER 2: Individual player statistics at WC 2026."""
    return call("zafronix", "/player", {"name": player})

def get_injury_report(team: str):
    """CYCLE 1+2: Current injury and availability status."""
    return call("zafronix", "/injuries", {"team": team})

# ── Travel/Logistics ─────────────────────────────────────────────────────────

def get_travel_burden(team: str):
    """LAYER 4: Team travel distance, jet lag, logistics fatigue."""
    return call("travel", "/team-travel", {"team": team})

# ── Aggregated data fetch for full match analysis ────────────────────────────

def fetch_match_data(team1: str, team2: str) -> dict:
    """
    Fetches all available data for a match from all APIs in parallel.
    Used by CYCLE 1 (morning analysis) and CYCLE 2 (pre-match refresh).
    Returns combined data package for the 5-layer analysis model.
    """
    import concurrent.futures

    tasks = {
        "prediction":    lambda: get_match_prediction(team1, team2),
        "odds":          lambda: get_current_odds(team1, team2),
        "odds_movement": lambda: get_odds_movement(team1, team2),
        "value_bets":    lambda: get_value_bets(team1, team2),
        "team1_info":    lambda: get_team_info(team1),
        "team2_info":    lambda: get_team_info(team2),
        "team1_injuries":lambda: get_injury_report(team1),
        "team2_injuries":lambda: get_injury_report(team2),
        "team1_travel":  lambda: get_travel_burden(team1),
        "team2_travel":  lambda: get_travel_burden(team2),
    }

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(fn): key for key, fn in tasks.items()}
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            results[key] = future.result()

    return {
        "match": f"{team1} vs {team2}",
        "fetched_at": datetime.now().isoformat(),
        "data": results,
    }

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "matches"
    if cmd == "matches":
        print(json.dumps(get_today_matches(), indent=2))
    elif cmd == "match" and len(sys.argv) == 4:
        print(json.dumps(fetch_match_data(sys.argv[2], sys.argv[3]), indent=2))
    elif cmd == "schedule":
        print(json.dumps(get_wc_schedule(), indent=2))
    elif cmd == "standings" and len(sys.argv) == 3:
        print(json.dumps(get_group_standings(sys.argv[2]), indent=2))
    else:
        print("Usage: rapidapi.py [matches | match TEAM1 TEAM2 | schedule | standings GROUP]")
