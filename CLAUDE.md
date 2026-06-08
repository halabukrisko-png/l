# ⚽ World Cup Analysis Agent — WC 2026

Professional AI football analyst for FIFA World Cup 2026. Full 5-layer analysis model, 3 automated cycles, 4 notification types, Poisson probability distributions, value bet detection.

## Repository Structure

```
/
├── CLAUDE.md                          # This file
├── run.sh                             # Quick launcher — all commands
├── system-prompt/
│   └── WC_Analysis_Agent_EN.md        # Full agent system prompt
├── agent/
│   ├── wc_agent.py                    # Core: all 3 cycles + 4 notifications
│   ├── scheduler.py                   # Automatic time-based scheduler
│   └── matchday.json                  # Today's match schedule (update daily)
├── scripts/
│   └── api/
│       └── rapidapi.py                # All 5 RapidAPI data sources
├── .claude/
│   └── settings.json                  # MCP servers + hooks
├── mcp-config/
│   └── servers.json                   # MCP server reference
└── logs/                              # Output from each cycle (auto-created)
```

## Quick Start

```bash
# Morning analysis (CYCLE 1) — run at 08:00 on match days
bash run.sh morning

# Start full automatic scheduler (all cycles auto-timed)
bash run.sh scheduler

# Manual cycle triggers
bash run.sh prematch Mexico "South Africa" 15:00 "22:00 CEST"
bash run.sh lastminute Mexico "South Africa" 15:00
bash run.sh postmatch Mexico "South Africa" "2:0"

# Test everything works
bash run.sh test
```

## Automated Cycles (system-prompt/WC_Analysis_Agent_EN.md)

| Cycle | Trigger | What it does |
|-------|---------|--------------|
| 🌅 CYCLE 1 | 08:00 (2h before first kick-off) | Morning analysis — all matches, full 5-layer model, daily tips table |
| ⚡ CYCLE 2 | 75 min before each kick-off | Pre-match refresh — lineups, odds movement, tip updates |
| 🔴 CYCLE 3 | 30 min before each kick-off | Last minute tip — confirmed lineups, sharp money signals |
| 📋 TYPE B | 65 min before each kick-off | Lineup confirmation notification |
| 🏁 TYPE D | After final whistle | Post-match report — stats, goals, tip results |

## 5 MCP Data Sources

| Server key | API | Data |
|-----------|-----|------|
| `wc2026-live` | world-cup-2026-live-api | Live scores, lineups, match events |
| `football-prediction-wc2026` | football-prediction-wc2026 | Match predictions, probabilities |
| `sports-odds-intelligence` | sports-odds-intelligence-api | Live odds, movement, value bets |
| `worldcup-travel-deals` | worldcuptraveldealsapi | Travel burden, logistics |
| `zafronix-fifa-wc` | zafronix-fifa-world-cup-api | Squad data, player stats, injuries |

> **Note:** MCP servers require active RapidAPI subscription for each API.
> Subscribe at: https://rapidapi.com — search for each API name above.
> Without subscription, the agent falls back to WebSearch automatically.

## Match Day Workflow

1. **Update `agent/matchday.json`** with today's matches (or let Live API auto-detect)
2. **Run `bash run.sh scheduler`** — all cycles fire automatically at correct times
3. **Outputs land in `logs/`** — one file per cycle per match

## Time Zones (WC 2026 — USA/Canada/Mexico)

- Eastern Time (ET) = CET − 6h
- Central Time (CT) = CET − 7h
- Pacific Time (PT) = CET − 9h
