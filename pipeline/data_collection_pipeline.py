"""
Data Collection Pipeline for NBA Statistics
"""
import os
import re
import random
import time
import sqlite3
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import toml
from sbrscrape import Scoreboard
from prefect import flow, task
from prefect.task_runners import ThreadPoolTaskRunner
from tqdm import tqdm
from pipeline.utils.tools import fetch_json_data, convert_json_to_df
from pipeline.utils.team_code_index import (
    team_index_10, team_index_12, team_index_13,
    team_index_14, team_index_current
)
@task(log_prints=True)
def process_csv_file(config, odd_db_path):
    """Process CSV odds data file into season tables"""
    csv_path = '../data/OddsData.csv'
    output_folder = '../data/csv/'
    os.makedirs(output_folder, exist_ok=True)

    conn = sqlite3.connect(odd_db_path)
    data = pd.read_csv(csv_path)
    data['Date'] = pd.to_datetime(data['Date'], yearfirst=True).dt.date

    for season_key, season_data in config['fetch-data'].items():
        start = datetime.strptime(season_data["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(season_data["end_date"], "%Y-%m-%d").date()
        season_df = data[(data['Date'] >= start) & (data['Date'] <= end)]
        season_df.to_csv(f"{output_folder}odds_{season_key}.csv", index=False)
        season_df.to_sql(f"odds_{season_key}", conn, if_exists="replace", index=False)

    conn.close()
    print("CSV processing completed.")


@task(log_prints=True)
def fetch_team_data(config, team_db_path):
    """Fetch team statistics data for each day in the season"""
    url = config['data-url']['data-url']
    conn = sqlite3.connect(team_db_path)
    cursor = conn.cursor()

    for season_key, season_value in config['fetch-data'].items():
        start_date = datetime.strptime(season_value['start_date'], "%Y-%m-%d").date()
        end_date = datetime.strptime(season_value['end_date'], "%Y-%m-%d").date()
        current_date = start_date

        while current_date <= end_date:
            url_data = url.format(
                current_date.month,
                current_date.day,
                season_value['start_year'],
                current_date.year,
                season_key
            )
            print(f"Fetching {current_date}")

            raw_data = fetch_json_data(url_data)
            if raw_data:
                data = convert_json_to_df(raw_data)
                columns = ', '.join([f'"{col}" TEXT' for col in data.columns])
                create_table_query = (f"CREATE TABLE IF NOT EXISTS '{current_date.strftime('%Y-%m-%d')}'"
                                      f" ({columns}, 'Date' TEXT);")
                cursor.execute(create_table_query)
                conn.commit()
                data['Date'] = str(current_date)
                data.to_sql(current_date.strftime('%Y-%m-%d'), conn, if_exists='replace', index=True)
            else:
                print(f"No data for {current_date}")

            current_date += timedelta(days=1)
            time.sleep(random.uniform(0.5, 2))

    conn.close()
    print("Team data fetching completed.")


@task(log_prints=True)
def fetch_odd_data(config, odd_db_path):
    """Fetch betting odds data from sportsbooks"""
    sportsbook = 'bet365'
    conn = sqlite3.connect(odd_db_path)

    for season_key, season_value in config['fetch-odd-data'].items():
        current_day = datetime.strptime(season_value['start_date'], "%Y-%m-%d").date()
        end_date = datetime.strptime(season_value['end_date'], "%Y-%m-%d").date()
        data = []

        while current_day <= end_date:
            print(f"Fetching odds: {current_day}")
            sb = Scoreboard(date=current_day)

            if not hasattr(sb, "games"):
                current_day = current_day + timedelta(days=1)
                continue

            for game in sb.games:
                try:
                    data.append({
                        'Date': current_day,
                        'Home': game['home_team'],
                        'Away': game['away_team'],
                        'OU': game['total'][sportsbook],
                        'Spread': game['away_spread'][sportsbook],
                        'ML_Home': game['home_ml'][sportsbook],
                        'ML_Away': game['away_ml'][sportsbook],
                        'Points': game['away_score'] + game['home_score'],
                        'Win_Margin': game['home_score'] - game['away_score'],
                    })
                except KeyError:
                    print(f"No {sportsbook} odds data for: {game}")

            current_day = current_day + timedelta(days=1)
            time.sleep(random.uniform(0.3, 1.0))

        df = pd.DataFrame(data)
        df.to_sql(f'odds_{season_key}', conn, if_exists="replace", index=True)

    conn.close()
    print("Odds data fetching completed.")


@task(log_prints=True)
def process_odd_data(odd_db_path):
    """Process odd data to calculate rest days for teams"""
    conn = sqlite3.connect(odd_db_path)

    tables = [
        'odds_2010-11', 'odds_2011-12', 'odds_2012-13', 'odds_2013-14', 'odds_2014-15', 'odds_2015-16',
        'odds_2016-17', 'odds_2017-18', 'odds_2018-19', 'odds_2019-20', 'odds_2020-21', 'odds_2021-22',
        'odds_2022-23', 'odds_2023-24', 'odds_2024-25'
    ]

    def get_date(date_string):
        year, month, day = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_string).groups()
        return datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d')

    for table in tqdm(tables):
        try:
            data = pd.read_sql_query(f'SELECT * FROM "{table}"', conn, index_col="index")
            teams_last_played = {}

            for index, row in data.iterrows():
                if 'Home' not in row or 'Away' not in row:
                    continue

                # Process home team rest days
                if row['Home'] not in teams_last_played:
                    teams_last_played[row['Home']] = get_date(row['Date'])
                    home_games_rested = 10
                else:
                    current_date = get_date(row['Date'])
                    days_diff = (current_date - teams_last_played[row['Home']]).days
                    home_games_rested = days_diff if 0 < days_diff < 9 else 9
                    teams_last_played[row['Home']] = current_date

                # Process away team rest days
                if row['Away'] not in teams_last_played:
                    teams_last_played[row['Away']] = get_date(row['Date'])
                    away_games_rested = 10
                else:
                    current_date = get_date(row['Date'])
                    days_diff = (current_date - teams_last_played[row['Away']]).days
                    away_games_rested = days_diff if 0 < days_diff < 9 else 9
                    teams_last_played[row['Away']] = current_date

                data.at[index, 'Days_Rest_Home'] = home_games_rested
                data.at[index, 'Days_Rest_Away'] = away_games_rested

            data.to_sql(table, conn, if_exists="replace")
        except Exception as e:
            print(f"Error processing {table}: {e}")

    conn.close()
    print("Odds data processing completed.")


@task(log_prints=True)
def merge_data(config, team_db_path, odd_db_path, output_db_path):
    """Merge team stats and odds data into final dataset"""
    team_conn = sqlite3.connect(team_db_path)
    odd_conn = sqlite3.connect(odd_db_path)
    conn = sqlite3.connect(output_db_path)

    scores = []
    win_margin = []
    OU = []
    OU_Cover = []
    games = []
    days_rest_away = []
    days_rest_home = []

    for key, value in config['create-game'].items():
        season = key
        print(f'Processing {season}')

        try:
            odds_df = pd.read_sql_query(f'SELECT * FROM "odds_{key}"', odd_conn, index_col='index')

            for row in odds_df.itertuples():
                home_team = row.Home
                away_team = row.Away
                date = row.Date

                try:
                    team_df = pd.read_sql_query(f'SELECT * FROM "{date}"', team_conn, index_col='index')

                    if len(team_df.index) == 30:
                        scores.append(row.Points)
                        OU.append(row.OU)
                        days_rest_home.append(row.Days_Rest_Home)
                        days_rest_away.append(row.Days_Rest_Away)

                        # Set win margin binary value
                        win_margin.append(1 if row.Win_Margin > 0 else 0)

                        # Set OU cover binary value
                        OU_Cover.append(1 if row.Points > row.OU else 0)

                        # Get correct team index based on season
                        if season in ('2010-11', '2011-12'):
                            home_team_series = team_df.iloc[team_index_10.get(home_team)]
                            away_team_series = team_df.iloc[team_index_10.get(away_team)]
                        elif season == '2012-13':
                            home_team_series = team_df.iloc[team_index_12.get(home_team)]
                            away_team_series = team_df.iloc[team_index_12.get(away_team)]
                        elif season == '2013-14':
                            home_team_series = team_df.iloc[team_index_13.get(home_team)]
                            away_team_series = team_df.iloc[team_index_13.get(away_team)]
                        elif season in ('2022-23', '2023-24', '2024-25'):
                            home_team_series = team_df.iloc[team_index_current.get(home_team)]
                            away_team_series = team_df.iloc[team_index_current.get(away_team)]
                        else:
                            home_team_series = team_df.iloc[team_index_14.get(home_team)]
                            away_team_series = team_df.iloc[team_index_14.get(away_team)]

                        # Concatenate home and away team data
                        game = pd.concat([
                            home_team_series,
                            away_team_series.rename(index={col: f'{col}.1' for col in team_df.columns.values})
                        ])
                        games.append(game)
                except Exception as e:
                    print(f"Error processing game {date}, {home_team} vs {away_team}: {e}")
        except Exception as e:
            print(f"Error processing season {season}: {e}")

    # Create final dataset
    if games:
        season = pd.concat(games, ignore_index=True, axis=1)
        season = season.T
        frame = season.drop(columns=['TEAM_ID', 'TEAM_ID.1'])
        frame['Score'] = np.asarray(scores)
        frame['Home-Team-Win'] = np.asarray(win_margin)
        frame['OU'] = np.asarray(OU)
        frame['OU-Cover'] = np.asarray(OU_Cover)
        frame['Days-Rest-Home'] = np.asarray(days_rest_home)
        frame['Days-Rest-Away'] = np.asarray(days_rest_away)

        # Convert numeric columns to float
        for field in frame.columns.values:
            if 'TEAM_' in field or 'Date' in field or field not in frame:
                continue
            frame[field] = frame[field].astype(float)

        frame.to_sql('dataset', conn, if_exists='replace')
        print(f"Final dataset created with {len(frame)} records")
    else:
        print("No games data to merge")

    conn.close()
    team_conn.close()
    odd_conn.close()
    print("Data merging completed.")


@flow(log_prints=True)
def data_collection_pipeline(
        config_path='../config.toml',
        team_db_path='../data/TeamData.db',
        odd_db_path='../data/OddData.db',
        output_db_path='../data/Dataset.db'
):
    """
    Comprehensive Data Collection Pipeline

    Phases:
    1. Process CSV odds data
    2. Fetch team statistics and odds data in parallel
    3. Process odd data with rest days
    4. Merge collected data
    """

    os.makedirs(os.path.dirname(team_db_path), exist_ok=True)
    os.makedirs(os.path.dirname(odd_db_path), exist_ok=True)
    os.makedirs(os.path.dirname(output_db_path), exist_ok=True)
    config = toml.load(config_path)

    # Process CSV file first
    process_csv_file(config, odd_db_path)

    # Run team data and odds data fetching in parallel using .submit()
    task_runner = ThreadPoolTaskRunner()
    with task_runner:
        team_future = fetch_team_data.submit(config, team_db_path)
        odds_future = fetch_odd_data.submit(config, odd_db_path)
        team_result = team_future.result()
        odds_result = odds_future.result()

    # Continue with sequential tasks that depend on the parallel tasks
    process_odd_data(odd_db_path)
    merge_data(config, team_db_path, odd_db_path, output_db_path)


def main():
    """
    Entry point for data collection pipeline
    """
    data_collection_pipeline()


if __name__ == "__main__":
    main()