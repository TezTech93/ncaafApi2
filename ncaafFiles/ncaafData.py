import sqlite3
import datetime as dt
import requests
from bs4 import BeautifulSoup
import os
import pandas as pd

current_year = dt.datetime.now().year

# Database field lists
Week = []
Day = []
Date = []
OT = []
Opp = []
Tm = []
Opp2 = []
Cmp = []
Att = []
PassYds = []
PassTD = []
Int = []
Sk = []
SkYds = []
PassYA = []
PassNYA = []
CmpPct = []
PasserRate = []
RushAtt = []
RushYds = []
RushYA = []
RushTD = []
FGM = []
FGA = []
XPM = []
XPA = []
Pnt = []
PuntYds = []
ThirdDownConv = []
ThirdDownAtt = []
FourthDownConv = []
FourthDownAtt = []
ToP = []

def ncaafdb(team, year=current_year):
    """
    Scrape NCAAF team stats and store in SQLite database
    """
    team = team.lower()
    year = year
    
    # Create ncaafDb directory if it doesn't exist
    os.makedirs('ncaafDb', exist_ok=True)
    
    sample_list = []
    s = 'stats'
    a = 0
    
    try:
        # NCAAF stats URL (using Sports Reference format)
        url = f'https://www.sports-reference.com/cfb/schools/{team}/{year}/gamelog/'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        content = requests.get(url, headers=headers)
        content.raise_for_status()
        
        soup = BeautifulSoup(content.content, 'html.parser')
        
        # Find the offensive stats table
        table = soup.find('table', {'id': 'offense'})
        if not table:
            print(f"No offensive stats table found for {team} {year}")
            return False
            
        # Extract all table cells
        td = table.find_all('td')
        th = table.find_all('th')
        
        # Combine all cells for processing
        all_cells = th + td
        
        for cell in all_cells:
            sample_list.append(cell.text.strip())
        
        # NCAAF typically has around 30+ stats per game
        # Adjust slice indices based on actual table structure
        stats_per_game = 35  # This may need adjustment
        
        if len(sample_list) < stats_per_game:
            print(f"Not enough data found for {team} {year}")
            return False
        
        # Extract stats by slicing the list (adjust indices based on actual data)
        Week = sample_list[0::stats_per_game]
        Day = sample_list[1::stats_per_game]
        Date = sample_list[2::stats_per_game]
        OT = sample_list[4::stats_per_game] if len(sample_list) > 4 else []
        Opp = sample_list[5::stats_per_game] if len(sample_list) > 5 else []
        Tm = sample_list[6::stats_per_game] if len(sample_list) > 6 else []
        Opp2 = sample_list[7::stats_per_game] if len(sample_list) > 7 else []
        Cmp = sample_list[8::stats_per_game] if len(sample_list) > 8 else []
        Att = sample_list[9::stats_per_game] if len(sample_list) > 9 else []
        PassYds = sample_list[10::stats_per_game] if len(sample_list) > 10 else []
        PassTD = sample_list[11::stats_per_game] if len(sample_list) > 11 else []
        Int = sample_list[12::stats_per_game] if len(sample_list) > 12 else []
        Sk = sample_list[13::stats_per_game] if len(sample_list) > 13 else []
        SkYds = sample_list[14::stats_per_game] if len(sample_list) > 14 else []
        PassYA = sample_list[15::stats_per_game] if len(sample_list) > 15 else []
        PassNYA = sample_list[16::stats_per_game] if len(sample_list) > 16 else []
        CmpPct = sample_list[17::stats_per_game] if len(sample_list) > 17 else []
        PasserRate = sample_list[18::stats_per_game] if len(sample_list) > 18 else []
        RushAtt = sample_list[19::stats_per_game] if len(sample_list) > 19 else []
        RushYds = sample_list[20::stats_per_game] if len(sample_list) > 20 else []
        RushYA = sample_list[21::stats_per_game] if len(sample_list) > 21 else []
        RushTD = sample_list[22::stats_per_game] if len(sample_list) > 22 else []
        FGM = sample_list[23::stats_per_game] if len(sample_list) > 23 else []
        FGA = sample_list[24::stats_per_game] if len(sample_list) > 24 else []
        XPM = sample_list[25::stats_per_game] if len(sample_list) > 25 else []
        XPA = sample_list[26::stats_per_game] if len(sample_list) > 26 else []
        Pnt = sample_list[27::stats_per_game] if len(sample_list) > 27 else []
        PuntYds = sample_list[28::stats_per_game] if len(sample_list) > 28 else []
        ThirdDownConv = sample_list[29::stats_per_game] if len(sample_list) > 29 else []
        ThirdDownAtt = sample_list[30::stats_per_game] if len(sample_list) > 30 else []
        FourthDownConv = sample_list[31::stats_per_game] if len(sample_list) > 31 else []
        FourthDownAtt = sample_list[32::stats_per_game] if len(sample_list) > 32 else []
        ToP = sample_list[33::stats_per_game] if len(sample_list) > 33 else []
        
        # Create database connection
        db_path = os.path.join('ncaafDb', f'{team}-{year}-{s}.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Create table
        cur.execute("""CREATE TABLE IF NOT EXISTS Stats(
            Week TEXT, Day TEXT, Date TEXT, OT TEXT, Opp TEXT, Tm TEXT, Opp2 TEXT,
            Cmp TEXT, Att TEXT, PassYds TEXT, PassTD TEXT, Int TEXT, Sk TEXT, SkYds TEXT,
            PassYA TEXT, PassNYA TEXT, CmpPct TEXT, PasserRate TEXT, RushAtt TEXT, RushYds TEXT,
            RushYA TEXT, RushTD TEXT, FGM TEXT, FGA TEXT, XPM TEXT, XPA TEXT, Pnt TEXT,
            PuntYds TEXT, ThirdDownConv TEXT, ThirdDownAtt TEXT, FourthDownConv TEXT,
            FourthDownAtt TEXT, ToP TEXT)""")
        
        # Insert data
        for i in range(len(Date)):
            try:
                cur.execute("""INSERT INTO Stats VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                          (Week[i] if i < len(Week) else '',
                           Day[i] if i < len(Day) else '',
                           Date[i] if i < len(Date) else '',
                           OT[i] if i < len(OT) else '',
                           Opp[i] if i < len(Opp) else '',
                           Tm[i] if i < len(Tm) else '',
                           Opp2[i] if i < len(Opp2) else '',
                           Cmp[i] if i < len(Cmp) else '',
                           Att[i] if i < len(Att) else '',
                           PassYds[i] if i < len(PassYds) else '',
                           PassTD[i] if i < len(PassTD) else '',
                           Int[i] if i < len(Int) else '',
                           Sk[i] if i < len(Sk) else '',
                           SkYds[i] if i < len(SkYds) else '',
                           PassYA[i] if i < len(PassYA) else '',
                           PassNYA[i] if i < len(PassNYA) else '',
                           CmpPct[i] if i < len(CmpPct) else '',
                           PasserRate[i] if i < len(PasserRate) else '',
                           RushAtt[i] if i < len(RushAtt) else '',
                           RushYds[i] if i < len(RushYds) else '',
                           RushYA[i] if i < len(RushYA) else '',
                           RushTD[i] if i < len(RushTD) else '',
                           FGM[i] if i < len(FGM) else '',
                           FGA[i] if i < len(FGA) else '',
                           XPM[i] if i < len(XPM) else '',
                           XPA[i] if i < len(XPA) else '',
                           Pnt[i] if i < len(Pnt) else '',
                           PuntYds[i] if i < len(PuntYds) else '',
                           ThirdDownConv[i] if i < len(ThirdDownConv) else '',
                           ThirdDownAtt[i] if i < len(ThirdDownAtt) else '',
                           FourthDownConv[i] if i < len(FourthDownConv) else '',
                           FourthDownAtt[i] if i < len(FourthDownAtt) else '',
                           ToP[i] if i < len(ToP) else ''))
            except Exception as e:
                print(f"Error inserting row {i}: {e}")
                continue
                
        conn.commit()
        conn.close()
        
        print(f"Successfully stored {len(Date)} games for {team} {year}")
        return True
        
    except Exception as e:
        print(f"Error scraping {team} {year}: {e}")
        return False

def ncaafAddGame(team, game_data):
    """
    Add a single game to NCAAF database
    """
    try:
        db_path = os.path.join('ncaafDb', f'{team}-{current_year}-stats.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        cur.execute("""INSERT INTO Stats VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  game_data)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding game: {e}")
        return False

# Common NCAAF teams for reference
NCAF_COMMON_TEAMS = [
    "alabama", "ohio-state", "clemson", "oklahoma", "georgia", 
    "notre-dame", "texas", "michigan", "florida", "lsu",
    "usc", "penn-state", "oregon", "auburn", "florida-state",
    "texas-am", "wisconsin", "miami-fl", "tennessee", "oklahoma-state"
]
