from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import HTMLResponse
import sys, os

sys.path.append(os.path.dirname(__file__) + "/ncaafFiles/")
from ncaafGamelines import *
from ncaafGetData import get_team_stats, get_player_stats, ncaafdb
from ncaafTeam import NcaafTeam  # Import the team class

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NCAAF_TEAMS = [
    # FBS Schools (Bowl Subdivision)
    "Air Force", "Akron", "Alabama", "Appalachian State", "Arizona", 
    "Arizona State", "Arkansas", "Arkansas State", "Army", "Auburn",
    "Ball State", "Baylor", "Boise State", "Boston College", "Bowling Green",
    "Buffalo", "BYU", "California", "Central Michigan", "Charlotte",
    "Cincinnati", "Clemson", "Coastal Carolina", "Colorado", "Colorado State",
    "Connecticut", "Delaware", "Duke", "East Carolina", "Eastern Michigan",
    "Florida", "Florida Atlantic", "Florida International", "Florida State", "Fresno State",
    "Georgia", "Georgia Southern", "Georgia State", "Georgia Tech", "Hawaii",
    "Houston", "Illinois", "Indiana", "Iowa", "Iowa State", "Jacksonville State",
    "James Madison", "Kansas", "Kansas State", "Kennesaw State", "Kent State",
    "Kentucky", "Liberty", "Louisiana", "Louisiana Monroe", "Louisiana Tech", "Louisville",
    "LSU", "Marshall", "Maryland", "Memphis", "Miami (FL)",
    "Miami (OH)", "Michigan", "Michigan State", "Middle Tennessee", "Minnesota",
    "Mississippi State", "Missouri", "Missouri State", "Navy", "NC State",
    "Nebraska", "Nevada", "New Mexico", "New Mexico State", "North Carolina",
    "North Texas", "Northern Illinois", "Northwestern", "Notre Dame", "Ohio",
    "Ohio State", "Oklahoma", "Oklahoma State", "Old Dominion", "Ole Miss",
    "Oregon", "Oregon State", "Penn State", "Pittsburgh", "Purdue", "Rice",
    "Rutgers", "Sam Houston", "San Diego State", "San Jose State", "SMU",
    "South Alabama", "South Carolina", "South Florida", "Southern Miss", "Stanford",
    "Syracuse", "TCU", "Temple", "Tennessee", "Texas",
    "Texas A&M", "Texas State", "Texas Tech", "Toledo", "Troy",
    "Tulane", "Tulsa", "UAB", "UCF", "UCLA",
    "UMass", "UNLV", "USC", "Utah", "Utah State",
    "UTEP", "UTSA", "Vanderbilt", "Virginia", "Virginia Tech",
    "Wake Forest", "Washington", "Washington State", "West Virginia", "Western Kentucky",
    "Western Michigan", "Wisconsin", "Wyoming",
    
    # FCS Schools (Championship Subdivision) playing FBS opponents in 2025[citation:2]
    "Abilene Christian", "Alabama A&M", "Alabama State", "Albany", "Alcorn State",
    "Austin Peay", "Bethune-Cookman", "Bryant", "Bucknell", "Cal Poly",
    "Campbell", "Central Arkansas", "Central Connecticut State", "Charleston Southern", "Chattanooga",
    "Colgate", "Delaware State", "Duquesne", "East Texas A&M", "Eastern Illinois",
    "Eastern Kentucky", "Eastern Washington", "Elon", "ETSU", "Florida A&M",
    "Fordham", "Furman", "Gardner-Webb", "Grambling State", "Holy Cross",
    "Houston Christian", "Howard", "Idaho", "Idaho State", "Illinois State",
    "Incarnate Word", "Indiana State", "Jackson State", "Lafayette", "Lamar",
    "Lehigh", "LIU", "Lindenwood", "Maine", "McNeese",
    "Mercer", "Merrimack", "Monmouth", "Morgan State", "Murray State",
    "New Hampshire", "Nicholls", "Norfolk State", "North Alabama", "North Carolina A&T",
    "North Carolina Central", "North Dakota", "Northern Arizona", "Northern Colorado", "Northern Iowa",
    "Northwestern State", "Portland State", "Prairie View A&M", "Rhode Island", "Richmond",
    "Robert Morris", "Sacramento State", "Saint Francis (PA)", "Samford", "Southeastern Louisiana",
    "Southeast Missouri State", "South Carolina State", "South Dakota", "Southern", "Southern Illinois",
    "Stony Brook", "Tarleton State", "Tennessee State", "Tennessee Tech", "Texas Southern",
    "The Citadel", "Towson", "UC Davis", "UT Martin", "Villanova",
    "VMI", "Wagner", "Weber State", "Western Carolina", "Western Illinois",
    "William & Mary", "Wofford", "Youngstown State"
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
            <!-- ... (keep your existing form HTML) ... -->
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
