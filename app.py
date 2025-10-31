"""
Comprehensive NBA analysis server (full version).

This server extends the functionality of the pro version with advanced analytics
and parlay suggestions. It provides endpoints to generate detailed reports,
perform analysis, and manage persisted data via Supabase.

Endpoints:
  - GET /api/report/<team>     Generate raw report using scraping utilities
                               and store it in Supabase.
  - GET /api/reports           Retrieve stored reports for the authenticated user.
  - GET /api/analysis/<team>   Generate analysis metrics and parlay suggestions
                               based on the latest report data.
  - GET /full.html             Serve the full-featured front-end page.

See `analysis.py` and `fetch_data.py` for underlying data processing.
"""
import json
import os
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
from urllib.parse import unquote
import requests
from dotenv import load_dotenv

from fetch_data import (
    get_player_statistics_api_nba,
    get_scores_rapid,
    get_team_games,
    get_team_injuries,
    get_odds_for_games,
)
from bdl import team_lookup as bdl_team_lookup, games_by_team as bdl_games_by_team, injuries_by_team as bdl_injuries_by_team
from odds_api import current_odds as odds_current_odds, find_odds_for_matchup as odds_find_for_matchup
from analysis import calculate_basic_metrics, calculate_ats_ou_rates, generate_parlay_suggestions

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Server configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# NBA season configuration
DEFAULT_NBA_SEASON = int(os.getenv("DEFAULT_NBA_SEASON", "2025"))

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)


# Team mapping: UI slug -> Basketball-Reference abbreviation
SLUG_TO_BR = {
    # Atlantic Division
    'celtics': 'BOS',
    'nets': 'BRK',
    'knicks': 'NYK',
    '76ers': 'PHI',
    'raptors': 'TOR',

    # Central Division
    'bulls': 'CHI',
    'cavaliers': 'CLE',
    'pistons': 'DET',
    'pacers': 'IND',
    'bucks': 'MIL',

    # Southeast Division
    'hawks': 'ATL',
    'hornets': 'CHA',
    'heat': 'MIA',
    'magic': 'ORL',
    'wizards': 'WAS',

    # Northwest Division
    'nuggets': 'DEN',
    'timberwolves': 'MIN',
    'thunder': 'OKC',
    'trail-blazers': 'POR',
    'jazz': 'UTA',

    # Pacific Division
    'warriors': 'GSW',
    'clippers': 'LAC',
    'lakers': 'LAL',
    'suns': 'PHX',
    'kings': 'SAC',

    # Southwest Division
    'mavericks': 'DAL',
    'rockets': 'HOU',
    'grizzlies': 'MEM',
    'pelicans': 'NOP',
    'spurs': 'SAS',
}


def _resolve_br_abbr(team_input: str) -> tuple[str, str]:
    """Normalize incoming team value to (slug, BR abbreviation).

    - If input is a known slug, map to BR abbr
    - If input looks like a 3-letter abbr, use as-is uppercased
    - Otherwise, best-effort uppercase fallback (may be invalid)
    """
    slug = team_input.lower().strip()
    if slug in SLUG_TO_BR:
        return slug, SLUG_TO_BR[slug]
    # Allow passing BR abbr directly (e.g., 'CHI')
    ti = team_input.strip()
    if len(ti) == 3 and ti.isalpha():
        return ti.lower(), ti.upper()
    return slug, ti.upper()


class FullHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        """Allow no-arg construction in tests by setting minimal I/O fields.

        In production, BaseHTTPRequestHandler requires (request, client_address, server).
        Tests instantiate FullHandler() directly and patch methods, so we bypass super().__init__
        when no args are provided.
        """
        if len(args) == 0 and not kwargs:
            self.headers = {}
            self.rfile = io.BytesIO()
            self.wfile = io.BytesIO()
            self.path = '/'
            return
        super().__init__(*args, **kwargs)
    def do_GET(self):
        # Parse path and query string separately
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        if path.startswith('/api/report/'):
            team = path[len('/api/report/'):].strip('/')
            save_flag = query.get('save', ['false'])[0].lower() == 'true'
            self.handle_generate_report(team, save_flag)
        elif path == '/api/reports':
            self.handle_list_reports(query)
        elif path.startswith('/api/analysis/'):
            team = path[len('/api/analysis/'):].strip('/')
            self.handle_analysis(team)
        elif path.startswith('/api/refresh/'):
            team = path[len('/api/refresh/'):].strip('/')
            self.handle_refresh(team)
        elif path.startswith('/api/game/') and path.endswith('/players'):
            # /api/game/<game_id>/players
            try:
                game_id = path.split('/')[3]
            except Exception:
                self.send_response(400)
                self.end_headers()
                return
            self.handle_player_stats(game_id)
        elif path.startswith('/api/odds/scores'):
            from urllib.parse import parse_qs
            query = parse_qs(parsed.query)
            fixture_id = (query.get('fixtureId') or query.get('fixtureid') or [None])[0]
            if not fixture_id:
                self.send_response(400)
                self.end_headers()
                return
            self.handle_scores(fixture_id)
        elif path.startswith('/report'):
            from urllib.parse import parse_qs
            query = parse_qs(parsed.query)
            team = (query.get('team') or [None])[0]
            if not team:
                self.send_response(400)
                self.end_headers()
                return
            self.handle_report_simple(team)
        elif path.startswith('/api/report_bdl'):
            # expects /api/report_bdl?team=CHI (abbr or name)
            from urllib.parse import parse_qs
            query = parse_qs(parsed.query)
            team = (query.get('team') or [None])[0]
            if not team:
                self.send_response(400)
                self.end_headers()
                return
            self.handle_report_bdl(team)
        elif path in ('/', '/full.html', '/index.html'):
            self.serve_full_page()
        else:
            self.send_response(404)
            self.end_headers()

    def serve_full_page(self):
        try:
            tmpl_path = os.path.join(os.path.dirname(__file__), 'templates', 'full.html')
            with open(tmpl_path, 'rb') as fh:
                content = fh.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Full page not found.')

    def handle_generate_report(self, team: str, save_flag: bool):
        # Deprecated legacy endpoint (scraping disabled). Direct callers to API-first.
        self.send_response(410)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'error': 'deprecated',
            'message': 'Use /report?team= or /api/report_bdl?team= for API-first reports.'
        }).encode('utf-8'))

    def handle_list_reports(self, query):
        """Return stored reports filtered by query parameters.

        Query parameters:
          team: filter by team abbreviation
          from:  ISO date string (inclusive) - filter by created_at >= from
          to:    ISO date string (inclusive) - filter by created_at <= to
        """
        if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps([]).encode('utf-8'))
            return
        bearer = self.headers.get('Authorization')
        team_filter = query.get('team', [None])[0]
        date_from = query.get('from', [None])[0]
        date_to = query.get('to', [None])[0]
        reports = fetch_reports(bearer, team_filter, date_from, date_to)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(reports).encode('utf-8'))

    def handle_analysis(self, team: str):
        # Deprecated: analysis previously used legacy scraping report. Consider rebuilding on /report data.
        self.send_response(410)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'error': 'deprecated',
            'message': 'Analysis endpoint is disabled in API-first mode.'
        }).encode('utf-8'))

    def handle_refresh(self, team: str):
        # Deprecated: refresh relied on legacy pipelines. Use ETL script or API-first endpoints.
        self.send_response(410)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'error': 'deprecated',
            'message': 'Refresh is disabled in API-first mode.'
        }).encode('utf-8'))

    def handle_player_stats(self, game_id: str):
        """Return per-player statistics for a game via API-NBA provider."""
        stats = get_player_statistics_api_nba(game_id)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'game_id': game_id,
            'players': stats,
        }).encode('utf-8'))

    def handle_scores(self, fixture_id: str):
        data = get_scores_rapid(fixture_id)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def handle_report_simple(self, team_query: str):
        """API-first report using BDL (games, injuries) + The Odds API (odds).

        Minimal change path that avoids legacy scraping.
        """
        games = get_team_games(team_query, limit=25)
        injuries = get_team_injuries(team_query)
        odds = get_odds_for_games()
        payload = {
            'team': team_query,
            'games': games[:10] if isinstance(games, list) else [],
            'injuries': injuries,
            'odds': odds,
        }
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def handle_report_bdl(self, team_query: str):
        """Compose report using BallDontLie + The Odds API."""
        # Lookup team in BDL
        team = bdl_team_lookup(team_query)
        if not team:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "team_not_found"}).encode('utf-8'))
            return
        team_id = team.get('id')
        season = DEFAULT_NBA_SEASON
        games_resp = bdl_games_by_team(team_id, season=season)
        games = games_resp.get('data', []) if isinstance(games_resp, dict) else []
        injuries_resp = bdl_injuries_by_team(team_id)
        injuries = injuries_resp.get('data', []) if isinstance(injuries_resp, dict) else []

        # Odds: get current odds and filter for events including this team
        try:
            odds_events = odds_current_odds()
        except Exception:
            odds_events = []
        team_names = [team.get('full_name'), team.get('name'), team.get('abbreviation')]
        odds_for_team = odds_find_for_matchup(odds_events, [t for t in team_names if t])

        payload = {
            'team': {
                'id': team_id,
                'name': team.get('full_name') or team.get('name'),
                'abbreviation': team.get('abbreviation'),
                'city': team.get('city'),
                'division': team.get('division'),
                'conference': team.get('conference'),
            },
            'season': season,
            'games': games,
            'injuries': injuries,
            'odds': odds_for_team,
        }
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def log_message(self, format, *args):
        return


