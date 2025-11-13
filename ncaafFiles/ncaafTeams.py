import datetime as dt
import sqlite3
import pandas as pd
import os

dirname = os.path.dirname(__file__)

now = dt.datetime.now()
todays_date = dt.date(now.year, now.month, now.day)

class NcaafTeam:
    w = 0
    l = 0
    
    def __init__(self, Name='', **kwargs):
        self.name = Name
        # Initialize all stats attributes
        stats_attrs = [
            'Week', 'Day', 'Date', 'OT', 'Opp', 'Tm', 'Opp2', 'Cmp', 'Att', 
            'PassYds', 'PassTD', 'Int', 'Sk', 'SkYds', 'PassYA', 'PassNYA', 
            'CmpPct', 'PasserRate', 'RushAtt', 'RushYds', 'RushYA', 'RushTD',
            'FGM', 'FGA', 'XPM', 'XPA', 'Pnt', 'PuntYds', 'ThirdDownConv',
            'ThirdDownAtt', 'FourthDownConv', 'FourthDownAtt', 'ToP'
        ]
        
        for attr in stats_attrs:
            setattr(self, attr.lower(), '')
            
        # Set attributes from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key.lower()):
                setattr(self, key.lower(), value)

    def get_stats(self, team, year):
        """Get all stats for a team"""
        self.w = 0
        self.l = 0
        filename = os.path.join(dirname, f'ncaafDb/{team}-{year}-stats.db')
        
        if not os.path.exists(filename):
            print(f"Database file not found: {filename}")
            return None
            
        conn = sqlite3.connect(filename)
        cur = conn.cursor()
        
        try:
            cur.execute('SELECT * FROM Stats')
            rows = cur.fetchall()
            conn.close()
            
            if not rows:
                return None
                
            # Return both team stats and opponent stats
            mid_point = len(rows) // 2
            selected_team = rows[:mid_point]
            opp_team = rows[mid_point:]
            
            return [selected_team, opp_team]
            
        except Exception as e:
            print(f"Error reading stats: {e}")
            conn.close()
            return None

    def last2(self, team, year):
        """Get last 2 games stats"""
        return self._get_recent_games(team, year, 2)
    
    def last4(self, team, year):
        """Get last 4 games stats"""
        return self._get_recent_games(team, year, 4)
    
    def last8(self, team, year):
        """Get last 8 games stats"""
        return self._get_recent_games(team, year, 8)

    def _get_recent_games(self, team, year, num_games):
        """Helper method to get recent games"""
        self.w = 0
        self.l = 0
        
        filename = os.path.join(dirname, f'ncaafDb/{team}-{year}-stats.db')
        
        if not os.path.exists(filename):
            print(f"Database file not found: {filename}")
            return False
            
        conn = sqlite3.connect(filename)
        
        try:
            # Read data into pandas DataFrame
            query = "SELECT * FROM Stats"
            team_stats = pd.read_sql_query(query, conn)
            conn.close()
            
            if len(team_stats) < num_games:
                print(f"Not enough games found. Have {len(team_stats)}, need {num_games}")
                return False
            
            # Define column names based on database structure
            columns = [
                'Week', 'Day', 'Date', 'OT', 'Opp', 'Tm', 'Opp2', 'Cmp', 'Att',
                'PassYds', 'PassTD', 'Int', 'Sk', 'SkYds', 'PassYA', 'PassNYA',
                'CmpPct', 'PasserRate', 'RushAtt', 'RushYds', 'RushYA', 'RushTD',
                'FGM', 'FGA', 'XPM', 'XPA', 'Pnt', 'PuntYds', 'ThirdDownConv',
                'ThirdDownAtt', 'FourthDownConv', 'FourthDownAtt', 'ToP'
            ]
            
            team_stats.columns = columns
            
            # Get recent games
            recent_games = team_stats.tail(num_games)
            
            # Set attributes for recent games
            for col in columns:
                setattr(self, col.lower(), recent_games[col].tolist())
            
            return True
            
        except Exception as e:
            print(f"Error getting recent games: {e}")
            conn.close()
            return False

    def calculate_win_loss(self, team, year):
        """Calculate win-loss record from database"""
        filename = os.path.join(dirname, f'ncaafDb/{team}-{year}-stats.db')
        
        if not os.path.exists(filename):
            return 0, 0
            
        conn = sqlite3.connect(filename)
        
        try:
            team_stats = pd.read_sql_query("SELECT * FROM Stats", conn)
            conn.close()
            
            # Simple win-loss calculation based on scores
            # This would need adjustment based on actual data structure
            wins = 0
            losses = 0
            
            for _, game in team_stats.iterrows():
                try:
                    tm_score = int(game['Tm']) if game['Tm'] and game['Tm'].isdigit() else 0
                    opp_score = int(game['Opp2']) if game['Opp2'] and game['Opp2'].isdigit() else 0
                    
                    if tm_score > opp_score:
                        wins += 1
                    elif tm_score < opp_score:
                        losses += 1
                except (ValueError, KeyError):
                    continue
            
            self.w = wins
            self.l = losses
            return wins, losses
            
        except Exception as e:
            print(f"Error calculating win-loss: {e}")
            return 0, 0

# Create instance
ncaaf_team = NcaafTeam()
