import sqlite3
import datetime as dt
import requests
from bs4 import BeautifulSoup
import os
import pandas as pd
import logging
import time
from random import uniform
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

current_year = dt.datetime.now().year

def get_soup(url):
    """Helper function to fetch and parse HTML"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        # Add respectful delay
        time.sleep(uniform(1, 3))
        content = requests.get(url, headers=headers, timeout=10)
        content.raise_for_status()
        soup = BeautifulSoup(content.content, 'html.parser')
        return soup
    except Exception as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return None

def get_team_gamelog(team: str, year: int) -> List[Dict]:
    """
    Get NCAAF team gamelog using Sports Reference with improved table targeting
    """
    all_stats = []
    
    try:
        # Convert team name to URL format
        team_url = team.lower().replace(' ', '-').replace('(', '').replace(')', '')
        url = f'https://www.sports-reference.com/cfb/schools/{team_url}/{year}/gamelog/'
        
        soup = get_soup(url)
        if not soup:
            logger.warning(f"Could not fetch page for {team} ({year})")
            return []
        
        # Check if page exists and has data
        if "Page Not Found" in soup.text:
            logger.warning(f"No schedule found for {team} ({year})")
            return []
        
        # Target the specific schedule table - try both offense and defense tables
        table = soup.find('table', {'id': 'offense'})
        if not table:
            table = soup.find('table', {'id': 'defense'})
        if not table:
            logger.warning(f"No schedule table found for {team} ({year})")
            return []
        
        # More robust row filtering
        rows = table.find_all('tr')
        
        for row in rows:
            try:
                # Skip header rows and empty rows
                if (row.get('class') and 
                    any(cls in row.get('class', []) for cls in ['thead', 'over_header'])) or not row.find('td'):
                    continue
                
                # Look for cells with data-stat attributes
                cells = row.find_all(['td', 'th'])
                game_data = {}
                
                for cell in cells:
                    stat_name = cell.get('data-stat')
                    if not stat_name:
                        continue
                        
                    stat_value = cell.text.strip()
                    
                    # Capture all relevant fields
                    if stat_name in [
                        'date_game', 'opp_name', 'game_location', 'game_result',
                        'points', 'opp_points', 'pass_cmp', 'pass_att', 'pass_yds',
                        'pass_td', 'pass_int', 'rush_att', 'rush_yds', 'rush_td',
                        'turnovers', 'penalties', 'penalty_yds', 'first_down',
                        'third_down_conv', 'third_down_att', 'fourth_down_conv',
                        'fourth_down_att', 'time_of_possession'
                    ] and stat_value:
                        game_data[stat_name] = stat_value
                    
                    # Also capture the opponent link for team code
                    if stat_name == 'opp_name' and cell.find('a'):
                        opp_link = cell.find('a').get('href', '')
                        if '/cfb/schools/' in opp_link:
                            game_data['opp_code'] = opp_link.split('/')[-2]
                
                # Only add if we have basic game info and it's not a header row
                if ('date_game' in game_data and game_data['date_game'] and 
                    'opp_name' in game_data and game_data['opp_name'] and
                    not game_data['date_game'].startswith('Date')):
                    
                    # Add metadata
                    game_data['team'] = team
                    game_data['year'] = year
                    game_data['source'] = 'sports_reference'
                    
                    all_stats.append(game_data)
                    
            except Exception as e:
                logger.debug(f"Error processing row for {team}: {e}")
                continue
        
        logger.info(f"Found {len(all_stats)} games for {team} ({year})")
        return all_stats
        
    except Exception as e:
        logger.error(f"Error getting gamelog for {team} {year}: {e}")
        return []

def get_team_stats(team: str, year: int) -> Dict:
    """
    Main function to get NCAAF team stats - uses Sports Reference data structure
    """
    try:
        # First try to get from database
        db_stats = _get_stats_from_db(team, year)
        if db_stats:
            gamelog = db_stats
            logger.info(f"Loaded {len(gamelog)} games from database for {team} ({year})")
        else:
            # Get gamelog data from web
            gamelog = get_team_gamelog(team, year)
        
        if not gamelog:
            return {"error": f"No data found for {team} {year}"}
        
        # Calculate summary stats
        summary = _calculate_summary_stats(gamelog)
        summary['games'] = gamelog
        summary['team'] = team
        summary['year'] = year
        
        # Store in database for caching if not already there
        if not db_stats:
            _store_stats_in_db(team, year, gamelog)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error in get_team_stats: {e}")
        return {"error": str(e)}

def _calculate_summary_stats(games: List[Dict]) -> Dict:
    """Calculate summary statistics from game data using Sports Reference field names"""
    try:
        if not games:
            return {}
            
        total_games = len(games)
        wins = 0
        losses = 0
        
        # Basic stats accumulators
        total_points = 0
        total_points_against = 0
        total_pass_yards = 0
        total_rush_yards = 0
        total_pass_attempts = 0
        total_pass_completions = 0
        total_rush_attempts = 0
        total_turnovers = 0
        
        for game in games:
            try:
                # Calculate win/loss - Sports Reference uses 'game_result' field
                result = game.get('game_result', '')
                if 'W' in result.upper():
                    wins += 1
                elif 'L' in result.upper():
                    losses += 1
                
                # Accumulate stats using Sports Reference field names
                points_for = int(game['points']) if game.get('points') and game['points'].isdigit() else 0
                points_against = int(game['opp_points']) if game.get('opp_points') and game['opp_points'].isdigit() else 0
                
                total_points += points_for
                total_points_against += points_against
                
                # Passing and rushing stats
                pass_yards = int(game['pass_yds']) if game.get('pass_yds') and game['pass_yds'].isdigit() else 0
                rush_yards = int(game['rush_yds']) if game.get('rush_yds') and game['rush_yds'].isdigit() else 0
                pass_att = int(game['pass_att']) if game.get('pass_att') and game['pass_att'].isdigit() else 0
                pass_cmp = int(game['pass_cmp']) if game.get('pass_cmp') and game['pass_cmp'].isdigit() else 0
                rush_att = int(game['rush_att']) if game.get('rush_att') and game['rush_att'].isdigit() else 0
                turnovers = int(game['turnovers']) if game.get('turnovers') and game['turnovers'].isdigit() else 0
                
                total_pass_yards += pass_yards
                total_rush_yards += rush_yards
                total_pass_attempts += pass_att
                total_pass_completions += pass_cmp
                total_rush_attempts += rush_att
                total_turnovers += turnovers
                
            except (ValueError, KeyError) as e:
                logger.debug(f"Error processing game stats: {e}")
                continue
        
        # Calculate percentages and averages
        completion_pct = (total_pass_completions / total_pass_attempts * 100) if total_pass_attempts > 0 else 0
        yards_per_pass = (total_pass_yards / total_pass_attempts) if total_pass_attempts > 0 else 0
        yards_per_rush = (total_rush_yards / total_rush_attempts) if total_rush_attempts > 0 else 0
        
        return {
            'record': f"{wins}-{losses}",
            'wins': wins,
            'losses': losses,
            'points_per_game': round(total_points / total_games, 1) if total_games > 0 else 0,
            'points_against_per_game': round(total_points_against / total_games, 1) if total_games > 0 else 0,
            'pass_yards_per_game': round(total_pass_yards / total_games, 1) if total_games > 0 else 0,
            'rush_yards_per_game': round(total_rush_yards / total_games, 1) if total_games > 0 else 0,
            'completion_percentage': round(completion_pct, 1),
            'yards_per_pass': round(yards_per_pass, 1),
            'yards_per_rush': round(yards_per_rush, 1),
            'turnovers_per_game': round(total_turnovers / total_games, 1) if total_games > 0 else 0,
            'total_games': total_games
        }
        
    except Exception as e:
        logger.error(f"Error calculating summary stats: {e}")
        return {}

def _store_stats_in_db(team: str, year: int, games: List[Dict]) -> bool:
    """Store stats in SQLite database for caching"""
    try:
        # Create ncaafDb directory if it doesn't exist
        os.makedirs('ncaafDb', exist_ok=True)
        
        db_path = f"ncaafDb/{team.lower().replace(' ', '-').replace('(', '').replace(')', '')}-{year}-stats.db"
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Create table with Sports Reference field names
        cur.execute("""CREATE TABLE IF NOT EXISTS Stats(
            game_date TEXT, opponent TEXT, game_location TEXT, game_result TEXT,
            points INTEGER, opp_points INTEGER, pass_cmp INTEGER, pass_att INTEGER,
            pass_yds INTEGER, pass_td INTEGER, pass_int INTEGER, rush_att INTEGER,
            rush_yds INTEGER, rush_td INTEGER, turnovers INTEGER, penalties INTEGER,
            penalty_yds INTEGER, first_down INTEGER, third_down_conv INTEGER,
            third_down_att INTEGER, fourth_down_conv INTEGER, fourth_down_att INTEGER,
            time_of_possession TEXT, opp_code TEXT, team TEXT, year INTEGER, source TEXT)""")
        
        # Clear existing data for this team/year
        cur.execute("DELETE FROM Stats WHERE team = ? AND year = ?", (team, year))
        
        # Insert data
        for game in games:
            try:
                cur.execute("""INSERT INTO Stats VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                          (
                            game.get('date_game', ''),
                            game.get('opp_name', ''),
                            game.get('game_location', ''),
                            game.get('game_result', ''),
                            int(game.get('points', 0)) if game.get('points') and str(game['points']).isdigit() else 0,
                            int(game.get('opp_points', 0)) if game.get('opp_points') and str(game['opp_points']).isdigit() else 0,
                            int(game.get('pass_cmp', 0)) if game.get('pass_cmp') and str(game['pass_cmp']).isdigit() else 0,
                            int(game.get('pass_att', 0)) if game.get('pass_att') and str(game['pass_att']).isdigit() else 0,
                            int(game.get('pass_yds', 0)) if game.get('pass_yds') and str(game['pass_yds']).isdigit() else 0,
                            int(game.get('pass_td', 0)) if game.get('pass_td') and str(game['pass_td']).isdigit() else 0,
                            int(game.get('pass_int', 0)) if game.get('pass_int') and str(game['pass_int']).isdigit() else 0,
                            int(game.get('rush_att', 0)) if game.get('rush_att') and str(game['rush_att']).isdigit() else 0,
                            int(game.get('rush_yds', 0)) if game.get('rush_yds') and str(game['rush_yds']).isdigit() else 0,
                            int(game.get('rush_td', 0)) if game.get('rush_td') and str(game['rush_td']).isdigit() else 0,
                            int(game.get('turnovers', 0)) if game.get('turnovers') and str(game['turnovers']).isdigit() else 0,
                            int(game.get('penalties', 0)) if game.get('penalties') and str(game['penalties']).isdigit() else 0,
                            int(game.get('penalty_yds', 0)) if game.get('penalty_yds') and str(game['penalty_yds']).isdigit() else 0,
                            int(game.get('first_down', 0)) if game.get('first_down') and str(game['first_down']).isdigit() else 0,
                            int(game.get('third_down_conv', 0)) if game.get('third_down_conv') and str(game['third_down_conv']).isdigit() else 0,
                            int(game.get('third_down_att', 0)) if game.get('third_down_att') and str(game['third_down_att']).isdigit() else 0,
                            int(game.get('fourth_down_conv', 0)) if game.get('fourth_down_conv') and str(game['fourth_down_conv']).isdigit() else 0,
                            int(game.get('fourth_down_att', 0)) if game.get('fourth_down_att') and str(game['fourth_down_att']).isdigit() else 0,
                            game.get('time_of_possession', ''),
                            game.get('opp_code', ''),
                            game.get('team', ''),
                            game.get('year', year),
                            game.get('source', 'sports_reference')
                          ))
            except Exception as e:
                logger.debug(f"Error inserting game into database: {e}")
                continue
                
        conn.commit()
        conn.close()
        
        logger.info(f"Stored {len(games)} games in database for {team} {year}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing stats in database: {e}")
        return False

