
import datetime as dt
import requests
from bs4 import BeautifulSoup

now = dt.datetime.now()
today = f'{now.month},{now.day},{now.year}'

off_headers = [
    'Date','Home','Opp','Result','Cmp','Att','Pct','Yds','TD','Att','Yds','Avg','TD','Plays',
    'Yds','Avg','Pass','Rush','Pen','Tot','No',	'Yds','Fum','Int','Tot'
]

def_headers = [
    'Rk_Def2','Date_Def'	,'Location_Def','Opponent_Def','Result_Def','Cmp_Def','Att_Def','Pct_Def','Yds_Def','TD_Def','Att_Def','Yds_Def','Avg_Def','TD_Def','Plays_Def',
    'Yds_Def','Avg_Def','Pass_Def','Rush_Def','Pen_Def','Tot_Def','No_Def',	'Yds_Def','Fum_Def','Int_Def','Tot_Def'
]

def get_team_stats(team,year):
    url = f'https://www.sports-reference.com/cfb/schools/{team}/{year}/gamelog/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    off_body = soup.find(id='offense')
    off_tbody = off_body.find('tbody')
    off_rows = off_body.find_all('tr')   

    all_data = []
    for row in off_rows:
        cells = row.find_all('td')
        print(len(cells))
        if not cells:
            continue

        data = {
        header: cells[idx].text if len(cells) > idx else None
        for idx, header in enumerate(off_headers)
    }
        
        all_data.append(data)

    print(all_data)
    print(type(all_data))
    try:
        return all_data
    except Exception as e:
        return e



def get_player_stats(player,year):
    fname_lname = player.split(' ')
    fname = fname_lname[0]
    lname = fname_lname[1]
    letter = lname[0].lower()
    print(letter)
    player_id = lname[0:5] + fname[0:2] +'01'
    player_id = player_id.lower()
    print(player_id)
    #url = 'https://www.basketball-reference.com/players/{letter}/{player_id}/gamelog/{year}'
    #response = requests.get(url)
    #soup = BeautifulSoup(response.text, 'html.parser')
    #rows = soup.find_all('tr')

    #for row in rows:
        #print(row)

def get_coach_stats(coach):
    pass
