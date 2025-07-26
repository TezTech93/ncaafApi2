import re
import json
import requests
from pprint import pprint

def get_draftkings_ncaaf_gamelines():
    """Get NCAAF game lines by directly accessing the stadiumLeagueData structure"""
    url = "https://sportsbook.draftkings.com/leagues/football/ncaaf"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Debug: Save response to file
        with open('ncaaf_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        # Extract JSON data - try multiple patterns
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
            print("Could not find JSON data in page")
            return []
            
        data = json.loads(json_data)
        
        # Debug: Save JSON data to file
        with open('ncaaf_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        # Try different data locations - DraftKings sometimes changes these
        possible_data_locations = [
            data.get('stadiumLeagueData', {}),
            data.get('sportsbook', {}),
            data.get('events', {}),
            data.get('presentation', {}).get('sports', {}),
            data.get('presentation', {}).get('events', {})
        ]
        
        ncaaf_events = []
        possible_league_ids = ['88809', '84606', '87637']  # Common NCAAF league IDs
        
        for data_location in possible_data_locations:
            if not data_location:
                continue
                
            # Try to find events with any of the possible league IDs
            for league_id in possible_league_ids:
                ncaaf_events = [
                    e for e in data_location.get('events', []) 
                    if e.get('leagueId') == league_id
                ]
                if ncaaf_events:
                    print(f"Found NCAAF events with league ID: {league_id}")
                    break
            if ncaaf_events:
                break
                
        if not ncaaf_events:
            print("No NCAAF events found in any data location")
            print("Available league IDs found:", 
                  {e.get('leagueId') for loc in possible_data_locations 
                   for e in loc.get('events', [])})
            return []
            
        # Get all markets and selections from the data location that worked
        markets = []
        selections = []
        for loc in possible_data_locations:
            if 'markets' in loc and 'selections' in loc:
                markets = loc.get('markets', [])
                selections = loc.get('selections', [])
                break
                
        gamelines = []
        
        for event in ncaaf_events:
            try:
                # Get team names
                participants = event.get('participants', [])
                away_team = participants[0]['name'] if len(participants) > 0 else 'Away'
                home_team = participants[1]['name'] if len(participants) > 1 else 'Home'
                
                # Initialize game line
                gameline = {
                    'event_id': event['id'],
                    'home': home_team,
                    'away': away_team,
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
                
                # Find all markets for this event
                event_markets = [
                    m for m in markets 
                    if m.get('eventId') == event['id']
                ]
                
                for market in event_markets:
                    market_id = market['id']
                    market_type = market.get('marketType', {}).get('name', '')
                    
                    # Get all selections for this market
                    market_selections = [
                        s for s in selections 
                        if s.get('marketId') == market_id
                    ]
                    
                    # Moneyline market
                    if market_type == 'Moneyline':
                        for selection in market_selections:
                            if selection.get('outcomeType') == 'Home':
                                gameline['home_ml'] = selection.get('displayOdds', {}).get('american', 'N/A')
                            elif selection.get('outcomeType') == 'Away':
                                gameline['away_ml'] = selection.get('displayOdds', {}).get('american', 'N/A')
                    
                    # Spread market
                    elif market_type == 'Spread':
                        for selection in market_selections:
                            if selection.get('outcomeType') == 'Home':
                                gameline['home_spread'] = selection.get('points', 'N/A')
                                gameline['home_spread_odds'] = selection.get('displayOdds', {}).get('american', 'N/A')
                            elif selection.get('outcomeType') == 'Away':
                                gameline['away_spread'] = selection.get('points', 'N/A')
                                gameline['away_spread_odds'] = selection.get('displayOdds', {}).get('american', 'N/A')
                    
                    # Total market
                    elif market_type == 'Total':
                        for selection in market_selections:
                            if selection.get('label') == 'Over':
                                gameline['total'] = selection.get('points', 'N/A')
                                gameline['over_odds'] = selection.get('displayOdds', {}).get('american', 'N/A')
                            elif selection.get('label') == 'Under':
                                gameline['under_odds'] = selection.get('displayOdds', {}).get('american', 'N/A')
                
                gamelines.append(gameline)
                
            except Exception as e:
                print(f"Error processing event {event.get('id')}: {e}")
                continue
        
        return gamelines
        
    except Exception as e:
        print(f"Error: {e}")
        return []

def print_gamelines(gamelines):
    """Print the game lines in readable format"""
    if not gamelines:
        print("No game lines found")
        return
    
    print(f"\nFound {len(gamelines)} NCAAF games:")
    for i, game in enumerate(gamelines, 1):
        print(f"\nGame {i}: {game['away']} @ {game['home']}")
        print(f"Start: {game.get('start_date', 'N/A')} | Status: {game.get('status', 'N/A')}")
        print(f"Moneyline: {game['away_ml']} / {game['home_ml']}")
        print(f"Spread: {game['away_spread']} ({game['away_spread_odds']}) / {game['home_spread']} ({game['home_spread_odds']})")
        print(f"Total: {game['total']} (O: {game['over_odds']} / U: {game['under_odds']})")

print("Starting DraftKings NCAAF scraper...")
ncaaf_game_lines = get_draftkings_ncaaf_gamelines()
print_gamelines(ncaaf_game_lines)
