#!/usr/bin/env python3
"""Extract NBA game lines from DraftKings using Playwright."""
import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright


async def extract_game_lines(event_url: str, game_id: str) -> dict:
    """Extract game lines from a DraftKings event page."""
    result = {"game_id": game_id, "url": event_url, "lines": {}}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Go to game lines subpage
        game_lines_url = f"{event_url}?category=all-odds&subcategory=game-lines"
        await page.goto(game_lines_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)  # Wait for JS to render

        # Extract all buttons (these contain the odds)
        buttons = await page.query_selector_all("button")
        for btn in buttons:
            text = await btn.inner_text()
            if any(c in text for c in ["−", "+", "O ", "U ", "−"]):
                # Get the label/category from parent elements
                result["lines"][text.strip()] = text.strip()

        # Try to find specific betting markets
        try:
            # Look for spread, total, moneyline sections
            elements = await page.query_selector_all("[class*='odds'], [class*='market'], [class*='line']")
            for el in elements:
                text = await el.inner_text()
                if text and len(text) < 50:
                    if any(c in text for c in ["−", "+", "O", "U"]) and not text.startswith("{"):
                        result["lines"][text.strip()] = text.strip()
        except Exception:
            pass

        await browser.close()

    return result


async def main():
    # NBA games for March 22, 2026
    games = [
        {"id": "33847567", "away": "POR Trail Blazers", "home": "DEN Nuggets",
         "url": "https://sportsbook.draftkings.com/event/por-trail-blazers-%40-den-nuggets/33847567"},
        {"id": "33847580", "away": "BKN Nets", "home": "SAC Kings",
         "url": "https://sportsbook.draftkings.com/event/bkn-nets-%40-sac-kings/33847580"},
        {"id": "33847582", "away": "WAS Wizards", "home": "NY Knicks",
         "url": "https://sportsbook.draftkings.com/event/was-wizards-%40-ny-knicks/33847582"},
        {"id": "33847583", "away": "MIN Timberwolves", "home": "BOS Celtics",
         "url": "https://sportsbook.draftkings.com/event/min-timberwolves-%40-bos-celtics/33847583"},
        {"id": "33847584", "away": "TOR Raptors", "home": "PHO Suns",
         "url": "https://sportsbook.draftkings.com/event/tor-raptors-%40-pho-suns/33847584"},
    ]

    all_results = []
    for game in games:
        print(f"Extracting: {game['away']} @ {game['home']}...", file=sys.stderr)
        try:
            data = await extract_game_lines(game["url"], game["id"])
            data["away"] = game["away"]
            data["home"] = game["home"]
            all_results.append(data)
            print(f"  Found {len(data['lines'])} lines", file=sys.stderr)
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            all_results.append({"game_id": game["id"], "away": game["away"], "home": game["home"], "error": str(e), "lines": {}})

    print(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
