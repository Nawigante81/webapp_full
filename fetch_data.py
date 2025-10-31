"""
API-first data orchestration; legacy scraping code has been disabled.
"""
 
import time
import logging
import os
import random
from typing import Any
from typing import List, Dict, Optional
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
}
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.142 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12.6; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/125.0.0.0 Chrome/125.0.0.0 Safari/537.36",
]

# Scraping configuration from environment variables
SCRAPING_RATE_LIMIT_CALLS = int(os.getenv("SCRAPING_RATE_LIMIT_CALLS", "5"))
SCRAPING_RATE_LIMIT_PERIOD = int(os.getenv("SCRAPING_RATE_LIMIT_PERIOD", "60"))
SCRAPING_MAX_RETRIES = int(os.getenv("SCRAPING_MAX_RETRIES", "3"))
SCRAPING_BACKOFF_FACTOR = float(os.getenv("SCRAPING_BACKOFF_FACTOR", "1.0"))
SCRAPING_TIMEOUT = int(os.getenv("SCRAPING_TIMEOUT", "15"))

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

"""
API-first routing flags

These env-driven switches allow replacing legacy scraping with API sources
without refactoring the existing callers. Defaults mirror legacy behavior.
"""
# Data source routing flags
DATA_SRC_GAMES = os.getenv("DATA_SOURCE_GAMES", "br").lower()
DATA_SRC_INJ = os.getenv("DATA_SOURCE_INJURIES", "pdf").lower()
DATA_SRC_ODDS = os.getenv("DATA_SOURCE_ODDS", "scrape").lower()

# API clients (strict import – fail fast if missing)
from bdl import team_lookup as bdl_team_lookup, games_by_team as bdl_games_by_team, injuries_by_team as bdl_injuries_by_team
from odds_api import current_odds as odds_current_odds


def _bdl_resolve_team(q: str) -> Dict[str, Any]:
    """Resolve a team by abbreviation or name via BallDontLie, or raise."""
    team = bdl_team_lookup(q)
    if not team:
        raise ValueError(f"Team not found: {q}")
    return team


def get_team_games(team_abbr_or_name: str, limit: int = 25) -> List[Dict[str, Any]]:
    """Return team games via BallDontLie only. Legacy scraping disabled."""
    if os.getenv("DATA_SOURCE_GAMES", "bdl").lower() != "bdl":
        raise RuntimeError("Legacy BR scraping disabled")
    team = _bdl_resolve_team(team_abbr_or_name)
    season = int(os.getenv("DEFAULT_NBA_SEASON", "2025"))
    data = bdl_games_by_team(team.get("id"), season=season, per_page=limit)
    return (data or {}).get("data", [])


def get_team_injuries(team_abbr_or_name: str) -> List[Dict[str, Any]]:
    """Return team injuries via BallDontLie only. Legacy NBA PDF disabled."""
    if os.getenv("DATA_SOURCE_INJURIES", "bdl").lower() != "bdl":
        raise RuntimeError("Legacy NBA PDF injuries disabled")
    team = _bdl_resolve_team(team_abbr_or_name)
    data = bdl_injuries_by_team(team.get("id"))
    return (data or {}).get("data", [])


def get_odds_for_games() -> List[Dict[str, Any]]:
    """Return odds from The Odds API only when enabled; else []."""
    if os.getenv("DATA_SOURCE_ODDS", "the_odds_api").lower() != "the_odds_api":
        return []
    data = odds_current_odds()
    return data if isinstance(data, list) else []


# --- Safety guards: block legacy scraping calls ---
def _br_fetch_team_games(*args, **kwargs):
    raise RuntimeError("Basketball-Reference scraping removed. Use BallDontLie.")


def _pdf_injury_fetch(*args, **kwargs):
    raise RuntimeError("NBA PDF injuries removed. Use BallDontLie injuries.")

# legacy header builder removed (scraping disabled)

# Rate limiting with configurable parameters
 # legacy request helper removed (scraping disabled)


# legacy BR parsing helpers removed (scraping disabled)


 # legacy BR parsing helpers removed (scraping disabled)


def get_team_game_results_br(*args, **kwargs):
    raise RuntimeError("Basketball-Reference scraping removed. Use BallDontLie.")

def _season_to_nba_format(end_year: int) -> str:
    """Convert season end year to NBA API format, e.g., 2025 -> '2024-25'."""
    start = end_year - 1
    return f"{start}-{str(end_year)[-2:]}"

def get_team_game_results_nba_api(*args, **kwargs):
    raise RuntimeError("nba_api path disabled in API-first mode. Use BallDontLie.")

def get_team_game_results(*args, **kwargs):
    raise RuntimeError("Legacy dispatcher disabled. Use get_team_games (BallDontLie).")


def get_team_game_results_api_nba(*args, **kwargs) -> List[Dict[str, str]]:
    raise RuntimeError("RapidAPI API-NBA path disabled in API-first mode. Use BallDontLie.")

def _safe_int(val: Any) -> Optional[int]:
    """Safely cast to int, returning None on invalid/missing."""
    try:
        return int(val) if val is not None and val != "" else None
    except Exception:
        return None

