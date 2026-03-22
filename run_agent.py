#!/usr/bin/env python3
"""Run all 3 betting agents and generate parlays."""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Load the LLM caller - use the hermes agent directly
# For now, simulate with structured prompts

LINES_FILE = Path(__file__).parent / "todays_lines.json"
PARLAYS_DIR = Path(__file__).parent / "parlays"
PARLAYS_DIR.mkdir(exist_ok=True)

BASE_BET = 10

AGENTS = {
    "sharp": {
        "name": "The Sharp",
        "style": "contrarian",
        "prefers": "underdogs, overs, +EV plays",
        "description": "Sharp bettor who fades public consensus. Looks for +EV on underdogs and overs."
    },
    "public": {
        "name": "The Public",
        "style": "recreational",
        "prefers": "favorites, consensus picks",
        "description": "Recreational bettor who follows public consensus. Backs favorites and popular overs."
    },
    "model": {
        "name": "The Model",
        "style": "quantitative",
        "prefers": "pace-adjusted, defensive ratings, net rating splits",
        "description": "Data-driven model using pace, defensive ratings, and net rating splits."
    }
}


def load_lines():
    """Load today's lines."""
    if not LINES_FILE.exists():
        print(f"Error: {LINES_FILE} not found. Run scrape_lines.py first.", file=sys.stderr)
        sys.exit(1)
    with open(LINES_FILE) as f:
        return json.load(f)


def american_to_decimal(odds):
    """Convert American odds to decimal."""
    try:
        odds = int(odds)
        if odds > 0:
            return round(odds / 100 + 1, 3)
        else:
            return round(100 / abs(odds) + 1, 3)
    except:
        return None


def calculate_payout(legs, bet=10):
    """Calculate parlay payout from legs."""
    total_odds = 1.0
    for leg in legs:
        if leg.get("odds_decimal"):
            total_odds *= leg["odds_decimal"]
    return round(bet * total_odds, 2)


def format_pick(leg):
    """Format a pick for display."""
    return f"{leg['team']} {leg['line']} ({leg['odds_american']})"


def generate_parlay(agent_key, agent_info, lines_data):
    """Generate a 5-leg parlay for an agent."""
    games = lines_data.get("games", [])

    # Build prompt
    prompt = f"""You are {agent_info['name']}, a {agent_info['style']} sports bettor.
{agent_info['description']}

Today's NBA games and lines:
"""
    for g in games:
        prompt += f"\n{g['away']} @ {g['home']} ({g['time']})\n"
        for market in ["spread", "total", "moneyline"]:
            if g.get(market):
                for line in g[market]:
                    prompt += f"  {market.upper()}: {line['team']} {line.get('line', '')} @ {line.get('odds_american', 'N/A')}\n"

    prompt += f"""
Pick exactly 5 legs for a parlay. Choose based on your betting style.
Return ONLY valid JSON (no markdown, no explanation):
{{
  "agent": "{agent_key}",
  "legs": [
    {{"team": "team name", "line": "spread/total line", "odds_american": "+120", "market": "spread/total/moneyline", "reasoning": "brief reason"}}
  ],
  "reasoning": "overall parlay reasoning"
}}
"""

    return prompt


def call_llm(prompt):
    """Call the LLM. In cron context, this uses the hermes session."""
    try:
        from anthropic import Anthropic
        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        print(f"LLM call failed: {e}", file=sys.stderr)
        # Fallback: return sample data
        return None


def parse_llm_response(text):
    """Parse LLM JSON response."""
    if not text:
        return None
    # Try to extract JSON
    try:
        # Find JSON block
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
    return None


def create_sample_parlay(agent_key, lines_data):
    """Create a sample parlay when LLM isn't available."""
    games = lines_data.get("games", [])
    legs = []
    markets = ["spread", "spread", "total", "moneyline", "total"]

    import random
    random.seed(42)

    for i, market in enumerate(markets[:len(games)]):
        g = games[i % len(games)]
        if g.get(market):
            line = g[market][0]
            legs.append({
                "team": line["team"],
                "line": str(line.get("line", "")),
                "odds_american": str(line.get("odds_american", "+100")),
                "odds_decimal": line.get("odds_decimal", 2.0),
                "market": market,
                "game_id": g["game_id"],
                "reasoning": f"{AGENTS[agent_key]['name']} pick"
            })

    return {
        "agent": agent_key,
        "legs": legs,
        "reasoning": f"Sample parlay from {AGENTS[agent_key]['name']}",
        "is_sample": True
    }


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    lines_data = load_lines()

    print(f"Running agents for {today}", file=sys.stderr)
    print(f"Loaded {len(lines_data.get('games', []))} games", file=sys.stderr)

    parlays = {}
    for agent_key, agent_info in AGENTS.items():
        print(f"\n=== {agent_info['name']} ===", file=sys.stderr)

        prompt = generate_parlay(agent_key, agent_info, lines_data)
        response = call_llm(prompt)
        data = parse_llm_response(response)

        if not data or "legs" not in data:
            print(f"  Using sample data for {agent_key}", file=sys.stderr)
            data = create_sample_parlay(agent_key, lines_data)
        else:
            # Add decimal odds
            for leg in data.get("legs", []):
                if "odds_decimal" not in leg:
                    leg["odds_decimal"] = american_to_decimal(leg.get("odds_american", "+100"))

        # Calculate payout
        payout = calculate_payout(data.get("legs", []))
        data["payout"] = payout
        data["bet"] = BASE_BET
        data["profit"] = round(payout - BASE_BET, 2) if payout > 0 else -BASE_BET

        parlays[agent_key] = data

        # Save individual parlay
        out_file = PARLAYS_DIR / f"{today}_{agent_key}.json"
        with open(out_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Saved: {out_file}", file=sys.stderr)

        # Print summary
        print(f"  Legs:", file=sys.stderr)
        for leg in data.get("legs", []):
            print(f"    - {format_pick(leg)}", file=sys.stderr)
        print(f"  Odds: {payout/BASE_BET:.2f}x | Payout: ${payout:.2f}", file=sys.stderr)

    # Save combined
    combined_file = PARLAYS_DIR / f"{today}_all.json"
    with open(combined_file, "w") as f:
        json.dump(parlays, f, indent=2)

    print(f"\nAll parlays saved to {PARLAYS_DIR}", file=sys.stderr)

    # Post to Telegram
    try:
        import post_telegram
        for agent_key, data in parlays.items():
            msg = f"*{AGENTS[agent_key]['name']} Parlay ({today})*\n"
            for leg in data.get("legs", []):
                msg += f"• {format_pick(leg)}\n"
            msg += f"\nOdds: {data['payout']/BASE_BET:.2f}x | Bet: ${BASE_BET} | To Win: ${data['profit']:.2f}"
            post_telegram.send_message(msg)
    except Exception as e:
        print(f"Telegram post failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
