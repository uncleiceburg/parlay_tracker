# Parlay Betting Tracker

Daily NBA 5-game parlay picks from DraftKings, argued by 3 agents, tracked over time.

## 3 Agents

- **The Sharp**: Contrarian, +EV dogs & overs. Fades public consensus.
- **The Public**: Recreational, favorites & consensus. Follows the crowd.
- **The Model**: Quantitative, pace/defensive ratings & net rating splits. Data-driven.

## $10 base bet per agent per day

## Quick Start

```bash
# Scrape today's lines
source .venv/bin/activate
python scrape_lines.py

# Run agents to generate parlays
python run_agent.py

# Update results after games (prompts for each leg)
python update_results.py

# Generate Friday weekly summary
python weekly_summary.py
```

## Files

- `scrape_lines.py` - Pulls NBA lines from DraftKings (API + fallback scraping)
- `run_agent.py` - Runs all 3 agents, generates 5-leg parlays
- `update_results.py` - Enter game results, updates ledger
- `weekly_summary.py` - Friday report with W-L record, P&L, ROI, best/worst legs
- `post_telegram.py` - Telegram notifications to Rick (6313996149)
- `ledger.json` - All-time bet history and summary stats
- `parlays/` - Daily parlay JSONs by agent

## Cron Jobs

```
# Daily 8 AM ET - run agents
0 8 * * * cd ~/dev/parlay_tracker && .venv/bin/python scrape_lines.py && .venv/bin/python run_agent.py

# Friday 8 AM ET - weekly summary
0 8 * * 5 cd ~/dev/parlay_tracker && .venv/bin/python weekly_summary.py
```

## Adding Results

After games complete:

```bash
python update_results.py
```

The script prompts for W/L/P on each leg of each unprocessed parlay.

## Tracking

- `ledger.json` keeps all-time record
- Per-agent stats: W-L-P, net profit, ROI%
- Individual legs tracked for best/worst weekly picks
