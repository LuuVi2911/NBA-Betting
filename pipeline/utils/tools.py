import re
from datetime import datetime
import pandas as pd
import requests
from .team_code_index import team_index_current

custom_user_agent = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/537.36 (KHTML, like Gecko)'
                     ' Chrome/134.0.6998.118 Safari/537.36')

games_request_headers = {
    'User-Agent': custom_user_agent,
    'Dnt': '1',
    'Accept-Encoding': 'gzip, deflate, sdch',
    'Accept-Language': 'en',
    'origin': 'http://stats.nba.com',
    'Referer': 'https://github.com'
}
data_request_headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Host': 'stats.nba.com',
    'User-Agent': custom_user_agent,
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.nba.com/',
    'Connection': 'keep-alive'
}

def fetch_json_data(url):
    raw_data = requests.get(url, headers=data_request_headers)
    try:
        json_data = raw_data.json()
    except Exception as e:
        print(f"Error fetching JSON: {e}")
        return {}
    return json_data.get('resultSets')

def fetch_today_games_json(url):
    raw_data = requests.get(url, headers=games_request_headers)
    json_data = raw_data.json()
    return json_data.get('gs', {}).get('g', [])

def convert_json_to_df(data):
    try:
        data_list = data[0]
    except Exception as e:
        print(f"Error processing data: {e}")
        return pd.DataFrame()
    return pd.DataFrame(data=data_list.get('rowSet'), columns=data_list.get('headers'))

def create_todays_games_list(game_data):
    games = []
    for game in game_data:
        home_team = game.get('h')
        away_team = game.get('v')
        home_team_name = home_team.get('tc') + ' ' + home_team.get('tn')
        away_team_name = away_team.get('tc') + ' ' + away_team.get('tn')
        games.append([home_team_name, away_team_name])
    return games

def create_games_from_odds(odds_data):
    games = []
    for game in odds_data.keys():
        home_team, away_team = game.split(":")
        if home_team not in team_index_current or away_team not in team_index_current:
            continue
        games.append([home_team, away_team])
    return games

def parse_game_date(date_string):
    year1, month, day = re.search(r'(\d+)-\d+-(\d\d)(\d\d)', date_string).groups()
    year = year1 if int(month) > 8 else int(year1) + 1
    return datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d')
