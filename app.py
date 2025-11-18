from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import HTMLResponse
import sys, os

sys.path.append(os.path.dirname(__file__) + "/ncaafFiles/")
from ncaafGamelines import *
from ncaafGetData import get_team_stats, get_player_stats, ncaafdb
from ncaafTeams import NcaafTeam
from ncaafEvents import ncaaf_events_manager  # Import the events manager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NCAAF_TEAMS = [
    # ... (keep your existing team list)
]

# Years for dropdown
YEARS = [str(year) for year in range(2020, 2025)]

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
        # Get upcoming TBD events
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
                    justify-content: between;
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
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error generating manual form: {e}")
        # Fallback to basic form if events manager fails
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
            <!-- ... (same as your original form) ... -->
        </form>
    </body>
    </html>
    """

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

# ... (keep all your existing endpoints below)

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