def get_player_statistics_api_nba(game_id: str | int) -> List[Dict[str, Any]]:
    """Fetch per-player statistics for a specific game using API-NBA via RapidAPI.

    Args:
        game_id: API-NBA game identifier (e.g., 8133)

    Returns:
        A list of player stat dicts with normalized keys when possible.
    """
    key = os.getenv("RAPIDAPI_KEY")
    host = os.getenv("RAPIDAPI_HOST", "api-nba-v1.p.rapidapi.com")
    if not key:
        logger.error("RAPIDAPI_KEY not set; cannot use API-NBA player stats")
        return []

    headers = {
        "x-rapidapi-key": key,
        "x-rapidapi-host": host,
    }

    url = f"https://{host}/players/statistics"
    params = {"game": str(game_id)}

    max_retries = SCRAPING_MAX_RETRIES
    backoff = SCRAPING_BACKOFF_FACTOR
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=SCRAPING_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("response") or []
            normalized: List[Dict[str, Any]] = []
            for it in items:
                player = it.get("player") or {}
                team = it.get("team") or {}
                stats = it.get("statistics") or it  # some responses embed stats at top-level
                # Normalize key fields if present
                full_name = (
                    (player.get("firstname") or "").strip() + " " + (player.get("lastname") or "").strip()
                ).strip() or player.get("name") or ""
                norm = {
                    "player_id": player.get("id"),
                    "player": full_name,
                    "team": team.get("code") or team.get("name") or team.get("nickname"),
                    "minutes": stats.get("min") or stats.get("minutes"),
                    "points": _safe_int(stats.get("points")),
                    "rebounds": _safe_int(stats.get("totReb") or stats.get("rebounds")),
                    "assists": _safe_int(stats.get("assists")),
                    "steals": _safe_int(stats.get("steals")),
                    "blocks": _safe_int(stats.get("blocks")),
                    "turnovers": _safe_int(stats.get("turnovers")),
                    "fgm": _safe_int(stats.get("fgm")),
                    "fga": _safe_int(stats.get("fga")),
                    "tpm": _safe_int(stats.get("tpm") or stats.get("threePointsMade")),
                    "tpa": _safe_int(stats.get("tpa") or stats.get("threePointsAttempted")),
                    "ftm": _safe_int(stats.get("ftm")),
                    "fta": _safe_int(stats.get("fta")),
                    "plus_minus": _safe_int(stats.get("plusMinus") or stats.get("plusminus")),
                }
                normalized.append(norm)
            return normalized
        except requests.exceptions.RequestException as e:
            if attempt >= max_retries:
                logger.error(f"API-NBA player stats failed for game {game_id}: {e}")
                return []
            sleep_time = (backoff ** attempt) + random.uniform(0, 0.5)
            logger.warning(
                f"API-NBA player stats error (attempt {attempt+1}/{max_retries+1}) for game {game_id}: {e}. Retrying in {sleep_time:.2f}s"
            )
            time.sleep(sleep_time)


def get_scores_rapid(fixture_id: str) -> Dict[str, Any]:
    """Fetch game scores via a RapidAPI odds provider.

    Env:
    - ODDS_RAPIDAPI_HOST (e.g., odds-api1.p.rapidapi.com)
    - ODDS_RAPIDAPI_KEY
    """

    host = os.getenv("ODDS_RAPIDAPI_HOST")
    key = os.getenv("ODDS_RAPIDAPI_KEY")
    if not host or not key:
        logger.error("ODDS_RAPIDAPI_HOST/KEY not set; cannot fetch RapidAPI odds scores")
        return {}

    url = f"https://{host}/scores"
    headers = {
        "x-rapidapi-host": host,
        "x-rapidapi-key": key,
    }
    params = {"fixtureId": fixture_id}

    max_retries = SCRAPING_MAX_RETRIES
    backoff = SCRAPING_BACKOFF_FACTOR
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=SCRAPING_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            # Try common shapes: { response: {...} } or list
            payload = data.get("response") if isinstance(data, dict) else data
            if isinstance(payload, list) and payload:
                payload = payload[0]
            if not isinstance(payload, dict):
                return {"fixtureId": fixture_id, "raw": data}
            # Normalize some likely fields if present
            norm = {
                "fixtureId": fixture_id,
                "home": payload.get("home") or (payload.get("teams", {}) or {}).get("home"),
                "away": payload.get("away") or (payload.get("teams", {}) or {}).get("away"),
                "home_score": payload.get("home_score") or (payload.get("scores", {}) or {}).get("home"),
                "away_score": payload.get("away_score") or (payload.get("scores", {}) or {}).get("away"),
                "status": payload.get("status") or (payload.get("game", {}) or {}).get("status"),
                "date": payload.get("date") or (payload.get("game", {}) or {}).get("date"),
            }
            return norm
        except requests.exceptions.RequestException as e:
            if attempt >= max_retries:
                logger.error(f"RapidAPI scores failed for fixture {fixture_id}: {e}")
                return {"fixtureId": fixture_id, "error": str(e)}
            sleep_time = (backoff ** attempt) + random.uniform(0, 0.5)
            logger.warning(
                f"RapidAPI scores error (attempt {attempt+1}/{max_retries+1}) for fixture {fixture_id}: {e}. Retrying in {sleep_time:.2f}s"
            )
            time.sleep(sleep_time)


def get_closing_lines(*args, **kwargs) -> List[Dict[str, str]]:
    raise RuntimeError("VegasInsider scraping removed. Use The Odds API via get_odds_for_games().")


def get_injury_report(*args, **kwargs) -> List[Dict[str, str]]:
    raise RuntimeError("NBA PDF injury report removed. Use BallDontLie via get_team_injuries().")


def assemble_team_report(*args, **kwargs) -> Dict[str, Optional[object]]:
    raise RuntimeError("assemble_team_report deprecated. Use API-first /report endpoint and get_team_games/get_team_injuries/get_odds_for_games().")