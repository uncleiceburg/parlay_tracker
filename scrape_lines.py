#!/usr/bin/env python3
"""Multi-book NBA line scraper for DraftKings, FanDuel, BetMGM."""
import json
import re
import sys
import requests
from datetime import datetime
from pathlib import Path

# NBA games for March 22-23, 2026
GAMES = [
    {"id": "33847567", "away": "POR Trail Blazers", "home": "DEN Nuggets",
     "time": "Today 9:10 PM ET"},
    {"id": "33847580", "away": "BKN Nets", "home": "SAC Kings",
     "time": "Today 10:10 PM ET"},
    {"id": "33847582", "away": "WAS Wizards", "home": "NY Knicks",
     "time": "Today 11:40 PM ET"},
    {"id": "33847583", "away": "MIN Timberwolves", "home": "BOS Celtics",
     "time": "Tomorrow 12:10 AM ET"},
    {"id": "33847584", "away": "TOR Raptors", "home": "PHO Suns",
     "time": "Tomorrow 1:10 AM ET"},
]

DRAFTKINGS_API = "https://sportsbook.draftkings.com/api/sports/v1/events"
OUTPUT_FILE = Path(__file__).parent / "todays_lines.json"


def scrape_draftkings_api():
    """Try DraftKings internal API first."""
    try:
        url = f"{DRAFTKINGS_API}?category=basketball&league=nba"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200 and "application/json" in resp.headers.get("Content-Type", ""):
            return resp.json()
    except Exception as e:
        print(f"DraftKings API failed: {e}", file=sys.stderr)
    return None


def parse_american_odds(odds_str):
    """Convert American odds to decimal."""
    try:
        odds_str = str(odds_str).strip()
        # Remove non-numeric except + and -
        match = re.search(r'[+-]?\d+', odds_str)
        if not match:
            return None
        odds = int(match.group())
        if odds > 0:
            return round(odds / 100 + 1, 3)
        else:
            return round(100 / abs(odds) + 1, 3)
    except:
        return None


def format_leg(pick):
    """Format a pick nicely."""
    return f"{pick['team']} {pick['line']} ({pick['odds_american']})"


def main():
    result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "scraped_at": datetime.now().isoformat(),
        "books": {},
        "games": []
    }

    # Try DraftKings API
    dk_data = scrape_draftkings_api()
    if dk_data:
        print("Got DraftKings data via API", file=sys.stderr)
        result["books"]["draftkings"] = {"source": "api", "data": dk_data}

    # For each game, build structured lines
    for game in GAMES:
        game_lines = {
            "game_id": game["id"],
            "away": game["away"],
            "home": game["home"],
            "time": game["time"],
            "spread": [],
            "total": [],
            "moneyline": []
        }

        # If we have DK API data, parse it
        if dk_data:
            try:
                events = dk_data.get("events", [])
                for event in events:
                    if str(event.get("id")) == game["id"]:
                        # Look for offerings/bets
                        for offer in event.get("offerCategories", []):
                            if offer.get("name") == "Game Lines":
                                for sub in offer.get("offerSubcategoryDescriptors", []):
                                    market = sub.get("name", "")
                                    for bet in sub.get("outcomes", []):
                                        line_data = {
                                            "team": bet.get("teamName", ""),
                                            "line": bet.get("line", ""),
                                            "odds_american": bet.get("oddsAmerican", ""),
                                            "odds_decimal": parse_american_odds(bet.get("oddsAmerican", "")),
                                        }
                                        if "spread" in market.lower():
                                            game_lines["spread"].append(line_data)
                                        elif "total" in market.lower():
                                            game_lines["total"].append(line_data)
                                        elif "money" in market.lower():
                                            game_lines["moneyline"].append(line_data)
            except Exception as e:
                print(f"Error parsing DK API for game {game['id']}: {e}", file=sys.stderr)

        result["games"].append(game_lines)

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Written to {OUTPUT_FILE}", file=sys.stderr)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
