import os
import json
from typing import Any, Dict, List, Optional
import requests


SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


def _headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Prefer": "return=minimal",
    }


def rest_post(table: str, rows: List[Dict[str, Any]], on_conflict: Optional[str] = None) -> None:
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        return
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if on_conflict:
        url = f"{url}?on_conflict={on_conflict}"
    try:
        requests.post(url, headers=_headers(), data=json.dumps(rows), timeout=10)
    except requests.exceptions.RequestException:
        pass


def insert_teams(teams: List[Dict[str, Any]]) -> None:
    rest_post("teams", teams, on_conflict="id")


def insert_games(games: List[Dict[str, Any]]) -> None:
    rest_post("games", games, on_conflict="id")


def insert_injuries(injuries: List[Dict[str, Any]]) -> None:
    # Upsert on (player_id, reported_at) if you add a unique constraint; otherwise simple insert
    rest_post("injuries", injuries)


def insert_odds(odds_rows: List[Dict[str, Any]]) -> None:
    # If you add a unique key on id, you can use on_conflict="id"
    rest_post("odds", odds_rows)