def _get_stats_from_db(team: str, year: int) -> Optional[List[Dict]]:
    """Get stats from SQLite database (for caching)"""
    try:
        db_path = f"ncaafDb/{team.lower().replace(' ', '-').replace('(', '').replace(')', '')}-{year}-stats.db"
        if not os.path.exists(db_path):
            return None
            
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get all games
        cur.execute('SELECT * FROM Stats WHERE team = ? AND year = ?', (team, year))
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            return None
            
        # Convert to list of dictionaries
        columns = [
            'game_date', 'opponent', 'game_location', 'game_result', 'points', 'opp_points',
            'pass_cmp', 'pass_att', 'pass_yds', 'pass_td', 'pass_int', 'rush_att',
            'rush_yds', 'rush_td', 'turnovers', 'penalties', 'penalty_yds', 'first_down',
            'third_down_conv', 'third_down_att', 'fourth_down_conv', 'fourth_down_att',
            'time_of_possession', 'opp_code', 'team', 'year', 'source'
        ]
        
        games = []
        for row in rows:
            game_dict = dict(zip(columns, row))
            games.append(game_dict)
        
        return games
        
    except Exception as e:
        logger.error(f"Error reading from database: {e}")
        return None

def ncaafdb(team: str, year: int = current_year) -> bool:
    """
    Scrape NCAAF team stats and store in SQLite database
    Maintains backward compatibility
    """
    try:
        # First try to get from database
        db_stats = _get_stats_from_db(team, year)
        if db_stats:
            return True
        
        # If not in database, scrape and store
        gamelog = get_team_gamelog(team, year)
        if gamelog:
            return _store_stats_in_db(team, year, gamelog)
        else:
            logger.warning(f"No data found to store for {team} ({year})")
            return False
            
    except Exception as e:
        logger.error(f"Error in ncaafdb: {e}")
        return False

