from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import HTMLResponse
import sys, os
import json  # Add this import
import logging  # Add this import

# Add logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(__file__) + "/ncaafFiles/")
from ncaafGamelines import *
from ncaafGetData import get_team_stats, get_player_stats
from ncaafTeams import NcaafTeam
from ncaafEvents import ncaaf_events_manager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# COMPREHENSIVE NCAAF TEAMS LIST - UPDATED
NCAAF_TEAMS = [
    "Alabama", "Ohio State", "Georgia", "Michigan", "Clemson", "Texas", "Oklahoma",
    "Notre Dame", "LSU", "USC", "Penn State", "Florida State", "Oregon", "Texas A&M",
    "Tennessee", "Utah", "Washington", "Miami", "Wisconsin", "Auburn", "Florida",
    "Michigan State", "Iowa", "Oklahoma State", "Arkansas", "Kentucky", "UCLA",
    "North Carolina", "Baylor", "Mississippi", "Kansas State", "TCU", "Pittsburgh",
    "Louisville", "NC State", "Texas Tech", "South Carolina", "West Virginia",
    "Stanford", "Boise State", "Cincinnati", "Houston", "UCF", "BYU", "San Diego State",
    "Fresno State", "Appalachian State", "Coastal Carolina", "Liberty", "Army", "Navy",
    "Air Force", "Tulane", "Memphis", "SMU", "East Carolina", "Tulsa", "Temple",
    "South Florida", "Connecticut", "Massachusetts", "Old Dominion", "Charlotte",
    "Florida Atlantic", "Florida International", "Marshall", "Western Kentucky",
    "Middle Tennessee", "Louisiana Tech", "Rice", "UTSA", "North Texas", "UTEP",
    "Southern Miss", "Arkansas State", "Louisiana", "Louisiana-Monroe", "Troy",
    "South Alabama", "Georgia State", "Georgia Southern", "James Madison",
    "Jacksonville State", "Sam Houston", "Kennesaw State", "Delaware", "Missouri",
    "Vanderbilt", "Mississippi State", "South Carolina", "Kentucky", "Arkansas",
    "Arizona", "Arizona State", "Colorado", "Utah", "UCLA", "USC", "California",
    "Stanford", "Oregon", "Oregon State", "Washington", "Washington State",
    "Illinois", "Indiana", "Iowa", "Maryland", "Michigan", "Michigan State",
    "Minnesota", "Nebraska", "Northwestern", "Ohio State", "Penn State",
    "Purdue", "Rutgers", "Wisconsin", "Boston College", "Clemson", "Duke",
    "Florida State", "Georgia Tech", "Louisville", "Miami", "NC State",
    "North Carolina", "Pittsburgh", "Syracuse", "Virginia", "Virginia Tech",
    "Wake Forest", "Baylor", "Iowa State", "Kansas", "Kansas State",
    "Oklahoma", "Oklahoma State", "TCU", "Texas", "Texas Tech", "West Virginia",
    "UAB", "UTEP", "New Mexico State", "Samford", "Eastern Illinois", "Charlotte"
]

# Remove duplicates and sort
NCAAF_TEAMS = sorted(list(set(NCAAF_TEAMS)))

# Years for dropdown
YEARS = [str(year) for year in range(2020, 2026)]  # Extended to 2025

@app.get("/ncaaf/gamelines")
def get_lines():
    """Main gamelines endpoint"""
    try:
        manager = GamelineManager()
        db_gamelines = manager.read_gamelines()
        
        if db_gamelines:
            return {"Gamelines": {"manual": db_gamelines}}
        else:
            return {"Gamelines": {"manual": []}}
        
    except Exception as e:
        print(f"Error in /ncaaf/gamelines: {e}")
        return {"Gamelines": {"manual": []}}

