import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from clients import get_client, fetch

load_dotenv()

BASE = "https://api.balldontlie.io/v1"
KEY = os.getenv("BALLDONTLIE_API_KEY")
HEAD = {"Authorization": KEY} if KEY else None


def team_lookup(slug_or_abbr: str) -> Optional[Dict[str, Any]]:
    """Robust team lookup by slug or abbreviation.

    The BDL `search` parameter does substring matching. A query like 'CHA'
    may return "Chicago Bulls" first, which is incorrect for Charlotte.
    We prefer exact abbreviation match when the input is 3 letters; otherwise
    try exact name/full_name match; finally fall back to the first result.
    """
    q = (slug_or_abbr or "").strip()
    if not q:
        return None
    c = get_client()
    data = fetch(c, f"{BASE}/teams", params={"search": q}, headers=HEAD)
    items = data.get("data", []) if isinstance(data, dict) else []
    if not items:
        return None
    # If looks like abbreviation, prefer exact abbr match
    if len(q) == 3 and q.isalpha():
        q_up = q.upper()
        for it in items:
            if (it.get("abbreviation") or "").upper() == q_up:
                return it
    # Try exact full_name or name match (case-insensitive)
    q_low = q.lower()
    for it in items:
        name = (it.get("full_name") or it.get("name") or "").lower()
        if name == q_low:
            return it
    # Fallback: return the first item
    return items[0]


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
    try:
        return fetch(c, f"{BASE}/player_injuries", params={"team_ids[]": team_id, "per_page": per_page}, headers=HEAD)
    except Exception:
        # Return empty injuries if endpoint is not accessible (401 or other errors)
        return {"data": []}
