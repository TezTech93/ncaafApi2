import sqlite3
import datetime as dt
import requests
from bs4 import BeautifulSoup
import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)

current_year = dt.datetime.now().year

def get_soup(url):
    """Helper function to fetch and parse HTML"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    content = requests.get(url, headers=headers)
    soup = BeautifulSoup(content.content, 'html.parser')
    return soup

def get_team_gamelog(team, year):
    """
    Get NCAAF team gamelog using Sports Reference format
    Similar structure to your NFL function
    """
    all_stats = []
    
    # Convert team name to URL format (lowercase, hyphenated)
    team_url = team.lower().replace(' ', '-').replace('(', '').replace(')', '')
    url = f'https://www.sports-reference.com/cfb/schools/{team_url}/{year}/gamelog/'
    
    try:
        soup = get_soup(url)
        
        # Find the offensive stats table
        table = soup.find('table', {'id': 'offense'})
        if not table:
            print(f"No offensive stats table found for {team} {year}")
            return []
        
        # Find all relevant rows (excluding headers)
        rows = table.find_all('tr', id=lambda x: x and x.startswith('offense.'))
        
        for row in rows:
            game_data = {}
            
            # Extract all cells with data-stat attributes
            cells = row.find_all(['th', 'td'], attrs={"data-stat": True})
            
            for cell in cells:
                stat_name = cell['data-stat']
                stat_value = cell.text.strip()
                
                # Skip empty or irrelevant stats
                if not stat_value or stat_name in ['ranker', 'g']:
                    continue
                
                game_data[stat_name] = stat_value
            
            if game_data and 'date_game' in game_data:  # Only append if we have a date (valid game)
                all_stats.append(game_data)
                
        return all_stats if all_stats else []
        
    except Exception as e:
        logger.error(f"Error getting gamelog for {team} {year}: {e}")
        return []

def get_team_stats(team, year):
    """
    Main function to get NCAAF team stats - uses Sports Reference data structure
    """
    try:
        # Get gamelog data
        gamelog = get_team_gamelog(team, year)
        
        if not gamelog:
            return {"error": f"No data found for {team} {year}"}
        
        # Calculate summary stats
        summary = _calculate_summary_stats(gamelog)
        summary['games'] = gamelog
        summary['team'] = team
        summary['year'] = year
        
        # Store in database for caching
        _store_stats_in_db(team, year, gamelog)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error in get_team_stats: {e}")
        return {"error": str(e)}

def _calculate_summary_stats(games):
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
        
        for game in games:
            try:
                # Calculate win/loss - Sports Reference uses 'game_result' field
                result = game.get('game_result', '')
                if 'W' in result:
                    wins += 1
                elif 'L' in result:
                    losses += 1
                
                # Accumulate stats using Sports Reference field names
                points_for = int(game['points']) if game.get('points') and game['points'].isdigit() else 0
                points_against = int(game['opp_points']) if game.get('opp_points') and game['opp_points'].isdigit() else 0
                
                total_points += points_for
                total_points_against += points_against
                
                # Passing and rushing stats
                pass_yards = int(game['pass_yds']) if game.get('pass_yds') and game['pass_yds'].isdigit() else 0
                rush_yards = int(game['rush_yds']) if game.get('rush_yds') and game['rush_yds'].isdigit() else 0
                
                total_pass_yards += pass_yards
                total_rush_yards += rush_yards
                
            except (ValueError, KeyError) as e:
                logger.debug(f"Error processing game stats: {e}")
                continue
        
        return {
            'record': f"{wins}-{losses}",
            'wins': wins,
            'losses': losses,
            'points_per_game': round(total_points / total_games, 1) if total_games > 0 else 0,
            'points_against_per_game': round(total_points_against / total_games, 1) if total_games > 0 else 0,
            'pass_yards_per_game': round(total_pass_yards / total_games, 1) if total_games > 0 else 0,
            'rush_yards_per_game': round(total_rush_yards / total_games, 1) if total_games > 0 else 0,
            'total_games': total_games
        }
        
    except Exception as e:
        logger.error(f"Error calculating summary stats: {e}")
        return {}

def _store_stats_in_db(team, year, games):
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
            time_of_possession TEXT)""")
        
        # Insert data
        for game in games:
            try:
                cur.execute("""INSERT INTO Stats VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                          (
                            game.get('date_game', ''),
                            game.get('opp_name', ''),
                            game.get('game_location', ''),
                            game.get('game_result', ''),
                            int(game.get('points', 0)) if game.get('points') and game['points'].isdigit() else 0,
                            int(game.get('opp_points', 0)) if game.get('opp_points') and game['opp_points'].isdigit() else 0,
                            int(game.get('pass_cmp', 0)) if game.get('pass_cmp') and game['pass_cmp'].isdigit() else 0,
                            int(game.get('pass_att', 0)) if game.get('pass_att') and game['pass_att'].isdigit() else 0,
                            int(game.get('pass_yds', 0)) if game.get('pass_yds') and game['pass_yds'].isdigit() else 0,
                            int(game.get('pass_td', 0)) if game.get('pass_td') and game['pass_td'].isdigit() else 0,
                            int(game.get('pass_int', 0)) if game.get('pass_int') and game['pass_int'].isdigit() else 0,
                            int(game.get('rush_att', 0)) if game.get('rush_att') and game['rush_att'].isdigit() else 0,
                            int(game.get('rush_yds', 0)) if game.get('rush_yds') and game['rush_yds'].isdigit() else 0,
                            int(game.get('rush_td', 0)) if game.get('rush_td') and game['rush_td'].isdigit() else 0,
                            int(game.get('turnovers', 0)) if game.get('turnovers') and game['turnovers'].isdigit() else 0,
                            int(game.get('penalties', 0)) if game.get('penalties') and game['penalties'].isdigit() else 0,
                            int(game.get('penalty_yds', 0)) if game.get('penalty_yds') and game['penalty_yds'].isdigit() else 0,
                            int(game.get('first_down', 0)) if game.get('first_down') and game['first_down'].isdigit() else 0,
                            int(game.get('third_down_conv', 0)) if game.get('third_down_conv') and game['third_down_conv'].isdigit() else 0,
                            int(game.get('third_down_att', 0)) if game.get('third_down_att') and game['third_down_att'].isdigit() else 0,
                            int(game.get('fourth_down_conv', 0)) if game.get('fourth_down_conv') and game['fourth_down_conv'].isdigit() else 0,
                            int(game.get('fourth_down_att', 0)) if game.get('fourth_down_att') and game['fourth_down_att'].isdigit() else 0,
                            game.get('time_of_possession', '')
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

def _get_stats_from_db(team, year):
    """Get stats from SQLite database (for caching)"""
    try:
        db_path = f"ncaafDb/{team.lower().replace(' ', '-').replace('(', '').replace(')', '')}-{year}-stats.db"
        if not os.path.exists(db_path):
            return None
            
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get all games
        cur.execute('SELECT * FROM Stats')
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
            'time_of_possession'
        ]
        
        games = []
        for row in rows:
            game_dict = dict(zip(columns, row))
            games.append(game_dict)
        
        return games
        
    except Exception as e:
        logger.error(f"Error reading from database: {e}")
        return None

def ncaafdb(team, year=current_year):
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
            return False
            
    except Exception as e:
        logger.error(f"Error in ncaafdb: {e}")
        return False

def get_player_stats(player, season=None):
    """
    Get NCAAF player statistics - placeholder implementation
    """
    try:
        # This would be replaced with actual NCAAF API calls
        return {
            "player": player,
            "season": season or "2023",
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
        return None

def get_injury_report(team, week):
    """Get NCAAF injury report - placeholder implementation"""
    all_stats = []
    # url = f'https://www.sports-reference.com/cfb/schools/{team}/2024_injuries.htm'
    # soup = get_soup(url)
    # Implementation would go here
    return all_stats

def get_roster(team):
    """Get NCAAF roster - placeholder implementation"""
    pass

def get_coach_stats(coach):
    """Get NCAAF coach stats - placeholder implementation"""
    pass

print(f"Testing NCAAF stats for {test_team} {test_year}...")
stats = get_team_gamelog(test_team, test_year)

if stats:
    print(f"Successfully loaded {len(stats)} games for {test_team}")
    if stats:
        print(f"Sample game: {stats[0]}")
else:
    print(f"No data found for {test_team} {test_year}")

print('ncaaf stats loaded')
