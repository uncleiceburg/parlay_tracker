#!/usr/bin/env python3
"""Generate weekly Friday summary for Parlay Tracker."""
import json
from datetime import datetime
from pathlib import Path

LEDGER_FILE = Path(__file__).parent / "ledger.json"
POST_FILE = Path(__file__).parent / "weekly_summary.txt"

AGENTS = {
    "sharp": "The Sharp",
    "public": "The Public",
    "model": "The Model"
}


def load_ledger():
    """Load the ledger file."""
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE) as f:
            return json.load(f)
    return {"bets": [], "summary": {}}


def calculate_week_stats(ledger, agent):
    """Calculate stats for a specific agent this week."""
    bets = [b for b in ledger.get("bets", []) if b["agent"] == agent]
    if not bets:
        return None

    wins = sum(1 for b in bets if b["result"] == "WIN")
    losses = sum(1 for b in bets if b["result"] == "LOSS")
    pushes = sum(1 for b in bets if b["result"] == "PUSH")
    total = wins + losses + pushes
    net = sum(b["profit"] for b in bets)
    roi = (net / (total * 10)) * 100 if total > 0 else 0

    # Track individual legs for best/worst
    all_legs = []
    for bet in bets:
        for leg in bet.get("legs", []):
            all_legs.append({
                "date": bet["date"],
                "agent": agent,
                "pick": leg["pick"],
                "line": leg.get("line", ""),
                "odds": leg.get("odds", ""),
                "result": leg["result"],
                "profit": 10 * (2.0 if leg["result"] == "WIN" else -1 if leg["result"] == "LOSS" else 0)
            })

    return {
        "bets": total,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "net": net,
        "roi": roi,
        "legs": all_legs
    }


def find_best_worst_legs(legs):
    """Find best and worst individual legs."""
    if not legs:
        return None, None

    winning_legs = [l for l in legs if l["result"] == "WIN"]
    losing_legs = [l for l in legs if l["result"] == "LOSS"]

    # Best leg = highest odds winner
    best = None
    if winning_legs:
        for leg in winning_legs:
            try:
                odds = int(leg.get("odds", "+100").replace("+", ""))
                if best is None or odds > int(best.get("odds", "+100").replace("+", "")):
                    best = leg
            except:
                pass
        if best is None:
            best = winning_legs[0]

    # Worst leg = biggest favorite that lost
    worst = None
    if losing_legs:
        for leg in losing_legs:
            try:
                odds = int(leg.get("odds", "+100").replace("+", ""))
                if worst is None or odds < int(worst.get("odds", "+100").replace("+", "")):
                    worst = leg
            except:
                pass
        if worst is None:
            worst = losing_legs[0]

    return best, worst


def generate_summary():
    """Generate the weekly summary message."""
    ledger = load_ledger()
    week_start = datetime.now().strftime("%Y-%m-%d")

    lines = []
    lines.append("📊 PARLAY TRACKER WEEKLY REPORT")
    lines.append("=" * 35)
    lines.append(f"Week of {week_start}")
    lines.append("")

    all_best_legs = []
    all_worst_legs = []

    for agent_key, agent_name in AGENTS.items():
        stats = calculate_week_stats(ledger, agent_key)
        if not stats:
            lines.append(f"{agent_name}: No bets this week")
            lines.append("")
            continue

        record = f"{stats['wins']}W-{stats['losses']}L-{stats['pushes']}P"
        roi_sign = "+" if stats['roi'] >= 0 else ""
        net_sign = "+" if stats['net'] >= 0 else ""

        lines.append(f"{agent_name}")
        lines.append(f"  Record: {record}")
        lines.append(f"  Net: {net_sign}${stats['net']:.2f}")
        lines.append(f"  ROI: {roi_sign}{stats['roi']:.1f}%")
        lines.append("")

        best, worst = find_best_worst_legs(stats.get("legs", []))
        if best:
            all_best_legs.append(best)
        if worst:
            all_worst_legs.append(worst)

    # Best leg of week
    if all_best_legs:
        best_leg = max(all_best_legs, key=lambda x: abs(int(x.get("odds", "+100").replace("+", ""))))
        lines.append("🏆 Best Leg of Week:")
        lines.append(f"  {best_leg['pick']} {best_leg.get('line', '')} @ {best_leg.get('odds', '')}")

    # Worst leg of week
    if all_worst_legs:
        worst_leg = min(all_worst_legs, key=lambda x: abs(int(x.get("odds", "+100").replace("+", ""))))
        lines.append("💀 Worst Leg of Week:")
        lines.append(f"  {worst_leg['pick']} {worst_leg.get('line', '')} @ {worst_leg.get('odds', '')}")

    lines.append("")
    lines.append("-" * 35)
    lines.append("Recommended Base Bet: $10")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(lines)


def main():
    summary = generate_summary()
    print(summary)

    # Save to file
    with open(POST_FILE, "w") as f:
        f.write(summary)
    print(f"\nSaved to {POST_FILE}")

    # Post to Telegram
    try:
        from post_telegram import send_message, CHAT_ID
        # Send as multiple messages if too long
        for i in range(0, len(summary), 4096):
            chunk = summary[i:i+4096]
            send_message(chunk)
    except Exception as e:
        print(f"Telegram post failed: {e}")


if __name__ == "__main__":
    main()
