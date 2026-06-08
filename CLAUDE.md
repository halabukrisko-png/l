# ⚽ World Cup Analysis Agent — WC 2026

This repository contains the configuration and system prompt for the **FIFA World Cup 2026 AI Football Match Analyst Agent**.

## What This Agent Does

A professional AI football match analyst for WC 2026 that:
- Runs **3 automated analytical cycles** per match day (morning analysis, pre-match refresh, last-minute tip)
- Sends **4 types of daily notifications** (morning briefing, lineup confirmations, live alerts, post-match reports)
- Uses a **5-layer data model**: National Team DNA → Club Form → Tactics/xG → Situational Variables → Market Data
- Calculates **Poisson probability distributions** for scorelines and flags value bets automatically
- Draws from **Tier 1 sources**: Opta, StatsBomb, FBref, The Athletic, ESPN BPI, Gracenote/Nielsen, Pinnacle, Betfair Exchange

## Repository Structure

```
/
├── CLAUDE.md                        # This file
├── system-prompt/
│   └── WC_Analysis_Agent_EN.md      # Full agent system prompt (English)
├── .claude/
│   └── settings.json                # Claude Code settings and MCP servers
└── mcp-config/
    └── servers.json                 # MCP server configurations reference
```

## MCP Servers Configured

| Server | Purpose |
|--------|---------|
| Sports Odds Intelligence API | Live odds, odds movement, value bet detection |
| Football Prediction WC 2026 | Match predictions, probability models |
| World Cup 2026 Live API | Live scores, lineups, match events |
| WorldCupTravelDealsAPI | Travel/logistics data (travel burden analysis) |

## Running the Agent

Load the system prompt from `system-prompt/WC_Analysis_Agent_EN.md` into Claude and the agent will:

1. **On match days**: Automatically run Morning Analysis (08:00 local), Pre-Match Refresh (60–90 min before kick-off), and Last Minute Tip (30 min before kick-off)
2. **Throughout the day**: Send Morning Briefing, Lineup Confirmations, Live Alerts, Post-Match Reports, and Evening Summary
3. **On demand**: Answer any WC 2026 question, run custom match analyses, evaluate betting combinations

## Key Agent Rules

- Always searches for current data before analysing — never writes from memory alone
- Every tip includes: type + odds + probability % + value % + reasoning
- Combinations only use independent tips (one tip per match max)
- Win/Draw/Loss probabilities always sum to ~100%
- Gamble tips are always clearly labelled

## Time Zones

WC 2026 is played across USA, Canada, and Mexico. All times shown in **local stadium time** with CET equivalents.
- Eastern Time (ET) = CET − 6h
- Central Time (CT) = CET − 7h  
- Pacific Time (PT) = CET − 9h
