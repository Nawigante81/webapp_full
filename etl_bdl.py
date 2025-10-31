"""
ETL pipeline for BallDontLie + The Odds API into Supabase.

Usage examples:
  python etl_bdl.py --team CHI
  python etl_bdl.py --teams CHI,BOS,LAL --season 2025
"""
import argparse
import hashlib
import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv

from bdl import team_lookup, games_by_team, injuries_by_team
from odds_api import current_odds, find_odds_for_matchup
from supabase_client import insert_teams, insert_games, insert_injuries, insert_odds


def _as_team_row(team: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": team.get("id"),
        "abbreviation": team.get("abbreviation"),
        "full_name": team.get("full_name") or team.get("name"),
        "city": team.get("city"),
        "division": team.get("division"),
        "conference": team.get("conference"),
    }


def _as_game_rows(games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for g in games:
        rows.append(
            {
                "id": g.get("id"),
                "season": g.get("season"),
                "game_date": g.get("date"),
                "status": g.get("status"),
                "home_team_id": (g.get("home_team") or {}).get("id"),
                "visitor_team_id": (g.get("visitor_team") or {}).get("id"),
                "home_team_score": g.get("home_team_score"),
                "visitor_team_score": g.get("visitor_team_score"),
            }
        )
    return rows


def _as_injury_rows(injuries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for it in injuries:
        player = it.get("player") or {}
        team = it.get("team") or {}
        rows.append(
            {
                "player_id": player.get("id"),
                "team_id": team.get("id"),
                "status": it.get("status") or it.get("designation"),
                "description": it.get("description"),
                "reported_at": it.get("updated_at") or it.get("start_date"),
            }
        )
    return rows


def _event_id(ev: Dict[str, Any]) -> str:
    # Prefer id from API; else derive a stable hash from teams + commence_time
    ev_id = ev.get("id")
    if ev_id:
        return str(ev_id)
    basis = json.dumps({
        "home": ev.get("home_team"),
        "away": ev.get("away_team"),
        "t": ev.get("commence_time"),
    }, sort_keys=True)
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()


def _as_odds_rows(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for ev in events:
        rows.append(
            {
                "id": _event_id(ev),
                "sport_key": ev.get("sport_key"),
                "commence_time": ev.get("commence_time"),
                "home_team": ev.get("home_team"),
                "away_team": ev.get("away_team"),
                "markets": ev.get("bookmakers"),
                "raw": ev,
            }
        )
    return rows


def run_for_team(team_query: str, season: int) -> None:
    team = team_lookup(team_query)
    if not team:
        print(f"Team not found: {team_query}")
        return
    insert_teams([_as_team_row(team)])

    games = (games_by_team(team.get("id"), season=season) or {}).get("data", [])
    insert_games(_as_game_rows(games))

    injuries = (injuries_by_team(team.get("id")) or {}).get("data", [])
    if injuries:
        insert_injuries(_as_injury_rows(injuries))

    try:
        events = current_odds()
    except Exception:
        events = []
    names = [team.get("full_name"), team.get("name"), team.get("abbreviation"), team.get("city")]
    selected = find_odds_for_matchup(events, [n for n in names if n])
    if selected:
        insert_odds(_as_odds_rows(selected))


def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--team", help="Single team query (abbr/name)")
    parser.add_argument("--teams", help="Comma-separated list of team queries")
    parser.add_argument("--season", type=int, default=int(os.getenv("DEFAULT_NBA_SEASON", "2025")))
    args = parser.parse_args()

    teams: List[str] = []
    if args.team:
        teams = [args.team]
    elif args.teams:
        teams = [t.strip() for t in args.teams.split(",") if t.strip()]
    else:
        print("Provide --team or --teams")
        return

    for t in teams:
        run_for_team(t, season=args.season)


if __name__ == "__main__":
    main()