@app.get("/ncaaf/gamelines/manual", response_class=HTMLResponse)
def manual_input_form():
    """Serve HTML form for manual NCAAF gameline input with upcoming events"""
    try:
        # Get upcoming TBD events - THIS WILL NOW SHOW REAL GAMES
        upcoming_events = ncaaf_events_manager.get_upcoming_tbd_events(days=7)
        
        # Generate HTML for upcoming events
        upcoming_events_html = ""
        if upcoming_events:
            for event in upcoming_events:
                upcoming_events_html += f"""
                <div class="upcoming-event-card">
                    <div class="event-header">
                        <h4>{event['away_team']} @ {event['home_team']}</h4>
                        <span class="event-date">{event['game_day']} {event.get('start_time', '')}</span>
                    </div>
                    <form action="/ncaaf/gamelines/manual/quick" method="post" class="quick-gameline-form">
                        <input type="hidden" name="source" value="manual">
                        <input type="hidden" name="game_day" value="{event['game_day']}">
                        <input type="hidden" name="start_time" value="{event.get('start_time', '')}">
                        <input type="hidden" name="home_team" value="{event['home_team']}">
                        <input type="hidden" name="away_team" value="{event['away_team']}">
                        
                        <div class="quick-odds-row">
                            <div class="odds-group">
                                <label>Home ML:</label>
                                <input type="number" name="home_ml" placeholder="e.g., -150" value="">
                            </div>
                            <div class="odds-group">
                                <label>Away ML:</label>
                                <input type="number" name="away_ml" placeholder="e.g., +130" value="">
                            </div>
                        </div>
                        
                        <div class="quick-odds-row">
                            <div class="odds-group">
                                <label>Home Spread:</label>
                                <input type="number" step="0.5" name="home_spread" placeholder="e.g., -3.5" value="">
                            </div>
                            <div class="odds-group">
                                <label>Home Spread Odds:</label>
                                <input type="number" name="home_spread_odds" placeholder="e.g., -110" value="">
                            </div>
                        </div>
                        
                        <div class="quick-odds-row">
                            <div class="odds-group">
                                <label>Away Spread:</label>
                                <input type="number" step="0.5" name="away_spread" placeholder="e.g., +3.5" value="">
                            </div>
                            <div class="odds-group">
                                <label>Away Spread Odds:</label>
                                <input type="number" name="away_spread_odds" placeholder="e.g., -110" value="">
                            </div>
                        </div>
                        
                        <div class="quick-odds-row">
                            <div class="odds-group">
                                <label>Over/Under:</label>
                                <input type="number" step="0.5" name="over_under" placeholder="e.g., 55.5" value="">
                            </div>
                            <div class="odds-group">
                                <label>Over Odds:</label>
                                <input type="number" name="over_odds" placeholder="e.g., -110" value="">
                            </div>
                            <div class="odds-group">
                                <label>Under Odds:</label>
                                <input type="number" name="under_odds" placeholder="e.g., -110" value="">
                            </div>
                        </div>
                        
                        <button type="submit" class="quick-submit-btn">Add Gameline</button>
                    </form>
                </div>
                """
        else:
            upcoming_events_html = "<p>No upcoming games found. All scheduled games may already have gamelines.</p>"
        
        html_content = f"""
        <html>
        <head>
            <title>NCAAF Manual Gameline Input</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .formGrid {{ display: flex; flex-direction: column; gap: 20px; max-width: 1000px; }}
                .dateTimeRow {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
                .teamRow {{ display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 20px; }}
                .form-group {{ margin-bottom: 15px; }}
                label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
                input, select {{ padding: 8px; width: 100%; box-sizing: border-box; }}
                button {{ padding: 12px 24px; background: #007bff; color: white; border: none; cursor: pointer; font-size: 16px; }}
                button:hover {{ background: #0056b3; }}
                .card {{ border: 1px solid #ddd; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                
                /* Upcoming Events Styles */
                .upcoming-events-section {{ margin-top: 40px; }}
                .upcoming-event-card {{
                    border: 2px solid #e0e0e0;
                    padding: 15px;
                    margin-bottom: 15px;
                    border-radius: 8px;
                    background: #f9f9f9;
                }}
                .event-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 10px;
                }}
                .event-header h4 {{
                    margin: 0;
                    color: #333;
                }}
                .event-date {{
                    color: #666;
                    font-size: 0.9em;
                }}
                .quick-gameline-form {{
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }}
                .quick-odds-row {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 10px;
                }}
                .odds-group {{
                    display: flex;
                    flex-direction: column;
                }}
                .odds-group label {{
                    font-size: 0.8em;
                    color: #666;
                    margin-bottom: 2px;
                }}
                .quick-submit-btn {{
                    padding: 8px 16px;
                    background: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    margin-top: 10px;
                }}
                .quick-submit-btn:hover {{
                    background: #218838;
                }}
                .section-title {{
                    color: #333;
                    border-bottom: 2px solid #007bff;
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <h2>NCAAF Manual Gameline Input</h2>
            
            <!-- Update Events Button -->
            <div style="margin-bottom: 20px;">
                <button onclick="updateEvents()" style="background: #6c757d;">Update Events from Schedule</button>
                <span id="update-status" style="margin-left: 10px;"></span>
            </div>
            
            <!-- Standard Manual Input Form -->
            <div class="card">
                <h3>Custom Gameline Input</h3>
                <form action="/ncaaf/gamelines/manual" method="post">
                    <div class="form-group">
                        <label for="source">Source:</label>
                        <select id="source" name="source" required>
                            <option value="manual">Manual</option>
                            <option value="draftkings">DraftKings</option>
                            <option value="fanduel">FanDuel</option>
                            <option value="espn_bets">ESPN Bets</option>
                        </select>
                    </div>

                    <div class="dateTimeRow">
                        <div class="form-group">
                            <label for="game_day">Game Date:</label>
                            <input type="date" id="game_day" name="game_day" required>
                        </div>
                        <div class="form-group">
                            <label for="start_time">Start Time:</label>
                            <input type="time" id="start_time" name="start_time">
                        </div>
                    </div>

                    <div class="card">
                        <h4>Away Team</h4>
                        <div class="teamRow">
                            <div class="form-group">
                                <label for="away_team">Away Team:</label>
                                <select id="away_team" name="away_team" required>
                                    <option value="">Select Away Team</option>
                                    {"".join([f'<option value="{team}">{team}</option>' for team in NCAAF_TEAMS])}
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="away_ml">Away ML:</label>
                                <input type="number" id="away_ml" name="away_ml" placeholder="e.g., +150">
                            </div>
                            <div class="form-group">
                                <label for="away_spread">Away Spread:</label>
                                <input type="number" step="0.5" id="away_spread" name="away_spread" placeholder="e.g., +7.5">
                            </div>
                            <div class="form-group">
                                <label for="away_spread_odds">Spread Odds:</label>
                                <input type="number" id="away_spread_odds" name="away_spread_odds" placeholder="e.g., -110">
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <h4>Home Team</h4>
                        <div class="teamRow">
                            <div class="form-group">
                                <label for="home_team">Home Team:</label>
                                <select id="home_team" name="home_team" required>
                                    <option value="">Select Home Team</option>
                                    {"".join([f'<option value="{team}">{team}</option>' for team in NCAAF_TEAMS])}
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="home_ml">Home ML:</label>
                                <input type="number" id="home_ml" name="home_ml" placeholder="e.g., -170">
                            </div>
                            <div class="form-group">
                                <label for="home_spread">Home Spread:</label>
                                <input type="number" step="0.5" id="home_spread" name="home_spread" placeholder="e.g., -7.5">
                            </div>
                            <div class="form-group">
                                <label for="home_spread_odds">Spread Odds:</label>
                                <input type="number" id="home_spread_odds" name="home_spread_odds" placeholder="e.g., -110">
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="form-group">
                            <label for="over_under">Over/Under:</label>
                            <input type="number" step="0.5" id="over_under" name="over_under" placeholder="e.g., 55.5">
                        </div>
                        <div class="form-group">
                            <label for="over_odds">Over Odds:</label>
                            <input type="number" id="over_odds" name="over_odds" placeholder="e.g., -110">
                        </div>
                        <div class="form-group">
                            <label for="under_odds">Under Odds:</label>
                            <input type="number" id="under_odds" name="under_odds" placeholder="e.g., -110">
                        </div>
                    </div>

                    <button type="submit">Submit Custom Gameline</button>
                </form>
            </div>

            <!-- Upcoming Events Section -->
            <div class="upcoming-events-section">
                <h3 class="section-title">Upcoming Games (No Gamelines Yet)</h3>
                <p>Quickly add gamelines to scheduled games:</p>
                {upcoming_events_html}
            </div>

            <script>
                function updateEvents() {{
                    const statusElement = document.getElementById('update-status');
                    statusElement.innerHTML = 'Updating events...';
                    
                    fetch('/ncaaf/events/update?days=7&use_gamelines=false')
                        .then(response => response.json())
                        .then(data => {{
                            if (data.status === 'success') {{
                                statusElement.innerHTML = `✅ Updated ${{data.events_updated}} events`;
                                // Reload the page to show new events
                                setTimeout(() => location.reload(), 1000);
                            }} else {{
                                statusElement.innerHTML = '❌ Failed to update events';
                            }}
                        }})
                        .catch(error => {{
                            statusElement.innerHTML = '❌ Error updating events';
                            console.error('Error:', error);
                        }});
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error generating manual form: {e}")
        return HTMLResponse(content=generate_basic_form())

def generate_basic_form():
    """Generate basic form without events if manager fails"""
    return f"""
    <html>
    <head>
        <title>NCAAF Manual Gameline Input</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .formGrid {{ display: flex; flex-direction: column; gap: 20px; max-width: 800px; }}
            .dateTimeRow {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
            .teamRow {{ display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 20px; }}
            .form-group {{ margin-bottom: 15px; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            input, select {{ padding: 8px; width: 100%; box-sizing: border-box; }}
            button {{ padding: 12px 24px; background: #007bff; color: white; border: none; cursor: pointer; font-size: 16px; }}
            button:hover {{ background: #0056b3; }}
            .card {{ border: 1px solid #ddd; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <h2>NCAAF Manual Gameline Input</h2>
        <form action="/ncaaf/gamelines/manual" method="post">
            <div class="form-group">
                <label for="source">Source:</label>
                <select id="source" name="source" required>
                    <option value="manual">Manual</option>
                    <option value="draftkings">DraftKings</option>
                    <option value="fanduel">FanDuel</option>
                    <option value="espn_bets">ESPN Bets</option>
                </select>
            </div>

            <div class="dateTimeRow">
                <div class="form-group">
                    <label for="game_day">Game Date:</label>
                    <input type="date" id="game_day" name="game_day" required>
                </div>
                <div class="form-group">
                    <label for="start_time">Start Time:</label>
                    <input type="time" id="start_time" name="start_time">
                </div>
            </div>

            <div class="card">
                <h4>Away Team</h4>
                <div class="teamRow">
                    <div class="form-group">
                        <label for="away_team">Away Team:</label>
                        <select id="away_team" name="away_team" required>
                            <option value="">Select Away Team</option>
                            {"".join([f'<option value="{team}">{team}</option>' for team in NCAAF_TEAMS])}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="away_ml">Away ML:</label>
                        <input type="number" id="away_ml" name="away_ml" placeholder="e.g., +150">
                    </div>
                    <div class="form-group">
                        <label for="away_spread">Away Spread:</label>
                        <input type="number" step="0.5" id="away_spread" name="away_spread" placeholder="e.g., +7.5">
                    </div>
                    <div class="form-group">
                        <label for="away_spread_odds">Spread Odds:</label>
                        <input type="number" id="away_spread_odds" name="away_spread_odds" placeholder="e.g., -110">
                    </div>
                </div>
            </div>

            <div class="card">
                <h4>Home Team</h4>
                <div class="teamRow">
                    <div class="form-group">
                        <label for="home_team">Home Team:</label>
                        <select id="home_team" name="home_team" required>
                            <option value="">Select Home Team</option>
                            {"".join([f'<option value="{team}">{team}</option>' for team in NCAAF_TEAMS])}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="home_ml">Home ML:</label>
                        <input type="number" id="home_ml" name="home_ml" placeholder="e.g., -170">
                    </div>
                    <div class="form-group">
                        <label for="home_spread">Home Spread:</label>
                        <input type="number" step="0.5" id="home_spread" name="home_spread" placeholder="e.g., -7.5">
                    </div>
                    <div class="form-group">
                        <label for="home_spread_odds">Spread Odds:</label>
                        <input type="number" id="home_spread_odds" name="home_spread_odds" placeholder="e.g., -110">
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="form-group">
                    <label for="over_under">Over/Under:</label>
                    <input type="number" step="0.5" id="over_under" name="over_under" placeholder="e.g., 55.5">
                </div>
                <div class="form-group">
                    <label for="over_odds">Over Odds:</label>
                    <input type="number" id="over_odds" name="over_odds" placeholder="e.g., -110">
                </div>
                <div class="form-group">
                    <label for="under_odds">Under Odds:</label>
                    <input type="number" id="under_odds" name="under_odds" placeholder="e.g., -110">
                </div>
            </div>

            <button type="submit">Submit Custom Gameline</button>
        </form>
    </body>
    </html>
    """

@app.post("/ncaaf/gamelines/manual/dumps")
async def bulk_gamelines_dump(request: Request):
    """Bulk dump gamelines from Python list - handles both JSON and Python literal syntax"""
    try:
        # Get the raw request body
        body = await request.body()
        body_text = body.decode('utf-8')
        
        # Try to parse as JSON first
        try:
            data = json.loads(body_text)
            gamelines = data.get('gamelines', [])
        except json.JSONDecodeError:
            # If JSON fails, try to parse as Python literal
            # Remove variable assignment and clean up Python syntax
            cleaned_text = body_text.strip()
            
            # Remove 'gamelines = ' prefix if present
            if cleaned_text.startswith('gamelines'):
                cleaned_text = cleaned_text.split('=', 1)[1].strip()
            
            # Convert Python literal to JSON
            cleaned_text = cleaned_text.replace("'", '"')  # Single to double quotes
            cleaned_text = cleaned_text.replace('None', 'null')  # None to null
            cleaned_text = cleaned_text.replace('True', 'true')  # True to true
            cleaned_text = cleaned_text.replace('False', 'false')  # False to false
            
            # Parse the cleaned JSON
            gamelines = json.loads(cleaned_text)
            
            # If it's not a list yet, try to get the gamelines key
            if isinstance(gamelines, dict) and 'gamelines' in gamelines:
                gamelines = gamelines['gamelines']
        
        if not gamelines or not isinstance(gamelines, list):
            raise HTTPException(status_code=400, detail="No valid gamelines list provided")
        
        manager = GamelineManager()
        success_count = 0
        
        for gameline in gamelines:
            try:
                game_data = {
                    'home': gameline.get('home_team'),
                    'away': gameline.get('away_team'),
                    'game_day': gameline.get('game_day'),
                    'start_time': gameline.get('start_time'),
                    'home_ml': gameline.get('home_ml'),
                    'away_ml': gameline.get('away_ml'),
                    'home_spread': gameline.get('home_spread'),
                    'away_spread': gameline.get('away_spread'),
                    'home_spread_odds': gameline.get('home_spread_odds'),
                    'away_spread_odds': gameline.get('away_spread_odds'),
                    'over_under': gameline.get('over_under'),
                    'over_odds': gameline.get('over_odds'),
                    'under_odds': gameline.get('under_odds')
                }
                
                source = gameline.get('source', 'manual_dump')
                manager.update_gameline(source, game_data)
                success_count += 1
                
            except Exception as e:
                logger.error(f"Error processing gameline {gameline}: {e}")
                continue
        
        return {
            "status": "success",
            "message": f"Successfully added {success_count} gamelines to database",
            "gamelines_added": success_count,
            "total_processed": len(gamelines)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing bulk gamelines dump: {str(e)}")

@app.post("/ncaaf/gamelines/manual/quick")
async def submit_quick_gameline(
    source: str = Form(...),
    home_team: str = Form(...),
    away_team: str = Form(...),
    game_day: str = Form(...),
    start_time: str = Form(None),
    home_ml: int = Form(None),
    away_ml: int = Form(None),
    home_spread: float = Form(None),
    away_spread: float = Form(None),
    home_spread_odds: int = Form(None),
    away_spread_odds: int = Form(None),
    over_under: float = Form(None),
    over_odds: int = Form(None),
    under_odds: int = Form(None)
):
    """Handle quick gameline submission from upcoming events"""
    try:
        game_data = {
            'home': home_team,
            'away': away_team,
            'game_day': game_day,
            'start_time': start_time,
            'home_ml': home_ml,
            'away_ml': away_ml,
            'home_spread': home_spread,
            'away_spread': away_spread,
            'home_spread_odds': home_spread_odds,
            'away_spread_odds': away_spread_odds,
            'over_under': over_under,
            'over_odds': over_odds,
            'under_odds': under_odds
        }

        manager = GamelineManager()
        manager.update_gameline(source, game_data)
        
        return {
            "status": "success",
            "message": f"Quick gameline added for {away_team} @ {home_team}",
            "redirect": "/ncaaf/gamelines/manual"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting quick gameline: {str(e)}")

# Add events management endpoints
@app.get("/ncaaf/events/update")
def update_ncaaf_events(days: int = 7, use_gamelines: bool = False):
    """Update NCAAF events with schedule data"""
    try:
        updated_count = ncaaf_events_manager.update_events(days, use_gamelines)
        return {
            "status": "success", 
            "sport": "ncaaf",
            "events_updated": updated_count,
            "use_gamelines": use_gamelines
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ncaaf/events/upcoming")
def get_upcoming_events(days: int = 7):
    """Get upcoming TBD events"""
    try:
        events = ncaaf_events_manager.get_upcoming_tbd_events(days)
        return {"sport": "ncaaf", "upcoming_events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ncaaf/gamelines/manual")
async def submit_manual_gameline(
    source: str = Form(...),
    home_team: str = Form(...),
    away_team: str = Form(...),
    game_day: str = Form(...),
    start_time: str = Form(None),
    home_ml: int = Form(None),
    away_ml: int = Form(None),
    home_spread: float = Form(None),
    away_spread: float = Form(None),
    home_spread_odds: int = Form(None),
    away_spread_odds: int = Form(None),
    over_under: float = Form(None),
    over_odds: int = Form(None),
    under_odds: int = Form(None)
):
    """Handle manual NCAAF gameline submission"""
    try:
        game_data = {
            'home': home_team,
            'away': away_team,
            'game_day': game_day,
            'start_time': start_time,
            'home_ml': home_ml,
            'away_ml': away_ml,
            'home_spread': home_spread,
            'away_spread': away_spread,
            'home_spread_odds': home_spread_odds,
            'away_spread_odds': away_spread_odds,
            'over_under': over_under,
            'over_odds': over_odds,
            'under_odds': under_odds
        }

        manager = GamelineManager()
        manager.update_gameline(source, game_data)
        
        return {
            "status": "success",
            "message": f"NCAAF Gameline for {away_team} @ {home_team} submitted successfully",
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting NCAAF gameline: {str(e)}")

# ... (keep all your other existing endpoints)

@app.get("/ncaaf/team-select", response_class=HTMLResponse)
def team_select_form():
    """Serve HTML form for team stats with dropdowns"""
    html_content = f"""
    <html>
    <head>
        <title>NCAAF Team Stats</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .form-group {{ margin-bottom: 15px; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            select, button {{ padding: 10px; font-size: 16px; }}
            button {{ background: #007bff; color: white; border: none; cursor: pointer; }}
            button:hover {{ background: #0056b3; }}
            .stats-card {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .game-row {{ border-bottom: 1px solid #eee; padding: 8px 0; }}
        </style>
    </head>
    <body>
        <h2>NCAAF Team Statistics</h2>
        <form action="/ncaaf/team-stats" method="get" id="teamForm">
            <div class="form-group">
                <label for="team">Team:</label>
                <select id="team" name="team" required>
                    <option value="">Select Team</option>
                    {"".join([f'<option value="{team}">{team}</option>' for team in NCAAF_TEAMS])}
                </select>
            </div>
            <div class="form-group">
                <label for="year">Year:</label>
                <select id="year" name="year" required>
                    <option value="">Select Year</option>
                    {"".join([f'<option value="{year}">{year}</option>' for year in YEARS])}
                </select>
            </div>
            <button type="submit">Get Team Stats</button>
        </form>
        <div id="results"></div>
        
        <script>
            document.getElementById('teamForm').onsubmit = async function(e) {{
                e.preventDefault();
                const team = document.getElementById('team').value;
                const year = document.getElementById('year').value;
                
                if (team && year) {{
                    try {{
                        const response = await fetch(`/ncaaf/team-stats?team=${{encodeURIComponent(team)}}&year=${{year}}`);
                        const data = await response.json();
                        
                        let html = '<h3>Team Statistics:</h3>';
                        
                        if (data.summary) {{
                            html += `<div class="stats-card">
                                <h4>Season Summary</h4>
                                <p><strong>Record:</strong> ${{data.summary.record || 'N/A'}}</p>
                                <p><strong>Points Per Game:</strong> ${{data.summary.points_per_game || 'N/A'}}</p>
                                <p><strong>Points Against Per Game:</strong> ${{data.summary.points_against_per_game || 'N/A'}}</p>
                                <p><strong>Pass Yards Per Game:</strong> ${{data.summary.pass_yards_per_game || 'N/A'}}</p>
                                <p><strong>Rush Yards Per Game:</strong> ${{data.summary.rush_yards_per_game || 'N/A'}}</p>
                            </div>`;
                        }}
                        
                        if (data.games && data.games.length > 0) {{
                            html += '<h4>Game Log</h4>';
                            data.games.forEach(game => {{
                                html += `<div class="game-row">
                                    <strong>${{game.Date || 'N/A'}}</strong> vs ${{game.Opp || 'N/A'}}: 
                                    ${{game.Tm || '0'}} - ${{game.Opp2 || '0'}}
                                    ${{game.OT ? '(OT)' : ''}}
                                </div>`;
                            }});
                        }}
                        
                        document.getElementById('results').innerHTML = html;
                    }} catch (error) {{
                        document.getElementById('results').innerHTML = 
                            '<p style="color: red;">Error fetching data: ' + error + '</p>';
                    }}
                }}
            }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/ncaaf/team-stats")
def get_team_stats_via_form(team: str, year: str):
    """Get team stats via form parameters"""
    try:
        print(f"Fetching stats for {team} in {year}")
        results = get_team_stats(team, year)
        
        if not results or "error" in results:
            # Try to scrape data first
            team_url = team.lower().replace(' ', '-').replace('(', '').replace(')', '')
            if ncaafdb(team_url, year):
                results = get_team_stats(team, year)
            else:
                raise HTTPException(status_code=404, detail=f"Could not retrieve stats for {team} {year}")
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ncaaf/{team}/{year}")
def get_team_stats_endpoint(team: str, year: str):
    """Original team stats endpoint - maintained for compatibility"""
    return get_team_stats_via_form(team, year)

@app.get("/ncaaf/player-stats")
def get_player_stats_endpoint(player: str, season: str = None):
    """Get player stats"""
    try:
        results = get_player_stats(player, season)
        if not results:
            raise HTTPException(status_code=404, detail="Player stats not found")
        return {"Player_Stats": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ncaaf/team/recent/{team}/{year}/{games}")
def get_recent_games(team: str, year: str, games: int):
    """Get recent games data using NcaafTeam class"""
    try:
        ncaaf_team = NcaafTeam()
        
        if games == 2:
            success = ncaaf_team.last2(team, year)
        elif games == 4:
            success = ncaaf_team.last4(team, year)
        elif games == 8:
            success = ncaaf_team.last8(team, year)
        else:
            raise HTTPException(status_code=400, detail="Games must be 2, 4, or 8")
        
        if not success:
            raise HTTPException(status_code=404, detail="Could not retrieve recent games")
        
        # Return the recent games data
        recent_data = {
            'scores': ncaaf_team.tm if hasattr(ncaaf_team, 'tm') else [],
            'opponents': ncaaf_team.opp if hasattr(ncaaf_team, 'opp') else [],
            'dates': ncaaf_team.date if hasattr(ncaaf_team, 'date') else []
        }
        
        return recent_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ncaaf/scrape/{team}/{year}")
def scrape_team_data(team: str, year: str):
    """Endpoint to manually trigger data scraping"""
    try:
        team_url = team.lower().replace(' ', '-').replace('(', '').replace(')', '')
        success = ncaafdb(team_url, year)
        
        if success:
            return {"status": "success", "message": f"Data scraped for {team} {year}"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to scrape data for {team} {year}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add the manual events routes
@app.get("/ncaaf/events/manual", response_class=HTMLResponse)
def manual_events_form():
    """Serve HTML form for manual NCAAF events input"""
    html_content = f"""
    <html>
    <head>
        <title>Manual NCAAF Events Input</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .form-container {{ max-width: 800px; }}
            .form-group {{ margin-bottom: 15px; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            input, select {{ padding: 8px; width: 100%; box-sizing: border-box; }}
            button {{ padding: 12px 24px; background: #007bff; color: white; border: none; cursor: pointer; font-size: 16px; margin-right: 10px; }}
            button:hover {{ background: #0056b3; }}
            .game-row {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }}
            .add-game-btn {{ background: #28a745; }}
            .add-game-btn:hover {{ background: #218838; }}
            .remove-game-btn {{ background: #dc3545; }}
            .remove-game-btn:hover {{ background: #c82333; }}
        </style>
    </head>
    <body>
        <h2>Manual NCAAF Events Input</h2>
        
        <div class="form-container">
            <form id="eventsForm">
                <div id="gamesContainer">
                    <div class="game-row">
                        <div class="form-group">
                            <label>Game Date:</label>
                            <input type="date" name="game_day" required>
                        </div>
                        <div class="form-group">
                            <label>Start Time:</label>
                            <input type="time" name="start_time">
                        </div>
                        <div class="form-group">
                            <label>Away Team:</label>
                            <select name="away_team" required>
                                <option value="">Select Away Team</option>
                                {"".join([f'<option value="{team}">{team}</option>' for team in NCAAF_TEAMS])}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Home Team:</label>
                            <select name="home_team" required>
                                <option value="">Select Home Team</option>
                                {"".join([f'<option value="{team}">{team}</option>' for team in NCAAF_TEAMS])}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Source:</label>
                            <select name="source">
                                <option value="manual">Manual</option>
                                <option value="schedule">Schedule</option>
                                <option value="espn">ESPN</option>
                            </select>
                        </div>
                    </div>
                </div>
                
                <button type="button" class="add-game-btn" onclick="addGameRow()">Add Another Game</button>
                <button type="submit">Submit Events</button>
            </form>
            
            <div id="result" style="margin-top: 20px;"></div>
        </div>

        <script>
            let gameCount = 1;
            
            function addGameRow() {{
                gameCount++;
                const gamesContainer = document.getElementById('gamesContainer');
                const newGameRow = document.createElement('div');
                newGameRow.className = 'game-row';
                newGameRow.innerHTML = `
                    <div class="form-group">
                        <label>Game Date:</label>
                        <input type="date" name="game_day" required>
                    </div>
                    <div class="form-group">
                        <label>Start Time:</label>
                        <input type="time" name="start_time">
                    </div>
                    <div class="form-group">
                        <label>Away Team:</label>
                        <select name="away_team" required>
                            <option value="">Select Away Team</option>
                            {"".join([f'<option value="{team}">{team}</option>' for team in NCAAF_TEAMS])}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Home Team:</label>
                        <select name="home_team" required>
                            <option value="">Select Home Team</option>
                            {"".join([f'<option value="{team}">{team}</option>' for team in NCAAF_TEAMS])}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Source:</label>
                        <select name="source">
                            <option value="manual">Manual</option>
                            <option value="schedule">Schedule</option>
                            <option value="espn">ESPN</option>
                        </select>
                    </div>
                    <button type="button" class="remove-game-btn" onclick="this.parentElement.remove()">Remove Game</button>
                `;
                gamesContainer.appendChild(newGameRow);
            }}
            
            document.getElementById('eventsForm').onsubmit = async function(e) {{
                e.preventDefault();
                
                // Collect all games
                const games = [];
                const gameRows = document.querySelectorAll('.game-row');
                
                gameRows.forEach(row => {{
                    const inputs = row.querySelectorAll('input, select');
                    const gameData = {{}};
                    inputs.forEach(input => {{
                        if (input.name) {{
                            gameData[input.name] = input.value;
                        }}
                    }});
                    games.push(gameData);
                }});
                
                try {{
                    const response = await fetch('/ncaaf/events/manual/dumps', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{ games: games }})
                    }});
                    
                    const result = await response.json();
                    document.getElementById('result').innerHTML = 
                        `<p style="color: green;">✅ ${{result.message}}</p>`;
                        
                }} catch (error) {{
                    document.getElementById('result').innerHTML = 
                        `<p style="color: red;">❌ Error: ${{error}}</p>`;
                }}
            }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/ncaaf/events/manual/dumps")
async def bulk_events_dump(data: dict):
    """Bulk dump events from Python list"""
    try:
        games = data.get('games', [])
        if not games:
            raise HTTPException(status_code=400, detail="No games provided")
        
        # Convert to events format and update database
        events = []
        for game in games:
            event = {
                'game_day': game.get('game_day'),
                'start_time': game.get('start_time', 'TBD'),
                'home_team': game.get('home_team'),
                'away_team': game.get('away_team'),
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
                'source': game.get('source', 'manual_dump')
            }
            events.append(event)
        
        # Update database
        updated_count = ncaaf_events_manager._update_database(events)
        
        return {
            "status": "success",
            "message": f"Successfully added {updated_count} events to database",
            "events_added": updated_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing bulk events dump: {str(e)}")

@app.get("/ncaaf/gamelines/manual/dumps", response_class=HTMLResponse)
def gamelines_dump_form():
    """Serve HTML form for bulk gamelines dump"""
    html_content = f"""
    <html>
    <head>
        <title>Bulk NCAAF Gamelines Dump</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .form-container {{ max-width: 1000px; }}
            .form-group {{ margin-bottom: 15px; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            textarea {{ width: 100%; height: 300px; padding: 10px; font-family: monospace; }}
            button {{ padding: 12px 24px; background: #007bff; color: white; border: none; cursor: pointer; font-size: 16px; }}
            button:hover {{ background: #0056b3; }}
            .example {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .code {{ font-family: monospace; background: #e9ecef; padding: 10px; }}
        </style>
    </head>
    <body>
        <h2>Bulk NCAAF Gamelines Dump</h2>
        
        <div class="form-container">
            <div class="example">
                <h3>Example Python List Format:</h3>
                <div class="code">
gamelines = [<br>
&nbsp;&nbsp;{{<br>
&nbsp;&nbsp;&nbsp;&nbsp;"source": "draftkings",<br>
&nbsp;&nbsp;&nbsp;&nbsp;"game_day": "2025-11-22",<br>
&nbsp;&nbsp;&nbsp;&nbsp;"start_time": "14:30",<br>
&nbsp;&nbsp;&nbsp;&nbsp;"home_team": "Ohio State",<br>
&nbsp;&nbsp;&nbsp;&nbsp;"away_team": "Michigan",<br>
&nbsp;&nbsp;&nbsp;&nbsp;"home_ml": -150,<br>
&nbsp;&nbsp;&nbsp;&nbsp;"away_ml": 130,<br>
&nbsp;&nbsp;&nbsp;&nbsp;"home_spread": -3.5,<br>
&nbsp;&nbsp;&nbsp;&nbsp;"away_spread": 3.5,<br>
&nbsp;&nbsp;&nbsp;&nbsp;"home_spread_odds": -110,<br>
&nbsp;&nbsp;&nbsp;&nbsp;"away_spread_odds": -110,<br>
&nbsp;&nbsp;&nbsp;&nbsp;"over_under": 55.5,<br>
&nbsp;&nbsp;&nbsp;&nbsp;"over_odds": -110,<br>
&nbsp;&nbsp;&nbsp;&nbsp;"under_odds": -110<br>
&nbsp;&nbsp;}}<br>
]
                </div>
            </div>
            
            <form id="gamelinesDumpForm">
                <div class="form-group">
                    <label for="gamelinesData">Paste your Python list of gamelines:</label>
                    <textarea id="gamelinesData" name="gamelines_data" placeholder="Paste your Python list here..."></textarea>
                </div>
                
                <button type="submit">Submit Bulk Gamelines</button>
            </form>
            
            <div id="result" style="margin-top: 20px;"></div>
        </div>

        <script>
            document.getElementById('gamelinesDumpForm').onsubmit = async function(e) {{
                e.preventDefault();
                const gamelinesData = document.getElementById('gamelinesData').value;
                
                if (!gamelinesData.trim()) {{
                    document.getElementById('result').innerHTML = 
                        '<p style="color: red;">❌ Please provide gamelines data</p>';
                    return;
                }}
                
                try {{
                    // Send the raw text as-is, let the backend handle the parsing
                    const response = await fetch('/ncaaf/gamelines/manual/dumps', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'text/plain',
                        }},
                        body: gamelinesData
                    }});
                    
                    const result = await response.json();
                    document.getElementById('result').innerHTML = 
                        `<p style="color: green;">✅ ${{result.message}}</p>`;
                        
                }} catch (error) {{
                    document.getElementById('result').innerHTML = 
                        `<p style="color: red;">❌ Error: ${{error}}</p>`;
                }}
            }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Keep your existing player and coach endpoints
@app.get("/ncaaf/player-stats", response_class=HTMLResponse)
def player_select_form():
    """Serve HTML form for player stats"""
    html_content = """
    <html>
    <head>
        <title>NCAAF Player Stats</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
        </style>
    </head>
    <body>
        <h2>NCAAF Player Statistics</h2>
        <p>Player stats functionality is available via API.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/ncaaf/db-check")
def db_check():
    """Check database status"""
    try:
        from ncaafGamelines import GamelineManager
        manager = GamelineManager()
        gamelines = manager.read_gamelines()
        
        # Check if ncaafDb directory exists and has files
        db_files = []
        if os.path.exists('ncaafDb'):
            db_files = os.listdir('ncaafDb')
        
        return {
            "db_gamelines": gamelines, 
            "count": len(gamelines),
            "ncaafDb_files": db_files,
            "ncaafDb_count": len(db_files)
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
