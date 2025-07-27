import re
import json
import requests
import time
from pprint import pprint
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def get_ncaaf_gamelines_selenium_fallback():
    """Fallback using Selenium when JSON parsing fails"""
    url = "https://sportsbook.draftkings.com/leagues/football/ncaaf"
    
    # Configure Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64 x64) AppleWebKit/537.36")
    
    try:
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
        gamelines = []
        
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.sportsbook-event-accordion"))
        )
        
        # Scroll and wait for dynamic content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        
        # Extract game containers
        games = driver.find_elements(By.CSS_SELECTOR, "div.sportsbook-event-accordion__children-expanded")
        
        for game in games:
            try:
                teams = game.find_elements(By.CLASS_NAME, "event-cell__name-text")
                odds = game.find_elements(By.CSS_SELECTOR, ".sportsbook-outcome-cell__elements")
                
                if len(teams) >= 2 and len(odds) >= 6:
                    gameline = {
                        'event_id': f"selenium_{int(time.time())}",
                        'away': teams[0].text.strip(),
                        'home': teams[1].text.strip(),
                        'away_spread': odds[0].text.split('\n')[0],
                        'away_spread_odds': odds[0].text.split('\n')[-1],
                        'home_spread': odds[1].text.split('\n')[0],
                        'home_spread_odds': odds[1].text.split('\n')[-1],
                        'total': odds[2].text.split('\n')[0].replace('O ', ''),
                        'over_odds': odds[2].text.split('\n')[-1],
                        'under_odds': odds[3].text.split('\n')[-1],
                        'away_ml': odds[4].text.strip(),
                        'home_ml': odds[5].text.strip(),
                        'status': 'NOT_STARTED',
                        'start_date': ''
                    }
                    gamelines.append(gameline)
                    
            except Exception as e:
                print(f"Skipping game due to error: {str(e)}")
                continue
                
        return gamelines
        
    except Exception as e:
        print(f"Selenium fallback failed: {str(e)}")
        return []
    finally:
        if 'driver' in locals():
            driver.quit()

def get_draftkings_ncaaf_gamelines_json():
    """Primary JSON API method"""
    url = "https://sportsbook.draftkings.com/leagues/football/ncaaf"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Debugging saves
        with open('ncaaf_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        # Multiple JSON pattern matching
        json_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
            r'window\.__DK_DATA__\s*=\s*({.*?});'
        ]
        
        json_data = None
        for pattern in json_patterns:
            match = re.search(pattern, response.text, re.DOTALL)
            if match:
                json_data = match.group(1)
                break
                
        if not json_data:
            print("No JSON data found in page")
            return []
            
        data = json.loads(json_data)
        
        with open('ncaaf_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        # Search multiple possible data locations
        possible_data_locations = [
            data.get('stadiumLeagueData', {}),
            data.get('sportsbook', {}),
            data.get('presentation', {}).get('sports', {}),
            data.get('presentation', {}).get('events', {})
        ]
        
        ncaaf_events = []
        possible_league_ids = ['88809', '84606', '87637', '84241']
        
        for loc in possible_data_locations:
            for league_id in possible_league_ids:
                ncaaf_events = [e for e in loc.get('events', []) if str(e.get('leagueId')) == league_id]
                if ncaaf_events:
                    print(f"Found events in league {league_id}")
                    break
            if ncaaf_events:
                break
                
        if not ncaaf_events:
            print("No NCAAF events found in JSON data")
            return []
            
        # Extract markets and selections
        markets = next((loc.get('markets', []) for loc in possible_data_locations if 'markets' in loc)
        selections = next((loc.get('selections', []) for loc in possible_data_locations if 'selections' in loc)
        
        gamelines = []
        for event in ncaaf_events:
            try:
                participants = event.get('participants', [])
                gameline = {
                    'event_id': event.get('id', ''),
                    'home': participants[1]['name'] if len(participants) > 1 else 'Home',
                    'away': participants[0]['name'] if len(participants) > 0 else 'Away',
                    'start_date': event.get('startEventDate', ''),
                    'status': event.get('status', 'NOT_STARTED'),
                    'home_ml': 'N/A',
                    'away_ml': 'N/A',
                    'home_spread': 'N/A',
                    'away_spread': 'N/A',
                    'home_spread_odds': 'N/A',
                    'away_spread_odds': 'N/A',
                    'total': 'N/A',
                    'over_odds': 'N/A',
                    'under_odds': 'N/A'
                }
                
                event_markets = [m for m in markets if m.get('eventId') == event['id']]
                
                for market in event_markets:
                    market_selections = [s for s in selections if s.get('marketId') == market['id']]
                    market_type = market.get('marketType', {}).get('name', '')
                    
                    for selection in market_selections:
                        odds = selection.get('displayOdds', {}).get('american', 'N/A')
                        if market_type == 'Moneyline':
                            if selection.get('outcomeType') == 'Home':
                                gameline['home_ml'] = odds
                            elif selection.get('outcomeType') == 'Away':
                                gameline['away_ml'] = odds
                        elif market_type == 'Spread':
                            if selection.get('outcomeType') == 'Home':
                                gameline['home_spread'] = selection.get('points', 'N/A')
                                gameline['home_spread_odds'] = odds
                            elif selection.get('outcomeType') == 'Away':
                                gameline['away_spread'] = selection.get('points', 'N/A')
                                gameline['away_spread_odds'] = odds
                        elif market_type == 'Total':
                            if selection.get('label') == 'Over':
                                gameline['total'] = selection.get('points', 'N/A')
                                gameline['over_odds'] = odds
                            elif selection.get('label') == 'Under':
                                gameline['under_odds'] = odds
                
                gamelines.append(gameline)
                
            except Exception as e:
                print(f"Error processing event: {e}")
                continue
                
        return gamelines
        
    except Exception as e:
        print(f"JSON API method failed: {e}")
        return []

def get_draftkings_ncaaf_gamelines():
    """Main function with automatic fallback"""
    print("\nAttempting JSON API method...")
    json_data = get_draftkings_ncaaf_gamelines_json()
    
    if json_data:
        return json_data
        
    print("\nJSON method failed, trying Selenium fallback...")
    selenium_data = get_ncaaf_gamelines_selenium_fallback()
    
    if selenium_data:
        print("Selenium fallback succeeded")
        return selenium_data
        
    print("\nAll methods failed")
    return []

def print_gamelines(gamelines):
    """Print results in readable format"""
    if not gamelines:
        print("No game lines available")
        return
    
    print(f"\nFound {len(gamelines)} NCAAF games:")
    for i, game in enumerate(gamelines, 1):
        print(f"\nGame {i}: {game['away']} @ {game['home']}")
        print(f"Start: {game.get('start_date', 'N/A')} | Status: {game.get('status', 'N/A')}")
        print(f"Moneyline: {game['away_ml']} / {game['home_ml']}")
        print(f"Spread: {game['away_spread']} ({game['away_spread_odds']}) / {game['home_spread']} ({game['home_spread_odds']})")
        print(f"Total: {game['total']} (O: {game['over_odds']} / U: {game['under_odds']})")

print("Starting NCAAF Odds Scraper...")
gamelines = get_draftkings_ncaaf_gamelines()
print_gamelines(gamelines)
