import sqlite3
import datetime as dt
import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
import time

logger = logging.getLogger(__name__)

class NCAAFEventsManager:
    def __init__(self):
        self.sport = 'ncaaf'
        self.db_file = 'ncaaf_events.db'
        self.gameline_db_file = 'ncaaf_gamelines.db'
        self.init_database()
    
    def init_database(self):
        """Initialize NCAAF events database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_day DATE NOT NULL,
                start_time TEXT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                home_ml TEXT DEFAULT '---',
                away_ml TEXT DEFAULT '---',
                home_spread TEXT DEFAULT '---',
                away_spread TEXT DEFAULT '---',
                home_spread_odds TEXT DEFAULT '---',
                away_spread_odds TEXT DEFAULT '---',
                over_under TEXT DEFAULT '---',
                over_odds TEXT DEFAULT '---',
                under_odds TEXT DEFAULT '---',
                status TEXT DEFAULT 'TBD',
                source TEXT DEFAULT 'schedule',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_day, home_team, away_team)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("NCAAF events database initialized")

    def scrape_espn_schedule_simple(self, days: int = 30) -> List[Dict]:
        """
        Simple ESPN schedule scraper that focuses on getting real games
        """
        try:
            games = []
            current_year = dt.datetime.now().year
            
            # Try current season (2) and next season (3 if available)
            for season_type in [2, 3]:
                for week in range(1, 16):  # Try weeks 1-15
                    url = f"https://www.espn.com/college-football/schedule/_/week/{week}/year/{current_year}/seasontype/{season_type}"
                    
                    logger.info(f"Scraping ESPN week {week}, season {season_type}")
                    
                    try:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                        response = requests.get(url, headers=headers, timeout=10)
                        if response.status_code != 200:
                            continue
                            
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Look for schedule tables
                        tables = soup.find_all('table', class_='Table')
                        
                        for table in tables:
                            # Get date from table header
                            date_header = table.find_previous('div', class_='Table__Title')
                            if not date_header:
                                continue
                                
                            date_text = date_header.get_text().strip()
                            game_date = self._parse_simple_date(date_text, week, current_year)
                            
                            # Skip if too far in future
                            if not self._is_within_days(game_date, days):
                                continue
                            
                            # Parse game rows
                            rows = table.find_all('tr')[1:]  # Skip header row
                            
                            for row in rows:
                                try:
                                    # Get team cells - ESPN usually has team names in anchors
                                    team_cells = row.find_all('a', class_='AnchorLink')
                                    if len(team_cells) >= 2:
                                        away_team = self._clean_team_name(team_cells[0].get_text().strip())
                                        home_team = self._clean_team_name(team_cells[1].get_text().strip())
                                        
                                        if away_team and home_team:
                                            game_data = {
                                                'game_day': game_date.strftime('%Y-%m-%d'),
                                                'start_time': 'TBD',
                                                'home_team': home_team,
                                                'away_team': away_team,
                                                'source': 'espn'
                                            }
                                            games.append(game_data)
                                            logger.info(f"Found: {away_team} @ {home_team} on {game_date}")
                                            
                                except Exception as e:
                                    continue
                                    
                        time.sleep(1)  # Be respectful
                        
                    except Exception as e:
                        logger.debug(f"Error scraping week {week}: {e}")
                        continue
            
            logger.info(f"Found {len(games)} total games from ESPN")
            return games
            
        except Exception as e:
            logger.error(f"Error in simple ESPN scraper: {e}")
            return []

    def _parse_simple_date(self, date_text: str, week: int, year: int) -> dt.date:
        """Simple date parser"""
        try:
            # Remove "Week X - " prefix if present
            date_text = date_text.replace(f"Week {week} - ", "").strip()
            
            # Try to parse common formats
            for fmt in ['%A, %B %d', '%B %d']:
                try:
                    parsed = dt.datetime.strptime(date_text, fmt).date()
                    return parsed.replace(year=year)
                except:
                    continue
                    
            # Fallback: calculate from week (season starts late August)
            season_start = dt.date(year, 8, 26)  # Typical season start
            return season_start + dt.timedelta(weeks=week-1)
            
        except:
            return dt.date.today()

    def get_real_2025_schedule(self) -> List[Dict]:
        """Get the real 2025 schedule you provided"""
        games = []
        
        # Week 13 games for November 22, 2025
        week13_games = [
            ("Missouri", "Oklahoma", "11:00 AM"),
            ("Samford", "Texas A&M", "11:00 AM"),
            ("Louisville", "SMU", "11:00 AM"), 
            ("Rutgers", "Ohio State", "11:00 AM"),
            ("Miami", "Virginia Tech", "11:00 AM"),
            ("Charlotte", "Georgia", "11:45 AM"),
            ("Eastern Illinois", "Alabama", "1:00 PM"),
            ("South Florida", "UAB", "2:00 PM"),
            ("Arkansas", "Texas", "2:30 PM"),
            ("Kentucky", "Vanderbilt", "2:30 PM"),
            ("Michigan State", "Iowa", "2:30 PM"),
            ("Syracuse", "Notre Dame", "2:30 PM"),
            ("USC", "Oregon", "2:30 PM"),
            ("Kansas State", "Utah", "3:00 PM"),
        ]
        
        game_date = dt.date(2025, 11, 22)
        
        for away, home, time in week13_games:
            games.append({
                'game_day': game_date.strftime('%Y-%m-%d'),
                'start_time': time,
                'home_team': home,
                'away_team': away,
                'source': 'real_2025_schedule'
            })
        
        return games

    def get_schedule(self, days: int = 30) -> List[Dict]:
        """
        Main function to get NCAAF schedule
        Tries web scraping first, falls back to known 2025 schedule
        """
        logger.info(f"Getting NCAAF schedule for next {days} days")
        
        # Try to scrape from web
        games = self.scrape_espn_schedule_simple(days)
        
        # If no games found, use the real 2025 schedule
        if not games:
            logger.info("No games from web scraping, using real 2025 schedule")
            games = self.get_real_2025_schedule()
        
        # Remove duplicates
        unique_games = []
        seen = set()
        for game in games:
            key = (game['game_day'], game['home_team'], game['away_team'])
            if key not in seen:
                seen.add(key)
                unique_games.append(game)
        
        logger.info(f"Returning {len(unique_games)} unique games")
        return unique_games

    def _is_within_days(self, date: dt.date, days: int) -> bool:
        """Check if date is within the next X days"""
        today = dt.date.today()
        future_date = today + dt.timedelta(days=days)
        return today <= date <= future_date

    def _clean_team_name(self, team_name: str) -> str:
        """Clean team names"""
        if not team_name:
            return ""
        
        # Remove rankings
        team_name = team_name.lstrip('1234567890 ')
        
        # Standardize names
        name_map = {
            'Ohio St.': 'Ohio State',
            'Michigan St.': 'Michigan State', 
            'Kansas St.': 'Kansas State',
            'Miami (FL)': 'Miami',
            'Florida St.': 'Florida State',
        }
        
        return name_map.get(team_name, team_name)

    # KEEP YOUR EXISTING DATABASE METHODS - THEY WORK FINE

    def get_existing_gamelines(self, days: int = 7) -> List[Dict]:
        """Get existing NCAAF gamelines from gamelines database"""
        try:
            conn = sqlite3.connect(self.gameline_db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT game_day, start_time, home_team, away_team, 
                       home_ml, away_ml, home_spread, away_spread,
                       home_spread_odds, away_spread_odds, over_under,
                       over_odds, under_odds, source
                FROM gamelines 
                WHERE game_day BETWEEN date('now') AND date('now', ?)
                ORDER BY game_day, start_time
            ''', (f'+{days} days',))
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            logger.info(f"Found {len(results)} existing NCAAF gamelines")
            return results
            
        except Exception as e:
            logger.error(f"Error reading NCAAF gamelines: {e}")
            return []

    def update_events(self, days: int = 30, use_gamelines: bool = False) -> int:
        """
        Update NCAAF events with schedule data
        """
        try:
            # Get scheduled games
            scheduled_games = self.get_schedule(days)
            
            if use_gamelines:
                # Get existing gamelines and merge
                existing_gamelines = self.get_existing_gamelines(days)
                merged_events = self._merge_events(scheduled_games, existing_gamelines)
            else:
                # Only use schedule data, create TBD events
                merged_events = self._create_tbd_events(scheduled_games)
            
            # Update database
            updated_count = self._update_database(merged_events)
            
            # Cleanup old events
            self.cleanup_old_events()
            
            logger.info(f"Successfully updated {updated_count} NCAAF events")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating NCAAF events: {e}")
            return 0

    def _create_tbd_events(self, scheduled_games: List[Dict]) -> List[Dict]:
        """Create TBD events from scheduled games"""
        return [{
            'game_day': game['game_day'],
            'start_time': game.get('start_time', 'TBD'),
            'home_team': game['home_team'],
            'away_team': game['away_team'],
            'home_ml': '---',
            'away_ml': '---',
            'home_spread': '---',
            'away_spread': '---',
            'home_spread_odds': '---',
            'away_spread_odds': '---',
            'over_under': '---',
            'over_odds': '---',
            'under_odds': '---',
            'status': 'TBD',
            'source': game.get('source', 'schedule')
        } for game in scheduled_games]

    def _merge_events(self, scheduled_games: List[Dict], existing_gamelines: List[Dict]) -> List[Dict]:
        """Merge scheduled games with existing gamelines"""
        merged_events = self._create_tbd_events(scheduled_games)
        
        # Update with existing gamelines
        gameline_map = {(gl['game_day'], gl['home_team'], gl['away_team']): gl for gl in existing_gamelines}
        
        for event in merged_events:
            key = (event['game_day'], event['home_team'], event['away_team'])
            if key in gameline_map:
                gl = gameline_map[key]
                event.update({
                    'home_ml': gl.get('home_ml', '---'),
                    'away_ml': gl.get('away_ml', '---'),
                    'home_spread': gl.get('home_spread', '---'),
                    'away_spread': gl.get('away_spread', '---'),
                    'home_spread_odds': gl.get('home_spread_odds', '---'),
                    'away_spread_odds': gl.get('away_spread_odds', '---'),
                    'over_under': gl.get('over_under', '---'),
                    'over_odds': gl.get('over_odds', '---'),
                    'under_odds': gl.get('under_odds', '---'),
                    'status': 'OPEN',
                    'source': gl.get('source', 'unknown')
                })
        
        return merged_events

    def _update_database(self, events: List[Dict]) -> int:
        """Update events in the database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        updated_count = 0
        
        try:
            for event in events:
                cursor.execute('''
                    INSERT OR REPLACE INTO events 
                    (game_day, start_time, home_team, away_team, 
                     home_ml, away_ml, home_spread, away_spread, 
                     home_spread_odds, away_spread_odds, over_under, 
                     over_odds, under_odds, status, source, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    event['game_day'],
                    event.get('start_time'),
                    event['home_team'],
                    event['away_team'],
                    event.get('home_ml', '---'),
                    event.get('away_ml', '---'),
                    event.get('home_spread', '---'),
                    event.get('away_spread', '---'),
                    event.get('home_spread_odds', '---'),
                    event.get('away_spread_odds', '---'),
                    event.get('over_under', '---'),
                    event.get('over_odds', '---'),
                    event.get('under_odds', '---'),
                    event.get('status', 'TBD'),
                    event.get('source', 'schedule')
                ))
                updated_count += 1
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return updated_count

    def get_events(self, days: int = 7) -> List[Dict]:
        """Get NCAAF events from database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM events 
                WHERE game_day BETWEEN date('now') AND date('now', ?)
                ORDER BY game_day, start_time
            ''', (f'+{days} days',))
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
            
        except Exception as e:
            logger.error(f"Error reading events: {e}")
            return []
        finally:
            conn.close()

    def get_upcoming_tbd_events(self, days: int = 7) -> List[Dict]:
        """Get upcoming events without gamelines"""
        try:
            scheduled_games = self.get_schedule(days)
            existing_gamelines = self.get_existing_gamelines(days)
            
            # Create set of games that already have gamelines
            existing_games_set = {
                (gl['game_day'], gl['home_team'], gl['away_team']) 
                for gl in existing_gamelines
            }
            
            # Filter scheduled games to only include those without gamelines
            tbd_events = []
            for game in scheduled_games:
                game_key = (game['game_day'], game['home_team'], game['away_team'])
                if game_key not in existing_games_set:
                    tbd_events.append({
                        'game_day': game['game_day'],
                        'start_time': game.get('start_time', 'TBD'),
                        'home_team': game['home_team'],
                        'away_team': game['away_team'],
                        'home_ml': '',
                        'away_ml': '',
                        'home_spread': '',
                        'away_spread': '',
                        'home_spread_odds': '',
                        'away_spread_odds': '',
                        'over_under': '',
                        'over_odds': '',
                        'under_odds': '',
                        'status': 'TBD',
                        'source': game.get('source', 'schedule')
                    })
            
            logger.info(f"Found {len(tbd_events)} TBD events without gamelines")
            return tbd_events
            
        except Exception as e:
            logger.error(f"Error getting TBD events: {e}")
            return []

    def cleanup_old_events(self):
        """Remove old events"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM events WHERE game_day < date('now')")
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted_count} old events")
        except Exception as e:
            logger.error(f"Error cleaning up events: {e}")
        finally:
            conn.close()

# Global instance
ncaaf_events_manager = NCAAFEventsManager()
