"""
ETL helper to ingest historical odds and game results for ATS/O-U analysis.

This module:
1. Fetches recent games from BallDontLie.
2. Pulls current odds from The Odds API for matching games.
3. Stores lines + results in Supabase (games_odds table).
4. Computes ATS/O-U outcomes when both line and result are available.

Usage:
  python odds_etl.py --team CHI --days 30
"""
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from dotenv import load_dotenv
from bdl import team_lookup as bdl_team_lookup, games_by_team as bdl_games_by_team
from odds_api import current_odds as odds_current_odds
from supabase_client import get_supabase_client

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_spread(outcomes: List[Dict[str, Any]], team_name: str) -> Optional[float]:
    """Extract spread line for a given team from outcomes list."""
    for out in outcomes:
        if out.get('name') and team_name.lower() in out['name'].lower():
            return float(out.get('point', 0))
    return None


def parse_total(outcomes: List[Dict[str, Any]]) -> Optional[float]:
    """Extract total line (over/under) from outcomes."""
    for out in outcomes:
        if 'over' in out.get('name', '').lower():
            return float(out.get('point', 0))
    return None


def compute_ats(team_score: int, opp_score: int, spread: float, is_home: bool) -> str:
    """Compute ATS result: W/L/P.
    
    Spread is from team's perspective (negative if favored).
    """
    margin = team_score - opp_score
    adjusted = margin + spread
    if abs(adjusted) < 0.01:
        return 'P'  # push
    return 'W' if adjusted > 0 else 'L'


def compute_ou(team_score: int, opp_score: int, total: float) -> str:
    """Compute O/U result."""
    actual_total = team_score + opp_score
    diff = actual_total - total
    if abs(diff) < 0.01:
        return 'P'
    return 'O' if diff > 0 else 'U'


def ingest_odds_for_team(team_abbr: str, days: int = 30) -> None:
    """Fetch recent games, match with odds, store in Supabase."""
    sb = get_supabase_client()
    if not sb:
        logger.error("Supabase client not available")
        return

    # 1) Resolve team via BDL
    team = bdl_team_lookup(team_abbr)
    if not team:
        logger.error(f"Team not found: {team_abbr}")
        return
    team_id = team['id']
    team_full_name = team.get('full_name') or team.get('name')
    season = int(os.getenv("DEFAULT_NBA_SEASON", "2025"))

    # 2) Fetch recent games from BDL
    logger.info(f"Fetching games for {team_abbr} (season {season})")
    games_resp = bdl_games_by_team(team_id, season=season, per_page=50)
    games = games_resp.get('data', []) if isinstance(games_resp, dict) else []
    logger.info(f"Found {len(games)} games for {team_abbr}")

    # 3) Fetch current odds from The Odds API (for upcoming or recent)
    logger.info("Fetching odds from The Odds API")
    odds_events = odds_current_odds() or []
    logger.info(f"Found {len(odds_events)} odds events")

    # 4) Match and upsert
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = []
    for g in games:
        try:
            game_date_str = g.get('date') or ''
            if not game_date_str:
                continue
            game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
            if game_date < cutoff:
                continue
            
            home_team = g.get('home_team') or {}
            away_team = g.get('visitor_team') or {}
            is_home = (home_team.get('id') == team_id)
            opponent_abbr = (away_team.get('abbreviation') if is_home else home_team.get('abbreviation')) or ''
            
            team_score = int(g.get('home_team_score') or 0) if is_home else int(g.get('visitor_team_score') or 0)
            opp_score = int(g.get('visitor_team_score') or 0) if is_home else int(g.get('home_team_score') or 0)
            
            # Try to find matching odds event
            spread_line = None
            total_line = None
            h2h_team = None
            h2h_opp = None
            
            for ev in odds_events:
                ev_home = ev.get('home_team', '')
                ev_away = ev.get('away_team', '')
                # Simple name match (could be improved with fuzzy)
                if team_full_name.lower() in ev_home.lower() or team_full_name.lower() in ev_away.lower():
                    bookmakers = ev.get('bookmakers', [])
                    if bookmakers:
                        bm = bookmakers[0]
                        markets = bm.get('markets', [])
                        for mkt in markets:
                            if mkt.get('key') == 'spreads':
                                spread_line = parse_spread(mkt.get('outcomes', []), team_full_name)
                            elif mkt.get('key') == 'totals':
                                total_line = parse_total(mkt.get('outcomes', []))
                            elif mkt.get('key') == 'h2h':
                                for out in mkt.get('outcomes', []):
                                    if team_full_name.lower() in out.get('name', '').lower():
                                        h2h_team = float(out.get('price', 0))
                                    else:
                                        h2h_opp = float(out.get('price', 0))
                    break
            
            # Compute ATS/O-U if we have lines and results
            ats_result = None
            ou_result = None
            if spread_line is not None and team_score and opp_score:
                ats_result = compute_ats(team_score, opp_score, spread_line, is_home)
            if total_line is not None and team_score and opp_score:
                ou_result = compute_ou(team_score, opp_score, total_line)
            
            row = {
                'team_abbr': team_abbr,
                'opponent_abbr': opponent_abbr,
                'game_date': game_date.date().isoformat(),
                'is_home': is_home,
                'spread_line': spread_line,
                'total_line': total_line,
                'h2h_team_odds': h2h_team,
                'h2h_opp_odds': h2h_opp,
                'team_score': team_score if team_score else None,
                'opp_score': opp_score if opp_score else None,
                'ats_result': ats_result,
                'ou_result': ou_result,
            }
            rows.append(row)
        except Exception as e:
            logger.warning(f"Error processing game: {e}")
            continue
    
    if not rows:
        logger.info("No rows to insert")
        return
    
    logger.info(f"Upserting {len(rows)} rows for {team_abbr}")
    # Upsert: conflict on (team_abbr, game_date) update if exists
    # Supabase REST doesn't have native upsert with conflict, so we do insert and handle duplicates via unique constraint or delete+insert
    # For simplicity, we'll just insert and ignore conflicts or use a stored procedure
    # Here, simple insert (duplicates will fail silently or we can add logic)
    try:
        resp = sb.table('games_odds').insert(rows, upsert=False).execute()
        logger.info(f"Inserted {len(rows)} odds records")
    except Exception as e:
        logger.error(f"Supabase insert error: {e}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='ETL odds for ATS/O-U analysis')
    parser.add_argument('--team', required=True, help='Team abbreviation (e.g., CHI)')
    parser.add_argument('--days', type=int, default=30, help='Days of history to fetch')
    args = parser.parse_args()
    ingest_odds_for_team(args.team, args.days)
