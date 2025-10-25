from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import HTMLResponse
import sys, os

sys.path.append(os.path.dirname(__file__) + "/ncaafFiles/")
from ncaafGamelines import *
from ncaafGetData import *

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NCAAF team list for dropdowns (FBS teams)
NCAAF_TEAMS = [
    "Alabama", "Auburn", "LSU", "Georgia", "Florida", "Tennessee", "Texas A&M", "Ole Miss", "Arkansas", "Mississippi St",
    "Missouri", "Kentucky", "South Carolina", "Vanderbilt", "Ohio St", "Michigan", "Penn St", "Michigan St", "Wisconsin", "Iowa",
    "Minnesota", "Purdue", "Illinois", "Northwestern", "Nebraska", "Indiana", "Rutgers", "Maryland", "Oklahoma", "Texas",
    "Oklahoma St", "Baylor", "TCU", "Texas Tech", "Kansas", "Kansas St", "Iowa St", "West Virginia", "Clemson", "Florida St",
    "Miami FL", "North Carolina", "NC State", "Virginia Tech", "Pittsburgh", "Wake Forest", "Duke", "Georgia Tech", "Virginia",
    "Boston College", "Syracuse", "Louisville", "Notre Dame", "USC", "UCLA", "Oregon", "Washington", "Utah", "Stanford",
    "California", "Arizona", "Arizona St", "Colorado", "Oregon St", "Washington St", "Boise St", "BYU", "Cincinnati", "Houston",
    "UCF", "Memphis", "SMU", "Tulane", "Navy", "Army", "Air Force", "Coastal Carolina", "Appalachian St", "Liberty"
]

# Years for dropdown
YEARS = [str(year) for year in range(2020, 2025)]

@app.get("/ncaaf/gamelines")
def get_lines():
    return {"Gamelines": ncaaf_game_lines}

@app.get("/ncaaf/gamelines/manual", response_class=HTMLResponse)
def manual_input_form():
    """Serve HTML form for manual NCAAF gameline input"""
    html_content = f"""
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
            <div class="card">
                <div class="form-group">
                    <label for="source">Source:</label>
                    <select id="source" name="source" required>
                        <option value="manual">Manual</option>
                        <option value="draftkings">DraftKings</option>
                        <option value="fanduel">FanDuel</option>
                        <option value="espn_bets">ESPN Bets</option>
                    </select>
                </div>
            </div>

            <div class="card">
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
            </div>

            <div class="card">
                <h3>Away Team</h3>
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
                <h3>Home Team</h3>
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

            <button type="submit">Submit NCAAF Gameline</button>
        </form>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

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
        
        return {
            "status": "success",
            "message": f"NCAAF Gameline for {away_team} @ {home_team} submitted successfully",
            "data": game_data
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
                        const response = await fetch(`/ncaaf/${{team}}/${{year}}`);
                        const data = await response.json();
                        document.getElementById('results').innerHTML = 
                            '<h3>Results:</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    }} catch (error) {{
                        document.getElementById('results').innerHTML = 
                            '<p style="color: red;">Error fetching data</p>';
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
    return get_team_stats(team, year)

@app.get("/ncaaf/{team}/{year}")
def get_team_stats(team: str, year: str):
    """Original team stats endpoint"""
    try:
        results = get_team_stats(team, year)
        if not results:
            raise HTTPException(status_code=404, detail="No stats found for the given team and year")
        return {"Team_Stats": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ncaaf/player-stats", response_class=HTMLResponse)
def player_select_form():
    """Serve HTML form for player stats (placeholder)"""
    html_content = """
    <html>
    <head>
        <title>NCAAF Player Stats</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select, button { padding: 10px; font-size: 16px; }
            button { background: #007bff; color: white; border: none; cursor: pointer; }
            button:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <h2>NCAAF Player Statistics (Coming Soon)</h2>
        <p>Player stats functionality will be implemented here.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/ncaaf/{player}/")
def get_player_stats(player: str):
    """Placeholder for player stats"""
    return {"message": "Player stats endpoint - implementation pending"}

@app.get("/ncaaf/coach-stats", response_class=HTMLResponse)
def coach_select_form():
    """Serve HTML form for coach stats (placeholder)"""
    html_content = """
    <html>
    <head>
        <title>NCAAF Coach Stats</title>
    </head>
    <body>
        <h2>NCAAF Coach Statistics (Coming Soon)</h2>
        <p>Coach stats functionality will be implemented here.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/ncaaf/{coach}/")
def get_coach_stats(coach: str):
    """Placeholder for coach stats"""
    return {"message": "Coach stats endpoint - implementation pending"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