def get_player_stats(player: str, season: Optional[int] = None) -> Dict:
    """
    Get NCAAF player statistics - placeholder implementation
    """
    try:
        # This would be replaced with actual NCAAF API calls
        return {
            "player": player,
            "season": season or current_year,
            "position": "QB",
            "games_played": 12,
            "passing_yards": 3250,
            "passing_tds": 28,
            "interceptions": 5,
            "completion_percentage": "65.8%",
            "rushing_yards": 450,
            "rushing_tds": 8
        }
    except Exception as e:
        logger.error(f"Error getting NCAAF player stats: {e}")
        return {}

def get_injury_report(team: str, week: int) -> List[Dict]:
    """Get NCAAF injury report - placeholder implementation"""
    logger.info(f"Getting injury report for {team} week {week} - not implemented")
    return []

def get_roster(team: str) -> List[Dict]:
    """Get NCAAF roster - placeholder implementation"""
    logger.info(f"Getting roster for {team} - not implemented")
    return []

def get_coach_stats(coach: str) -> Dict:
    """Get NCAAF coach stats - placeholder implementation"""
    logger.info(f"Getting coach stats for {coach} - not implemented")
    return {}

test_team = "Alabama"
test_year = 2023

print(f"Testing NCAAF stats for {test_team} {test_year}...")
stats = get_team_gamelog(test_team, test_year)

if stats:
    print(f"Successfully loaded {len(stats)} games for {test_team}")
    if stats:
        print(f"Sample game: {stats[0]}")
        
    # Test summary stats
    summary = get_team_stats(test_team, test_year)
    print(f"Summary: {summary.get('record', 'N/A')} | PPG: {summary.get('points_per_game', 'N/A')}")
else:
    print(f"No data found for {test_team} {test_year}")

print('ncaaf stats loaded')
