import sqlite3
import datetime as dt
import requests
from bs4 import BeautifulSoup
import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)

current_year = dt.datetime.now().year

def get_team_stats(team, year):
    """
    Main function to get NCAAF team stats - integrates with your existing structure
    """
    try:
        # Convert team name to URL format (lowercase, hyphenated)
        team_url = team.lower().replace(' ', '-').replace('(', '').replace(')', '')
        
        # First try to get from database
        db_stats = _get_stats_from_db(team_url, year)
        if db_stats:
            return db_stats
        
        # If not in database, scrape and store
        if ncaafdb(team_url, year):
            return _get_stats_from_db(team_url, year)
        else:
            return {"error": f"Could not retrieve stats for {team} {year}"}
            
    except Exception as e:
        logger.error(f"Error in get_team_stats: {e}")
        return {"error": str(e)}

def _get_stats_from_db(team, year):
    """Get stats from SQLite database"""
    try:
        db_path = f"ncaafDb/{team}-{year}-stats.db"
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
            'Week', 'Day', 'Date', 'OT', 'Opp', 'Tm', 'Opp2', 'Cmp', 'Att',
            'PassYds', 'PassTD', 'Int', 'Sk', 'SkYds', 'PassYA', 'PassNYA',
            'CmpPct', 'PasserRate', 'RushAtt', 'RushYds', 'RushYA', 'RushTD',
            'FGM', 'FGA', 'XPM', 'XPA', 'Pnt', 'PuntYds', 'ThirdDownConv',
            'ThirdDownAtt', 'FourthDownConv', 'FourthDownAtt', 'ToP'
        ]
        
        games = []
        for row in rows:
            game_dict = dict(zip(columns, row))
            games.append(game_dict)
        
        # Calculate summary stats
        summary = _calculate_summary_stats(games)
        summary['games'] = games
        summary['team'] = team
        summary['year'] = year
        
        return summary
        
    except Exception as e:
        logger.error(f"Error reading from database: {e}")
        return None

def _calculate_summary_stats(games):
    """Calculate summary statistics from game data"""
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
                # Calculate win/loss
                tm_score = int(game['Tm']) if game['Tm'] and str(game['Tm']).isdigit() else 0
                opp_score = int(game['Opp2']) if game['Opp2'] and str(game['Opp2']).isdigit() else 0
                
                if tm_score > opp_score:
                    wins += 1
                elif tm_score < opp_score:
                    losses += 1
                
                # Accumulate stats
                total_points += tm_score
                total_points_against += opp_score
                total_pass_yards += int(game['PassYds']) if game['PassYds'] and str(game['PassYds']).isdigit() else 0
                total_rush_yards += int(game['RushYds']) if game['RushYds'] and str(game['RushYds']).isdigit() else 0
                
            except (ValueError, KeyError):
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

def ncaafdb(team, year=current_year):
    """
    Scrape NCAAF team stats and store in SQLite database
    """
    team = team.lower()
    
    # Create ncaafDb directory if it doesn't exist
    os.makedirs('ncaafDb', exist_ok=True)
    
    try:
        # NCAAF stats URL (using Sports Reference format)
        url = f'https://www.sports-reference.com/cfb/schools/{team}/{year}/gamelog/'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        content = requests.get(url, headers=headers)
        content.raise_for_status()
        
        soup = BeautifulSoup(content.content, 'html.parser')
        
        # Find the offensive stats table
        table = soup.find('table', {'id': 'offense'})
        if not table:
            print(f"No offensive stats table found for {team} {year}")
            return False
        
        # Extract table rows
        rows = table.find_all('tr')
        games_data = []
        
        for row in rows[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            if len(cells) > 5:  # Ensure it's a data row with enough cells
                game_data = [cell.text.strip() for cell in cells]
                games_data.append(game_data)
        
        if not games_data:
            print(f"No game data found for {team} {year}")
            return False
        
        # Create database connection
        db_path = os.path.join('ncaafDb', f'{team}-{year}-stats.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Create table with flexible columns based on actual data
        cur.execute("""CREATE TABLE IF NOT EXISTS Stats(
            Week TEXT, Day TEXT, Date TEXT, OT TEXT, Opp TEXT, Tm TEXT, Opp2 TEXT,
            Cmp TEXT, Att TEXT, PassYds TEXT, PassTD TEXT, Int TEXT, Sk TEXT, SkYds TEXT,
            PassYA TEXT, PassNYA TEXT, CmpPct TEXT, PasserRate TEXT, RushAtt TEXT, RushYds TEXT,
            RushYA TEXT, RushTD TEXT, FGM TEXT, FGA TEXT, XPM TEXT, XPA TEXT, Pnt TEXT,
            PuntYds TEXT, ThirdDownConv TEXT, ThirdDownAtt TEXT, FourthDownConv TEXT,
            FourthDownAtt TEXT, ToP TEXT)""")
        
        # Insert data - handle variable number of columns
        for game in games_data:
            # Pad the game data to match expected columns
            padded_game = game + [''] * (33 - len(game))
            try:
                cur.execute("""INSERT INTO Stats VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                          padded_game[:33])  # Ensure we only pass 33 values
            except Exception as e:
                print(f"Error inserting game: {e}")
                continue
                
        conn.commit()
        conn.close()
        
        print(f"Successfully stored {len(games_data)} games for {team} {year}")
        return True
        
    except Exception as e:
        print(f"Error scraping {team} {year}: {e}")
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

def get_team_gamelog(team, year):
    """
    Get NCAAF team gamelog
    """
    try:
        stats = get_team_stats(team, year)
        if stats and 'games' in stats:
            return stats['games']
        return []
    except Exception as e:
        logger.error(f"Error getting NCAAF team gamelog: {e}")
        return []
