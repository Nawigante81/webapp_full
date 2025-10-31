"""
Scheduler script for refreshing team reports.

This script can be run manually or via cron to refresh and store reports for
multiple teams at regular intervals. It relies on the same scraping and
Supabase functions used by the application. To schedule regular updates,
configure your system's cron scheduler to call this script (e.g., every
morning).

Usage:
    python3 scheduler.py
"""
import os
import logging
from dotenv import load_dotenv
from fetch_data import assemble_team_report
from app import save_report, SUPABASE_URL, SUPABASE_SERVICE_KEY, DEFAULT_NBA_SEASON

# Load environment variables
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)


SUPPORTED_TEAMS = {
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
    'spurs': 'SAS'
}


def refresh_all_teams():
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        logger.warning("Supabase not configured; skipping refresh.")
        return
        
    logger.info(f"Starting refresh for {len(SUPPORTED_TEAMS)} teams")
    
    for slug, br_abbr in SUPPORTED_TEAMS.items():
        try:
            logger.info(f"Refreshing data for {slug} ({br_abbr})")
            report = assemble_team_report(br_abbr, season=DEFAULT_NBA_SEASON)
            save_report(slug, report, bearer_token=None)
            logger.info(f"Successfully refreshed {slug}")
        except Exception as e:
            logger.error(f"Failed to refresh {slug}: {e}")
    
    logger.info("Team refresh process completed")


if __name__ == '__main__':
    refresh_all_teams()