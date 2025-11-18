import sqlite3
import datetime as dt
import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
import re
import time
import json

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

    def scrape_espn_schedule_real(self, days: int = 7) -> List[Dict]:
        """
        Scrape real NCAAF schedule from ESPN with improved parsing
        Targets the actual schedule structure used by ESPN
        """
        try:
            games = []
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # Get current year and calculate weeks
            current_year = dt.datetime.now().year
            current_date = dt.datetime.now()
            
            # Try multiple weeks around current date
            weeks_to_try = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
            
            for week in weeks_to_try:
                try:
                    url = f"https://www.espn.com/college-football/schedule/_/week/{week}/year/{current_year}/seasontype/2"
                    logger.info(f"Scraping ESPN week {week}, year {current_year}")
                    
                    time.sleep(1)  # Be respectful
                    
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Parse games from this week
                    week_games = self._parse_espn_schedule_page(soup, week, current_year, days)
                    games.extend(week_games)
                    
                    # If we found games and we're beyond current week, we can stop
                    if week_games and week > self._get_current_week():
                        break
                        
                except Exception as e:
                    logger.debug(f"Error scraping ESPN week {week}: {e}")
                    continue
            
            # Also try the main schedule page
            try:
                main_url = f"https://www.espn.com/college-football/schedule"
                response = requests.get(main_url, headers=headers, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    main_games = self._parse_espn_main_schedule(soup, days)
                    games.extend(main_games)
            except Exception as e:
                logger.debug(f"Error scraping ESPN main schedule: {e}")
            
            # Remove duplicates
            unique_games = []
            seen_games = set()
            for game in games:
                game_key = (game['game_day'], game['home_team'], game['away_team'])
                if game_key not in seen_games:
                    seen_games.add(game_key)
                    unique_games.append(game)
            
            logger.info(f"Found {len(unique_games)} unique real games from ESPN")
            return unique_games
            
        except Exception as e:
            logger.error(f"Error scraping real ESPN schedule: {e}")
            return []

    def _parse_espn_schedule_page(self, soup: BeautifulSoup, week: int, year: int, days: int) -> List[Dict]:
        """Parse ESPN schedule page for specific week"""
        games = []
        
        try:
            # Find schedule tables - ESPN uses tables with specific classes
            schedule_tables = soup.find_all('table', class_='Table')
            
            for table in schedule_tables:
                try:
                    # Get the date from table context
                    date_header = table.find_previous('div', class_='Table__Title')
                    table_date = None
                    
                    if date_header:
                        date_text = date_header.get_text().strip()
                        table_date = self._parse_espn_date_from_text(date_text, week, year)
                    
                    if not table_date:
                        # Default to calculating date from week
                        table_date = self._calculate_date_from_week(week, year)
                    
                    # Skip if date is too far in the future
                    if not self._is_within_days(table_date, days):
                        continue
                    
                    # Parse game rows
                    rows = table.find_all('tr', class_=lambda x: x and 'Table__TR' in x)
                    
                    for row in rows:
                        try:
                            # Skip header rows
                            if not row.find('td'):
                                continue
                            
                            game_data = self._parse_espn_game_row(row, table_date)
                            if game_data and game_data['home_team'] and game_data['away_team']:
                                games.append(game_data)
                                
                        except Exception as e:
                            logger.debug(f"Error parsing ESPN game row: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error parsing ESPN schedule table: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing ESPN schedule page: {e}")
        
        return games

    def _parse_espn_main_schedule(self, soup: BeautifulSoup, days: int) -> List[Dict]:
        """Parse ESPN main schedule page"""
        games = []
        
        try:
            # Look for schedule containers
            schedule_sections = soup.find_all('div', class_=lambda x: x and 'Schedule' in x)
            
            for section in schedule_sections:
                try:
                    # Extract date from section
                    date_element = section.find(['h2', 'h3', 'div'], class_=lambda x: x and 'date' in str(x).lower())
                    section_date = dt.date.today()
                    
                    if date_element:
                        date_text = date_element.get_text().strip()
                        section_date = self._parse_espn_date_from_text(date_text, 1, dt.datetime.now().year)
                    
                    # Find game elements
                    game_elements = section.find_all('div', class_=lambda x: x and 'game' in str(x).lower())
                    
                    for game_elem in game_elements:
                        try:
                            teams = game_elem.find_all('span', class_=lambda x: x and 'team' in str(x).lower())
                            if len(teams) >= 2:
                                away_team = self._clean_team_name(teams[0].get_text().strip())
                                home_team = self._clean_team_name(teams[1].get_text().strip())
                                
                                if away_team and home_team and self._is_within_days(section_date, days):
                                    game_data = {
                                        'game_day': section_date.strftime('%Y-%m-%d'),
                                        'start_time': 'TBD',
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'source': 'espn_main'
                                    }
                                    games.append(game_data)
                        except Exception as e:
                            logger.debug(f"Error parsing ESPN main schedule game: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error parsing ESPN main schedule section: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing ESPN main schedule: {e}")
        
        return games

    def _parse_espn_game_row(self, row, game_date: dt.date) -> Dict:
        """Parse individual game row from ESPN schedule"""
        try:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 3:
                return {}
            
            # ESPN typically has: teams cell, time/network cell, etc.
            teams_cell = cells[0]
            time_network_cell = cells[1] if len(cells) > 1 else None
            
            # Extract teams - look for team links or spans
            team_links = teams_cell.find_all('a', class_=lambda x: x and 'team' in str(x).lower())
            team_spans = teams_cell.find_all('span', class_=lambda x: x and 'team' in str(x).lower())
            
            teams = []
            if team_links:
                teams = [link.get_text().strip() for link in team_links]
            elif team_spans:
                teams = [span.get_text().strip() for span in team_spans]
            else:
                # Fallback: split by @ symbol or just take text
                cell_text = teams_cell.get_text().strip()
                if '@' in cell_text:
                    teams = [t.strip() for t in cell_text.split('@')]
                else:
                    # Assume it's just team names separated by space
                    teams = [t.strip() for t in re.split(r'\s+', cell_text) if t.strip()]
            
            if len(teams) >= 2:
                away_team = self._clean_team_name(teams[0])
                home_team = self._clean_team_name(teams[1])
                
                # Extract time if available
                start_time = 'TBD'
                if time_network_cell:
                    time_text = time_network_cell.get_text().strip()
                    if time_text and any(x in time_text.lower() for x in ['am', 'pm', 'et', 'ct', 'pt']):
                        start_time = time_text.split('\n')[0].strip()
                
                return {
                    'game_day': game_date.strftime('%Y-%m-%d'),
                    'start_time': start_time,
                    'home_team': home_team,
                    'away_team': away_team,
                    'source': 'espn_weekly'
                }
        
        except Exception as e:
            logger.debug(f"Error parsing ESPN game row: {e}")
        
        return {}

    def _parse_espn_date_from_text(self, date_text: str, week: int, year: int) -> dt.date:
        """Parse date from ESPN date text"""
        try:
            # Common ESPN formats: "Saturday, November 22", "Sat, Nov 22", "November 22"
            date_text = date_text.strip()
            
            # Remove day of week if present
            if ',' in date_text:
                parts = date_text.split(',', 1)
                if len(parts) > 1:
                    date_text = parts[1].strip()
            
            # Try different date formats
            formats = [
                '%B %d, %Y',
                '%b %d, %Y', 
                '%B %d',
                '%b %d'
            ]
            
            for fmt in formats:
                try:
                    parsed_date = dt.datetime.strptime(date_text, fmt).date()
                    if parsed_date.year == 1900:
                        parsed_date = parsed_date.replace(year=year)
                    return parsed_date
                except ValueError:
                    continue
            
            # Fallback to week-based calculation
            return self._calculate_date_from_week(week, year)
            
        except Exception as e:
            logger.debug(f"Error parsing ESPN date '{date_text}': {e}")
            return self._calculate_date_from_week(week, year)

    def _calculate_date_from_week(self, week: int, year: int) -> dt.date:
        """Calculate approximate date from week number"""
        try:
            # NCAAF season typically starts around late August
            season_start = dt.date(year, 8, 20)  # Approximate season start
            week_date = season_start + dt.timedelta(weeks=week-1)
            return week_date
        except:
            return dt.date.today()

    def _get_current_week(self) -> int:
        """Get current week of NCAAF season"""
        try:
            # Simple calculation - season starts late August
            season_start = dt.date(dt.datetime.now().year, 8, 20)
            days_since_start = (dt.date.today() - season_start).days
            return max(1, (days_since_start // 7) + 1)
        except:
            return 1

    def scrape_cbssports_schedule(self, days: int = 7) -> List[Dict]:
        """Alternative: Scrape from CBS Sports"""
        try:
            games = []
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            url = "https://www.cbssports.com/college-football/schedule/"
            logger.info(f"Scraping CBS Sports schedule")
            
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # CBS Sports structure may vary, look for schedule elements
            schedule_sections = soup.find_all('div', class_=lambda x: x and 'schedule' in str(x).lower())
            
            for section in schedule_sections:
                try:
                    # Extract date
                    date_element = section.find(['h2', 'h3', 'strong'])
                    section_date = dt.date.today()
                    
                    if date_element:
                        date_text = date_element.get_text().strip()
                        section_date = self._parse_generic_date(date_text)
                    
                    # Find game rows
                    game_rows = section.find_all('tr', class_=lambda x: x and 'row' in str(x))
                    
                    for row in game_rows:
                        try:
                            teams = row.find_all('a', class_=lambda x: x and 'team' in str(x))
                            if len(teams) >= 2:
                                away_team = self._clean_team_name(teams[0].get_text().strip())
                                home_team = self._clean_team_name(teams[1].get_text().strip())
                                
                                if away_team and home_team and self._is_within_days(section_date, days):
                                    game_data = {
                                        'game_day': section_date.strftime('%Y-%m-%d'),
                                        'start_time': 'TBD', 
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'source': 'cbssports'
                                    }
                                    games.append(game_data)
                        except Exception as e:
                            logger.debug(f"Error parsing CBS Sports game row: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error parsing CBS Sports section: {e}")
                    continue
            
            logger.info(f"Found {len(games)} games from CBS Sports")
            return games
            
        except Exception as e:
            logger.error(f"Error scraping CBS Sports: {e}")
            return []

    def _parse_generic_date(self, date_text: str) -> dt.date:
        """Parse generic date format"""
        try:
            formats = [
                '%A, %B %d, %Y',
                '%B %d, %Y',
                '%b %d, %Y',
                '%m/%d/%Y'
            ]
            
            for fmt in formats:
                try:
                    return dt.datetime.strptime(date_text, fmt).date()
                except ValueError:
                    continue
        except:
            pass
        return dt.date.today()

    def get_real_schedule(self, days: int = 7) -> List[Dict]:
        """
        Main function to get real NCAAF schedule
        Tries multiple sources to get actual games
        """
        logger.info(f"Getting real NCAAF schedule for next {days} days")
        
        games = []
        
        # Try ESPN first (most reliable)
        espn_games = self.scrape_espn_schedule_real(days)
        games.extend(espn_games)
        
        # If no games from ESPN, try CBS Sports
        if not games:
            logger.info("No games from ESPN, trying CBS Sports...")
            cbs_games = self.scrape_cbssports_schedule(days)
            games.extend(cbs_games)
        
        # If still no games, use the real Week 13 2025 schedule you provided
        if not games:
            logger.info("No games from web sources, using real 2025 Week 13 schedule")
            games = self._get_real_2025_week13_schedule(days)
        
        # Remove duplicates
        unique_games = []
        seen_games = set()
        for game in games:
            game_key = (game['game_day'], game['home_team'], game['away_team'])
            if game_key not in seen_games:
                seen_games.add(game_key)
                unique_games.append(game)
        
        logger.info(f"Found {len(unique_games)} real NCAAF games")
        return unique_games

    def _get_real_2025_week13_schedule(self, days: int = 7) -> List[Dict]:
        """Get the real Week 13 2025 schedule you provided"""
        games = []
        
        # Week 13 games for November 22, 2025
        week13_games = [
            # Format: (away_team, home_team, time)
            ("Missouri", "Oklahoma", "11:00 AM CST"),
            ("Samford", "Texas A&M", "11:00 AM CST"),
            ("Louisville", "SMU", "11:00 AM CST"),
            ("Rutgers", "Ohio St.", "11:00 AM CST"),
            ("Miami (FL)", "Virginia Tech", "11:00 AM CST"),
            ("Charlotte", "Georgia", "11:45 AM CST"),
            ("Eastern Illinois", "Alabama", "1:00 PM CST"),
            ("South Florida", "UAB", "2:00 PM CST"),
            ("Arkansas", "Texas", "2:30 PM CST"),
            ("Kentucky", "Vanderbilt", "2:30 PM CST"),
            ("Michigan St.", "Iowa", "2:30 PM CST"),
            ("Syracuse", "Notre Dame", "2:30 PM CST"),
            ("USC", "Oregon", "2:30 PM CST"),
            ("Kansas St.", "Utah", "3:00 PM CST"),
        ]
        
        # Set game date to November 22, 2025
        game_date = dt.date(2025, 11, 22)
        
        # Only include if within requested days
        if self._is_within_days(game_date, days):
            for away, home, time in week13_games:
                games.append({
                    'game_day': game_date.strftime('%Y-%m-%d'),
                    'start_time': time,
                    'home_team': self._clean_team_name(home),
                    'away_team': self._clean_team_name(away),
                    'source': 'real_2025_week13'
                })
        
        return games

    def _is_within_days(self, date: dt.date, days: int) -> bool:
        """Check if date is within the next X days"""
        today = dt.date.today()
        end_date = today + dt.timedelta(days=days)
        return today <= date <= end_date

    def _clean_team_name(self, team_name: str) -> str:
        """Clean and standardize team names"""
        if not team_name:
            return ""
        
        # Remove rankings like "11" from "11 Oklahoma"
        team_name = re.sub(r'^\d+\s+', '', team_name)
        
        # Standardize common team name variations
        team_mappings = {
            'Ohio St.': 'Ohio State',
            'Miami (FL)': 'Miami',
            'Michigan St.': 'Michigan State',
            'Kansas St.': 'Kansas State',
            'Notre Dame': 'Notre Dame',
            'Alabama': 'Alabama',
            'Georgia': 'Georgia',
            'Texas': 'Texas',
            'Oklahoma': 'Oklahoma',
            'USC': 'USC',
            'Oregon': 'Oregon',
            'LSU': 'LSU',
            'Michigan': 'Michigan',
            'Penn State': 'Penn State',
            'Florida State': 'Florida State',
            'Clemson': 'Clemson',
            'Tennessee': 'Tennessee',
            'Texas A&M': 'Texas A&M',
            'Utah': 'Utah',
            'Iowa': 'Iowa',
            'Wisconsin': 'Wisconsin',
            'Auburn': 'Auburn',
            'Florida': 'Florida',
            'Washington': 'Washington',
            'UCLA': 'UCLA',
            'Arkansas': 'Arkansas',
            'Kentucky': 'Kentucky',
            'Vanderbilt': 'Vanderbilt',
            'Syracuse': 'Syracuse',
            'Rutgers': 'Rutgers',
            'Louisville': 'Louisville',
            'SMU': 'SMU',
            'Virginia Tech': 'Virginia Tech',
            'Charlotte': 'Charlotte',
            'South Florida': 'South Florida',
            'UAB': 'UAB',
            'Eastern Illinois': 'Eastern Illinois',
            'Samford': 'Samford',
            'Missouri': 'Missouri',
        }
        
        return team_mappings.get(team_name, team_name)

    # UPDATE YOUR EXISTING get_schedule METHOD TO USE REAL GAMES:
    def get_schedule(self, days: int = 7) -> List[Dict]:
        """Get NCAAF schedule - uses real games instead of mock data"""
        return self.get_real_schedule(days)

    # KEEP ALL YOUR EXISTING DATABASE METHODS (they remain the same):
    # get_existing_gamelines, update_events, _create_tbd_events, _merge_events,
    # _update_database, get_events, cleanup_old_events, etc.
    
    def scrape_fbschedules(self, days: int = 7) -> List[Dict]:
        """Scrape NCAAF schedule from FBSchedules.com with improved parsing"""
        try:
            games = []
            
            # FBSchedules.com has different pages for different time periods
            base_urls = [
                "https://fbschedules.com/college-football-schedule/",
                "https://fbschedules.com/college-football-schedule/this-week/",
                "https://fbschedules.com/college-football-schedule/next-week/"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            for base_url in base_urls:
                try:
                    logger.info(f"Scraping FBSchedules from: {base_url}")
                    time.sleep(2)  # Be respectful
                    
                    response = requests.get(base_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Method 1: Look for schedule tables
                    games.extend(self._parse_fbschedules_tables(soup, days))
                    
                    # Method 2: Look for game cards/containers
                    games.extend(self._parse_fbschedules_game_containers(soup, days))
                    
                    # Method 3: Look for schedule lists
                    games.extend(self._parse_fbschedules_lists(soup, days))
                    
                except Exception as e:
                    logger.debug(f"Error scraping {base_url}: {e}")
                    continue
            
            # Remove duplicates
            unique_games = []
            seen_games = set()
            for game in games:
                game_key = (game['game_day'], game['home_team'], game['away_team'])
                if game_key not in seen_games:
                    seen_games.add(game_key)
                    unique_games.append(game)
            
            logger.info(f"Found {len(unique_games)} unique games from FBSchedules.com")
            return unique_games
            
        except Exception as e:
            logger.error(f"Error scraping FBSchedules.com: {e}")
            return []
    
    def _parse_fbschedules_tables(self, soup: BeautifulSoup, days: int) -> List[Dict]:
        """Parse schedule tables from FBSchedules"""
        games = []
        
        # Look for various table structures
        table_selectors = [
            'table.schedule-table',
            'table.football-schedule',
            'table.wp-block-table',
            'table'
        ]
        
        for selector in table_selectors:
            tables = soup.select(selector)
            for table in tables:
                try:
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        try:
                            # Skip header rows
                            if not row.find('td'):
                                continue
                                
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 3:
                                # Try to extract date and teams
                                date_text = self._extract_date_from_cell(cells[0])
                                teams_text = self._extract_teams_from_cell(cells[1])
                                
                                if teams_text and '@' in teams_text:
                                    teams = teams_text.split('@')
                                    away_team = self._clean_fbschedules_team(teams[0].strip())
                                    home_team = self._clean_fbschedules_team(teams[1].strip())
                                    
                                    if date_text:
                                        game_date = self._parse_fbschedules_date(date_text)
                                    else:
                                        # If no date in row, try to get from table context
                                        game_date = self._extract_date_from_table_context(table)
                                    
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
                                            logger.debug(f"Found game: {away_team} @ {home_team} on {game_date}")
                        except Exception as e:
                            logger.debug(f"Error parsing table row: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error parsing table: {e}")
                    continue
        
        return games
    
    def _parse_fbschedules_game_containers(self, soup: BeautifulSoup, days: int) -> List[Dict]:
        """Parse game containers from FBSchedules"""
        games = []
        
        # Look for game containers, cards, or list items
        container_selectors = [
            '.game-card',
            '.schedule-item',
            '.football-game',
            '.event-list',
            '.schedule-list li'
        ]
        
        for selector in container_selectors:
            containers = soup.select(selector)
            for container in containers:
                try:
                    # Extract text and look for team patterns
                    container_text = container.get_text().strip()
                    
                    # Look for "Away Team @ Home Team" pattern
                    if '@' in container_text:
                        # Extract date if available
                        date_match = re.search(r'(\w+ \d+,? \d{4}|\w+ \d+)', container_text)
                        game_date = None
                        if date_match:
                            game_date = self._parse_fbschedules_date(date_match.group(1))
                        else:
                            game_date = self._extract_date_from_context(container)
                        
                        # Extract teams
                        teams_match = re.search(r'([^@]+)@([^@]+)', container_text)
                        if teams_match:
                            away_team = self._clean_fbschedules_team(teams_match.group(1).strip())
                            home_team = self._clean_fbschedules_team(teams_match.group(2).strip())
                            
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
                    logger.debug(f"Error parsing game container: {e}")
                    continue
        
        return games
    
    def _parse_fbschedules_lists(self, soup: BeautifulSoup, days: int) -> List[Dict]:
        """Parse schedule lists from FBSchedules"""
        games = []
        
        # Look for list-based schedules
        list_items = soup.find_all('li')
        current_date = None
        
        for item in list_items:
            try:
                item_text = item.get_text().strip()
                
                # Check if this is a date header
                date_match = re.search(r'(\w+ \d+,? \d{4}|\w+ \d+)', item_text)
                if date_match and len(item_text) < 50:  # Likely a date header if short
                    current_date = self._parse_fbschedules_date(date_match.group(1))
                    continue
                
                # Check if this is a game item with @ symbol
                if current_date and '@' in item_text:
                    teams_match = re.search(r'([^@]+)@([^@]+)', item_text)
                    if teams_match:
                        away_team = self._clean_fbschedules_team(teams_match.group(1).strip())
                        home_team = self._clean_fbschedules_team(teams_match.group(2).strip())
                        
                        if self._is_within_days(current_date, days):
                            game_data = {
                                'game_day': current_date.strftime('%Y-%m-%d'),
                                'start_time': 'TBD',
                                'home_team': home_team,
                                'away_team': away_team,
                                'source': 'fbschedules'
                            }
                            games.append(game_data)
                            
            except Exception as e:
                logger.debug(f"Error parsing list item: {e}")
                continue
        
        return games
    
    def _extract_date_from_cell(self, cell) -> str:
        """Extract date text from table cell"""
        return cell.get_text().strip()
    
    def _extract_teams_from_cell(self, cell) -> str:
        """Extract teams text from table cell"""
        return cell.get_text().strip()
    
    def _extract_date_from_table_context(self, table) -> dt.date:
        """Extract date from table context (headers, captions, etc.)"""
        try:
            # Look for date in table headers or previous elements
            prev_elem = table.find_previous(['h2', 'h3', 'h4', 'strong', 'b'])
            if prev_elem:
                text = prev_elem.get_text().strip()
                date_match = re.search(r'(\w+ \d+,? \d{4}|\w+ \d+)', text)
                if date_match:
                    return self._parse_fbschedules_date(date_match.group(1))
        except:
            pass
        return dt.date.today()
    
    def _extract_date_from_context(self, element) -> dt.date:
        """Extract date from element context"""
        try:
            # Look for date in parent or sibling elements
            parent = element.find_previous(['h2', 'h3', 'h4', 'strong', 'b'])
            if parent:
                text = parent.get_text().strip()
                date_match = re.search(r'(\w+ \d+,? \d{4}|\w+ \d+)', text)
                if date_match:
                    return self._parse_fbschedules_date(date_match.group(1))
        except:
            pass
        return dt.date.today()
    
    def scrape_espn_schedule(self, days: int = 7) -> List[Dict]:
        """Improved ESPN schedule scraping"""
        try:
            games = []
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Try multiple ESPN endpoints
            endpoints = [
                f"https://www.espn.com/college-football/schedule",
                f"https://www.espn.com/college-football/schedule/_/week/1",
                f"https://www.espn.com/college-football/schedule/_/week/2"
            ]
            
            for url in endpoints:
                try:
                    logger.info(f"Scraping ESPN from: {url}")
                    time.sleep(2)
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for schedule tables
                    schedule_tables = soup.find_all('table', class_='schedule')
                    
                    for table in schedule_tables:
                        # Extract date from table header
                        date_header = table.find_previous('h2') or table.find_previous('div', class_='Table__Title')
                        table_date = dt.date.today()
                        if date_header:
                            date_text = date_header.get_text().strip()
                            table_date = self._parse_espn_date(date_text)
                        
                        rows = table.find_all('tr')[1:]  # Skip header
                        
                        for row in rows:
                            try:
                                teams = row.find_all('a', class_=lambda x: x and 'team' in x.lower())
                                if len(teams) >= 2:
                                    away_team = self._clean_team_name(teams[0].text.strip())
                                    home_team = self._clean_team_name(teams[1].text.strip())
                                    
                                    if away_team and home_team and self._is_within_days(table_date, days):
                                        game_data = {
                                            'game_day': table_date.strftime('%Y-%m-%d'),
                                            'start_time': 'TBD',
                                            'home_team': home_team,
                                            'away_team': away_team,
                                            'source': 'espn'
                                        }
                                        games.append(game_data)
                            except Exception as e:
                                logger.debug(f"Error parsing ESPN row: {e}")
                                continue
                                
                except Exception as e:
                    logger.debug(f"Error scraping ESPN endpoint {url}: {e}")
                    continue
            
            logger.info(f"Found {len(games)} games from ESPN")
            return games
            
        except Exception as e:
            logger.error(f"Error scraping ESPN schedule: {e}")
            return []
    
    def _parse_espn_date(self, date_text: str) -> dt.date:
        """Parse date from ESPN format"""
        try:
            # ESPN uses formats like "Saturday, September 2" or "Week 1 - Saturday"
            date_text = re.sub(r'Week \d+\s*-\s*', '', date_text)  # Remove "Week X - "
            
            formats = [
                '%A, %B %d',
                '%B %d'
            ]
            
            for fmt in formats:
                try:
                    parsed_date = dt.datetime.strptime(date_text, fmt).date()
                    return parsed_date.replace(year=dt.date.today().year)
                except ValueError:
                    continue
        except:
            pass
        return dt.date.today()
    
    def get_schedule(self, days: int = 7) -> List[Dict]:
        """Get NCAAF schedule with improved fallback logic"""
        logger.info(f"Getting NCAAF schedule for next {days} days")
        
        # Try FBSchedules.com first
        games = self.scrape_fbschedules(days)
        
        # If no games found, try ESPN
        if not games:
            logger.info("No games from FBSchedules, trying ESPN...")
            games = self.scrape_espn_schedule(days)
        
        # If still no games, create some sample data for testing
        if not games:
            logger.warning("No games found from any source, using sample data")
            games = self._get_sample_games(days)
        
        logger.info(f"Total games found: {len(games)}")
        return games
    
    def _get_sample_games(self, days: int) -> List[Dict]:
        """Provide sample games for testing when scraping fails"""
        sample_games = []
        today = dt.date.today()
        
        sample_matchups = [
            ("Ohio State", "Michigan"),
            ("Alabama", "Auburn"),
            ("Georgia", "Florida"),
            ("USC", "UCLA"),
            ("Texas", "Oklahoma")
        ]
        
        for i, (away, home) in enumerate(sample_matchups):
            if i < days:
                game_date = today + dt.timedelta(days=i)
                sample_games.append({
                    'game_day': game_date.strftime('%Y-%m-%d'),
                    'start_time': 'TBD',
                    'home_team': home,
                    'away_team': away,
                    'source': 'sample'
                })
        
        return sample_games

    def _is_within_days(self, date: dt.date, days: int) -> bool:
        """Check if date is within the next X days"""
        today = dt.date.today()
        end_date = today + dt.timedelta(days=days)
        return today <= date <= end_date

    # KEEP ALL THESE EXISTING FUNCTIONS - THEY SHOULD STAY AS THEY ARE:
    
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

    def get_upcoming_tbd_events(self, days: int = 7) -> List[Dict]:
        try:
            # Get all scheduled games
            scheduled_games = self.get_schedule(days)
            
            # Get existing gamelines to filter out games that already have odds
            existing_gamelines = self.get_existing_gamelines(days)
            
            # Create set of games that already have gamelines
            existing_games_set = set()
            for gameline in existing_gamelines:
                game_key = (gameline['game_day'], gameline['home_team'], gameline['away_team'])
                existing_games_set.add(game_key)
            
            # Filter scheduled games to only include those without gamelines
            tbd_events = []
            for game in scheduled_games:
                game_key = (game['game_day'], game['home_team'], game['away_team'])
                if game_key not in existing_games_set:
                    tbd_event = {
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
                    }
                    tbd_events.append(tbd_event)
            
            logger.info(f"Found {len(tbd_events)} TBD events without gamelines")
            return tbd_events
            
        except Exception as e:
            logger.error(f"Error getting TBD events: {e}")
            return []
    
    def _clean_team_name(self, team_name: str) -> str:
        """Clean team name from ESPN (fallback)"""
        return team_name

ncaaf_events_manager = NCAAFEventsManager()
