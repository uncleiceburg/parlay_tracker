#!/usr/bin/env python3
"""Update ledger with game results after they complete."""
import json
import sys
from datetime import datetime
from pathlib import Path

LEDGER_FILE = Path(__file__).parent / "ledger.json"
PARLAYS_DIR = Path(__file__).parent / "parlays"

BASE_BET = 10

MARKET_EMOJI = {"spread": "🎯", "total": "📊", "moneyline": "💰"}


def load_ledger():
    """Load the ledger file."""
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE) as f:
            return json.load(f)
    return {
        "bets": [],
        "summary": {
            "total_bets": 0, "wins": 0, "losses": 0, "pushes": 0, "net_profit": 0,
            "by_agent": {
                "sharp": {"bets": 0, "wins": 0, "losses": 0, "net": 0},
                "public": {"bets": 0, "wins": 0, "losses": 0, "net": 0},
                "model": {"bets": 0, "wins": 0, "losses": 0, "net": 0}
            }
        }
    }


def save_ledger(ledger):
    """Save the ledger file."""
    with open(LEDGER_FILE, "w") as f:
        json.dump(ledger, f, indent=2)


def update_summary(ledger, agent, result, payout, profit):
    """Update summary stats."""
    s = ledger["summary"]
    s["total_bets"] += 1
    s["by_agent"][agent]["bets"] += 1

    if result == "WIN":
        s["wins"] += 1
        s["by_agent"][agent]["wins"] += 1
        s["net_profit"] += profit
        s["by_agent"][agent]["net"] += profit
    elif result == "LOSS":
        s["losses"] += 1
        s["by_agent"][agent]["losses"] += 1
        s["net_profit"] += profit
        s["by_agent"][agent]["net"] += profit
    else:  # PUSH
        s["pushes"] += 1
        s["by_agent"][agent]["net"] += 0


def get_unprocessed_parlays():
    """Get parlay files that haven't been processed yet."""
    processed = set()
    ledger = load_ledger()
    for bet in ledger.get("bets", []):
        processed.add(f"{bet['date']}_{bet['agent']}")

    parlays = []
    for f in sorted(PARLAYS_DIR.glob("*_*.json")):
        # Skip "all" combined files
        if "_all.json" in f.name:
            continue
        # Check if already processed
        parts = f.stem.split("_")
        if len(parts) >= 2:
            date = parts[0]
            agent = parts[1]
            if f"{date}_{agent}" not in processed:
                parlays.append(f)
    return parlays


def prompt_results(parlay_file):
    """Prompt user for results of each leg."""
    with open(parlay_file) as f:
        parlay = json.load(f)

    print(f"\n=== {parlay['agent'].upper()} Parlay ===")
    legs = parlay.get("legs", [])
    for i, leg in enumerate(legs):
        print(f"  {i+1}. {leg.get('team', 'N/A')} {leg.get('line', '')} @ {leg.get('odds_american', 'N/A')}")

    results = []
    for i, leg in enumerate(legs):
        while True:
            r = input(f"Leg {i+1} result (W/L/P for Win/Loss/Push): ").strip().upper()
            if r in ["W", "L", "P"]:
                results.append(r)
                break
            print("  Enter W, L, or P")

    return results


def main():
    # Get unprocessed parlays
    parlays = get_unprocessed_parlays()

    if not parlays:
        print("No unprocessed parlays found.")
        print("Place new parlay files in parlays/ directory with format YYYY-MM-DD_agent.json")
        sys.exit(0)

    print(f"Found {len(parlays)} unprocessed parlay(s)")

    ledger = load_ledger()

    for parlay_file in parlays:
        with open(parlay_file) as f:
            parlay = json.load(f)

        date = parlay_file.stem.split("_")[0]
        agent = parlay_file.stem.split("_")[1]

        print(f"\nProcessing: {date} - {agent}")

        # Prompt for results
        results = prompt_results(parlay_file)

        legs = parlay.get("legs", [])
        all_wins = all(r == "W" for r in results)
        all_pushes = all(r == "P" for r in results)
        any_loss = any(r == "L" for r in results)

        if all_wins:
            result = "WIN"
            payout = parlay.get("payout", BASE_BET * 2.5)
            profit = payout - BASE_BET
        elif any_loss or all_pushes:
            result = "LOSS" if any_loss else "PUSH"
            payout = BASE_BET if any_loss else BASE_BET  # Push returns bet
            profit = -BASE_BET if any_loss else 0
        else:
            # Partial win
            win_count = sum(1 for r in results if r == "W")
            result = f"PARTIAL ({win_count}/{len(results)})"
            payout = round(BASE_BET * (win_count / len(results)), 2)
            profit = payout - BASE_BET

        # Record bet
        bet_record = {
            "date": date,
            "agent": agent,
            "legs": [{"pick": leg.get("team", ""), "line": leg.get("line", ""),
                      "odds": leg.get("odds_american", ""), "result": r}
                     for leg, r in zip(legs, results)],
            "result": result,
            "payout": payout,
            "profit": profit,
            "bet": BASE_BET
        }
        ledger["bets"].append(bet_record)

        # Update summary
        update_summary(ledger, agent, result, payout, profit)

        print(f"  Result: {result} | Payout: ${payout:.2f} | Profit: ${profit:.2f}")

    save_ledger(ledger)
    print(f"\nLedger updated and saved to {LEDGER_FILE}")
    print(f"Summary: {ledger['summary']['total_bets']} bets, "
          f"{ledger['summary']['wins']}W-{ledger['summary']['losses']}L-{ledger['summary']['pushes']}P, "
          f"Net: ${ledger['summary']['net_profit']:.2f}")


if __name__ == "__main__":
    main()
