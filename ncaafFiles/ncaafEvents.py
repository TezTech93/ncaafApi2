import sqlite3
import datetime as dt
import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
import re

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
        logger.info("Integrated NCAAF events database initialized")
    
    def scrape_fbschedules(self, days: int = 7) -> List[Dict]:
        """Scrape NCAAF schedule from FBSchedules.com"""
        try:
            upcoming_dates = self._get_upcoming_dates(days)
            games = []
            
            # FBSchedules.com has a clean structure for college football schedules
            base_url = "https://fbschedules.com/college-football-schedule/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(base_url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for schedule tables or game listings
            # FBSchedules.com typically uses tables or divs with clear class names
            schedule_tables = soup.find_all('table', class_=lambda x: x and 'schedule' in x.lower())
            
            if not schedule_tables:
                # Alternative: look for div-based schedules
                schedule_sections = soup.find_all('div', class_=lambda x: x and 'schedule' in x.lower())
                
            for table in schedule_tables:
                try:
                    rows = table.find_all('tr')[1:]  # Skip header row
                    
                    for row in rows:
                        try:
                            cells = row.find_all('td')
                            if len(cells) >= 3:
                                # Extract date, away team, and home team
                                date_cell = cells[0].text.strip()
                                teams_cell = cells[1].text.strip()
                                
                                # Parse teams (usually format: "Away Team @ Home Team")
                                if '@' in teams_cell:
                                    teams = teams_cell.split('@')
                                    away_team = self._clean_fbschedules_team(teams[0].strip())
                                    home_team = self._clean_fbschedules_team(teams[1].strip())
                                    
                                    # Parse date
                                    game_date = self._parse_fbschedules_date(date_cell)
                                    
                                    if game_date and away_team and home_team:
                                        if self._is_within_days(game_date, days):
                                            game_data = {
                                                'game_day': game_date.strftime('%Y-%m-%d'),
                                                'start_time': 'TBD',
                                                'home_team': home_team,
                                                'away_team': away_team,
                                                'source': 'fbschedules'
                                            }
                                            games.append(game_data)
                        except Exception as e:
                            logger.debug(f"Error parsing FBSchedules row: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error parsing FBSchedules table: {e}")
                    continue
            
            logger.info(f"Found {len(games)} games from FBSchedules.com")
            return games
            
        except Exception as e:
            logger.error(f"Error scraping FBSchedules.com: {e}")
            return []
    
    def scrape_espn_schedule(self, days: int = 7) -> List[Dict]:
        """Fallback: Scrape NCAAF schedule from ESPN"""
        try:
            upcoming_dates = self._get_upcoming_dates(days)
            games = []
            
            for target_date in upcoming_dates:
                url = f"https://www.espn.com/college-football/schedule/_/date/{target_date.strftime('%Y%m%d')}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                game_rows = soup.find_all('tr', class_=lambda x: x and 'away' in str(x))
                
                for row in game_rows:
                    try:
                        teams = row.find_all('a', class_='team-name')
                        if len(teams) >= 2:
                            away_team = self._clean_team_name(teams[0].text.strip())
                            home_team = self._clean_team_name(teams[1].text.strip())
                            
                            if away_team and home_team:
                                game_data = {
                                    'game_day': target_date.strftime('%Y-%m-%d'),
                                    'start_time': 'TBD',
                                    'home_team': home_team,
                                    'away_team': away_team,
                                    'source': 'espn'
                                }
                                games.append(game_data)
                    except Exception as e:
                        logger.debug(f"Error parsing ESPN game row: {e}")
                        continue
            
            logger.info(f"Found {len(games)} games from ESPN")
            return games
            
        except Exception as e:
            logger.error(f"Error scraping ESPN schedule: {e}")
            return []
    
    def get_schedule(self, days: int = 7) -> List[Dict]:
        """Get NCAAF schedule - try FBSchedules first, then ESPN as fallback"""
        # Try FBSchedules.com first (preferred source)
        games = self.scrape_fbschedules(days)
        
        # If FBSchedules returns no games, fall back to ESPN
        if not games:
            logger.info("FBSchedules.com returned no games, trying ESPN...")
            games = self.scrape_espn_schedule(days)
        
        return games
    
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
    
    def update_events(self, days: int = 7, use_gamelines: bool = False) -> int:
        """
        Update NCAAF events with schedule and optional gamelines
        
        Args:
            days: Number of days to look ahead
            use_gamelines: If True, merge with existing gamelines. If False, only use schedule data.
        """
        try:
            # Get scheduled games from FBSchedules.com (or ESPN fallback)
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
            
            logger.info(f"Successfully updated {updated_count} NCAAF events (use_gamelines: {use_gamelines})")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating NCAAF events: {e}")
            return 0
    
    def _create_tbd_events(self, scheduled_games: List[Dict]) -> List[Dict]:
        """Create TBD events from scheduled games only"""
        tbd_events = []
        
        for game in scheduled_games:
            tbd_event = {
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
            }
            tbd_events.append(tbd_event)
        
        return tbd_events
    
    def _merge_events(self, scheduled_games: List[Dict], existing_gamelines: List[Dict]) -> List[Dict]:
        """Merge scheduled games with existing gamelines"""
        merged_events = []
        
        # Create TBD events for all scheduled games first
        for game in scheduled_games:
            tbd_event = {
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
            }
            merged_events.append(tbd_event)
        
        # Update with existing gamelines where available
        for gameline in existing_gamelines:
            for event in merged_events:
                if (event['home_team'] == gameline['home_team'] and 
                    event['away_team'] == gameline['away_team'] and 
                    event['game_day'] == gameline['game_day']):
                    
                    # Update with actual gameline data
                    event.update({
                        'home_ml': gameline.get('home_ml', '---'),
                        'away_ml': gameline.get('away_ml', '---'),
                        'home_spread': gameline.get('home_spread', '---'),
                        'away_spread': gameline.get('away_spread', '---'),
                        'home_spread_odds': gameline.get('home_spread_odds', '---'),
                        'away_spread_odds': gameline.get('away_spread_odds', '---'),
                        'over_under': gameline.get('over_under', '---'),
                        'over_odds': gameline.get('over_odds', '---'),
                        'under_odds': gameline.get('under_odds', '---'),
                        'status': 'OPEN',
                        'source': gameline.get('source', 'unknown')
                    })
                    break
        
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
            logger.error(f"Error updating NCAAF events database: {e}")
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
            logger.error(f"Error reading NCAAF events: {e}")
            return []
        finally:
            conn.close()
    
    def cleanup_old_events(self):
        """Remove NCAAF events from past dates"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM events WHERE game_day < date('now')")
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted_count} old NCAAF events")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old NCAAF events: {e}")
            return 0
        finally:
            conn.close()
    
    def _get_upcoming_dates(self, days: int):
        """Get dates for the next X days"""
        today = dt.date.today()
        return [today + dt.timedelta(days=i) for i in range(days)]
    
    def _parse_fbschedules_date(self, date_text: str) -> dt.date:
        """Parse date from FBSchedules.com format"""
        try:
            # FBSchedules.com typically uses formats like "Saturday, September 2, 2023"
            # or "Sat, Sep 2"
            date_text = date_text.strip()
            
            # Remove day of week if present
            if ',' in date_text:
                # Format: "Saturday, September 2, 2023"
                date_parts = date_text.split(',', 1)
                if len(date_parts) > 1:
                    date_text = date_parts[1].strip()
            
            # Try different date formats
            formats = [
                '%B %d, %Y',  # "September 2, 2023"
                '%b %d, %Y',   # "Sep 2, 2023"
                '%B %d',       # "September 2" (current year assumed)
                '%b %d',       # "Sep 2" (current year assumed)
            ]
            
            for fmt in formats:
                try:
                    parsed_date = dt.datetime.strptime(date_text, fmt).date()
                    # If no year in format, assume current year
                    if parsed_date.year == 1900:
                        parsed_date = parsed_date.replace(year=dt.date.today().year)
                    return parsed_date
                except ValueError:
                    continue
            
            # If all parsing fails, return today's date
            return dt.date.today()
            
        except Exception as e:
            logger.debug(f"Error parsing FBSchedules date '{date_text}': {e}")
            return dt.date.today()
    
    def _clean_fbschedules_team(self, team_name: str) -> str:
        """Clean team name from FBSchedules.com"""
        # Remove rankings and extra text
        team_name = re.sub(r'\(\d+\)', '', team_name)  # Remove (1), (2), etc.
        team_name = re.sub(r'#\d+', '', team_name)     # Remove #1, #2, etc.
        team_name = team_name.strip()
        
        # Standardize common team name variations
        team_mappings = {
            'Alabama Crimson Tide': 'Alabama',
            'Ohio State Buckeyes': 'Ohio State', 
            'Clemson Tigers': 'Clemson',
            'Georgia Bulldogs': 'Georgia',
            'Oklahoma Sooners': 'Oklahoma',
            'Notre Dame Fighting Irish': 'Notre Dame',
            'Michigan Wolverines': 'Michigan',
            'Texas Longhorns': 'Texas',
            'LSU Tigers': 'LSU',
            'Florida Gators': 'Florida',
            # Add more mappings as needed
        }
        
        return team_mappings.get(team_name, team_name)
    
    def _clean_team_name(self, team_name: str) -> str:
        """Clean team name from ESPN (fallback)"""
        return team_name

# Global instance
ncaaf_events_manager = NCAAFEventsManager()
