import os
import json
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

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


def get_supabase_client():
    """Return a minimal Supabase-like client for queries (used by odds_etl)."""
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        return None
    
    class SupabaseTable:
        def __init__(self, table_name: str):
            self.table_name = table_name
            self.url = f"{SUPABASE_URL}/rest/v1/{table_name}"
        
        def insert(self, rows: List[Dict[str, Any]], upsert: bool = False):
            headers = _headers()
            headers.pop("Prefer", None)
            headers["Prefer"] = "return=representation"
            # For upsert, we need to use on_conflict parameter
            url = self.url
            if upsert:
                # Assuming conflict on (team_abbr, game_date)
                url = f"{url}?on_conflict=team_abbr,game_date"
            resp = requests.post(url, headers=headers, json=rows, timeout=10)
            resp.raise_for_status()
            
            # Return an object that has an execute() method
            class InsertResponse:
                def __init__(self, data):
                    self.data = data
                def execute(self):
                    return self
            
            return InsertResponse(resp.json())
        
        def select(self, cols: str = "*"):
            return SupabaseQuery(self.url, cols)
    
    class SupabaseQuery:
        def __init__(self, url: str, cols: str):
            self.url = url
            self.params = {"select": cols}
        
        def eq(self, col: str, val: Any):
            self.params[col] = f"eq.{val}"
            return self
        
        def order(self, col: str, desc: bool = False):
            self.params["order"] = f"{col}.{'desc' if desc else 'asc'}"
            return self
        
        def limit(self, n: int):
            self.params["limit"] = n
            return self
        
        def execute(self):
            resp = requests.get(self.url, headers=_headers(), params=self.params, timeout=10)
            resp.raise_for_status()
            return type('Resp', (), {'data': resp.json()})()
    
    class SupabaseClient:
        def table(self, name: str):
            return SupabaseTable(name)
    
    return SupabaseClient()
