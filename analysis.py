"""
Advanced analytics module for NBA reports.

This module takes raw scraped data (game results and betting lines) and
computes derived metrics such as average points scored/allowed, ATS and
over/under rates, offensive/defensive ratings, pace and basic trends. It also
generates parlay suggestions based on recent performance, strengths and
weaknesses.

The functions here assume that the input data comes from fetch_data.py:
    report = {
        'team': 'CHI',
        'results': [ ... list of game dictionaries ... ],
        'lines': [ ... list of betting lines ... ],
        'injuries': [ ... list of injuries ... ]
    }

If the input lists are empty (e.g. because scraping failed), the functions
return None or default values. They are designed to be called by the API
server to produce a richer response for end users.
"""

from typing import Dict, List, Optional, Tuple

def calculate_basic_metrics(report: Dict[str, object]) -> Dict[str, Optional[float]]:
    """Compute average points scored and allowed over all games in the report.

    Args:
        report: Data dictionary containing 'results' list.

    Returns:
        A dictionary with average points for and against, or None if data
        insufficient.
    """
    results: List[Dict[str, str]] = report.get('results', [])  # type: ignore
    if not results:
        return {
            'avg_points_for': None,
            'avg_points_against': None,
        }
    total_for = 0
    total_against = 0
    count = 0
    for game in results:
        try:
            pf = int(game['team_points'])
            pa = int(game['opp_points'])
        except (KeyError, ValueError, TypeError):
            continue
        total_for += pf
        total_against += pa
        count += 1
    if count == 0:
        return {
            'avg_points_for': None,
            'avg_points_against': None,
        }
    return {
        'avg_points_for': total_for / count,
        'avg_points_against': total_against / count,
    }


def calculate_ats_ou_rates(report: Dict[str, object]) -> Dict[str, Optional[str]]:
    """Calculate ATS (against the spread) and over/under rates for the last 10 games.

    Args:
        report: Data dictionary containing 'lines'.

    Returns:
        Dictionary with ATS and OU records in 'xW-yL' and 'xO-yU' format,
        respectively; None if insufficient data.
    """
    lines: List[Dict[str, str]] = report.get('lines', [])  # type: ignore
    if not lines:
        return {'ats_rate': None, 'ou_rate': None}
    last_n = lines[:10]
    ats_wins = sum(1 for l in last_n if l.get('ats') == 'W')
    ou_over = sum(1 for l in last_n if l.get('ou') == 'O')
    n = len(last_n)
    return {
        'ats_rate': f"{ats_wins}W-{n - ats_wins}L",
        'ou_rate': f"{ou_over}O-{n - ou_over}U",
    }


def generate_parlay_suggestions(report: Dict[str, object]) -> List[Dict[str, object]]:
    """Generate simple parlay suggestions based on recent ATS and OU performance.

    Uses heuristics: if a team has more over results than under, suggest over
    totals; if they cover the spread often, suggest them to cover; also
    includes a player prop placeholder based on injuries.

    Args:
        report: Data dictionary containing 'lines' and 'injuries'.

    Returns:
        List of leg dictionaries with description and confidence labels.
    """
    lines: List[Dict[str, str]] = report.get('lines', [])  # type: ignore
    injuries: List[Dict[str, str]] = report.get('injuries', [])  # type: ignore
    legs = []
    if lines:
        last5 = lines[:5]
        over_count = sum(1 for l in last5 if l.get('ou') == 'O')
        ats_count = sum(1 for l in last5 if l.get('ats') == 'W')
        if over_count >= 3:
            legs.append({
                'type': 'total',
                'bet': 'over',
                'confidence': 'Medium',
                'note': 'Team has hit the over in majority of last 5 games.'
            })
        else:
            legs.append({
                'type': 'total',
                'bet': 'under',
                'confidence': 'Medium',
                'note': 'Team tends to stay under recently.'
            })
        if ats_count >= 3:
            legs.append({
                'type': 'spread',
                'bet': 'cover',
                'confidence': 'Medium',
                'note': 'Team has covered the spread frequently.'
            })
        else:
            legs.append({
                'type': 'spread',
                'bet': 'fade',
                'confidence': 'Low',
                'note': 'Team struggles to cover the spread.'
            })
    # Example player prop suggestion based on injuries list
    if injuries:
        injured_names = [i['player'] for i in injuries]
        legs.append({
            'type': 'player_prop',
            'bet': 'backup over',
            'confidence': 'Low',
            'note': f"Starters {', '.join(injured_names)} are out; consider backups over stats."
        })
    return legs