def save_report(team: str, data: dict, bearer_token: str | None) -> None:
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        return
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/reports"
    headers = {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_SERVICE_KEY,
        'Authorization': f"Bearer {SUPABASE_SERVICE_KEY}",
        'Prefer': 'return=minimal'
    }
    if bearer_token:
        headers['Authorization'] = bearer_token
    payload = {
        'team': team.lower(),
        'data': data
    }
    try:
        requests.post(url=url, headers=headers, json=payload, timeout=5)
    except requests.exceptions.RequestException:
        pass


def fetch_reports(bearer_token: str | None, team: str | None = None, date_from: str | None = None, date_to: str | None = None) -> list:
    """Retrieve reports from Supabase with optional filters.

    Args:
        bearer_token: JWT for user context (or None for service role).
        team: Filter by team name (lowercase slug).
        date_from: ISO date string to filter reports created on or after this date.
        date_to: ISO date string to filter reports created on or before this date.

    Returns:
        List of report rows (JSON objects).
    """
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        return []
    # Build query string with filters
    filters = []
    if team:
        filters.append(f"team=eq.{team}")
    if date_from:
        filters.append(f"created_at=gte.{date_from}")
    if date_to:
        filters.append(f"created_at=lte.{date_to}")
    params = '&'.join(filters)
    if params:
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/reports?select=*&{params}"
    else:
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/reports?select=*"
    headers = {
        'apikey': SUPABASE_SERVICE_KEY,
        'Authorization': f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    if bearer_token:
        headers['Authorization'] = bearer_token
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException:
        return []


def run_server(host: str = None, port: int = None) -> None:
    host = host or SERVER_HOST
    port = port or SERVER_PORT
    
    logger.info(f"Starting NBA analysis server on {host}:{port}")
    logger.info(f"Supabase configured: {bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)}")
    
    with HTTPServer((host, port), FullHandler) as httpd:
        logger.info(f"Serving NBA full app on http://{host}:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        finally:
            logger.info("Server stopped")


if __name__ == '__main__':
    run_server()