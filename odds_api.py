import os
from typing import Any, Dict, List
from clients import get_client, fetch

BASE = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
KEY = os.getenv("ODDS_API_KEY")
REGIONS = os.getenv("ODDS_REGIONS", "eu,us")
MARKETS = os.getenv("ODDS_MARKETS", "h2h,spreads,totals")


def current_odds() -> List[Dict[str, Any]]:
    c = get_client()
    params = {
        "apiKey": KEY or "",
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": "decimal",
    }
    data = fetch(c, BASE, params=params)
    if isinstance(data, list):
        return data
    return []


def find_odds_for_matchup(events: List[Dict[str, Any]], team_names: List[str]) -> List[Dict[str, Any]]:
    """Filter odds events that include any of the provided team name tokens.

    team_names: list like ["Chicago Bulls", "Bulls", "CHI"]
    """
    tokens = [t.lower() for t in team_names if t]
    results: List[Dict[str, Any]] = []
    for ev in events:
        home = (ev.get("home_team") or "").lower()
        away = (ev.get("away_team") or "").lower()
        if any(tok in home or tok in away for tok in tokens):
            results.append(ev)
    return results
