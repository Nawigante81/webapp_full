import os
from typing import Any, Dict, Optional
from clients import get_client, fetch

BASE = "https://api.balldontlie.io/v1"
KEY = os.getenv("BALLDONTLIE_API_KEY")
HEAD = {"Authorization": KEY} if KEY else None


def team_lookup(slug_or_abbr: str) -> Optional[Dict[str, Any]]:
    c = get_client()
    data = fetch(c, f"{BASE}/teams", params={"search": slug_or_abbr}, headers=HEAD)
    items = data.get("data", []) if isinstance(data, dict) else []
    return items[0] if items else None


def games_by_team(team_id: int, season: Optional[int] = None, per_page: int = 25) -> Dict[str, Any]:
    c = get_client()
    params: Dict[str, Any] = {"team_ids[]": team_id, "per_page": per_page}
    if season:
        params["seasons[]"] = season
    return fetch(c, f"{BASE}/games", params=params, headers=HEAD)


def boxscore(game_id: int) -> Dict[str, Any]:
    c = get_client()
    return fetch(c, f"{BASE}/stats", params={"game_ids[]": game_id, "per_page": 100}, headers=HEAD)


def injuries_by_team(team_id: int, per_page: int = 100) -> Dict[str, Any]:
    c = get_client()
    return fetch(c, f"{BASE}/player_injuries", params={"team_ids[]": team_id, "per_page": per_page}, headers=HEAD)
