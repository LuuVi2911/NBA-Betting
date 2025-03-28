"""
NBA Game Prediction Pipeline with Prefect integration
"""
import os
import sys
import pickle
import random
from datetime import datetime
import numpy as np
import pandas as pd
from prefect import flow, task
from colorama import Fore, Style, init, deinit

from pipeline.utils.today_odds import get_sbr_odds
from pipeline.utils.today_game import create_today_game
from pipeline.utils.expected_value import expected_value
from pipeline.utils import kelly_criterion as kc
from pipeline.utils.tools import fetch_json_data, convert_json_to_df


@task
def get_random_color():
    """Task to get random color for output formatting"""
    return random.choice([
        Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.CYAN, Fore.MAGENTA
    ])


@task
def load_models(model_type='lgbm'):
    """Task to load prediction models"""
    if model_type == 'lgbm':
        with open('../model/LGBM_ML_model.pkl', 'rb') as f:
            ml_model = pickle.load(f)
        with open('../model/LGBM_UO_model.pkl', 'rb') as f:
            ou_model = pickle.load(f)
    return ml_model, ou_model


@task
def display_prediction(home_team, away_team, ml_pred, ou_pred, ou_value):
    """Task to display game predictions"""
    winner = np.argmax(ml_pred)
    winner_confidence = round(ml_pred[winner] * 100, 1)
    under_over = np.argmax(ou_pred)
    un_confidence = round(ou_pred[under_over] * 100, 1)

    winner_color = Fore.GREEN if winner == 1 else Fore.RED
    loser_color = Fore.RED if winner == 1 else Fore.GREEN
    ou_status_color = Fore.MAGENTA if under_over == 0 else Fore.BLUE

    ou_text = "UNDER" if under_over == 0 else "OVER"
    winner_team = home_team if winner == 1 else away_team
    loser_team = away_team if winner == 1 else home_team

    print(
        f"{winner_color}{Style.BRIGHT}{winner_team}{Style.RESET_ALL} "
        f"{Fore.CYAN}{Style.BRIGHT}({winner_confidence}%){Style.RESET_ALL} "
        f"vs {loser_color}{Style.BRIGHT}{loser_team}{Style.RESET_ALL}: "
        f"{ou_status_color}{Style.BRIGHT}{ou_text} "
        f"{ou_value} ({un_confidence}%){Style.RESET_ALL}"
    )
    return winner, winner_confidence, under_over, un_confidence


@task
def display_betting_analysis(home_team, away_team, ml_prediction, team_odds, ev_values, bankroll_fractions):
    """Task to display betting analysis"""
    ev_home, ev_away = ev_values
    bankroll_home, bankroll_away = bankroll_fractions

    # Color coding
    home_team_color = get_random_color()
    away_team_color = get_random_color()
    ev_home_color = Fore.GREEN if ev_home > 0 else Fore.RED
    ev_away_color = Fore.GREEN if ev_away > 0 else Fore.RED
    bankroll_color = Fore.GREEN + Style.BRIGHT if bankroll_home > 0 else Fore.RED + Style.BRIGHT

    print(f"{home_team_color}{Style.BRIGHT}{home_team}{Style.RESET_ALL} "
          f"EV: {ev_home_color}{ev_home}{Style.RESET_ALL} "
          f"{Style.BRIGHT}Bankroll: {Style.RESET_ALL}{bankroll_color}"
          f"{str(bankroll_home)}%{Style.RESET_ALL}")

    print(f"{away_team_color}{Style.BRIGHT}{away_team}{Style.RESET_ALL} "
          f"EV: {ev_away_color}{ev_away}{Style.RESET_ALL} "
          f"{Style.BRIGHT}Bankroll: {Style.RESET_ALL}{bankroll_color}"
          f"{str(bankroll_away)}%{Style.RESET_ALL}")


@flow()
def prediction_pipeline(
        sportsbook='fanduel',
        use_kelly_criterion=False,
        model_type='lgbm'
):
    """
    Comprehensive Prediction Pipeline with Prefect
    """
    init()

    try:
        # 1. Fetch today's games and odds
        print(f"Fetching games and odds from {sportsbook}")
        odds = get_sbr_odds(sportsbook=sportsbook)
        if not odds:
            print("No odds data available")
            return

        # Prepare team data URL
        data_url = 'https://stats.nba.com/stats/leaguedashteamstats?' \
                   'Conference=&DateFrom=&DateTo=&Division=&GameScope=&' \
                   'GameSegment=&LastNGames=0&LeagueID=00&Location=&' \
                   'MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&' \
                   'PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&' \
                   'PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&' \
                   'Season=2024-25&SeasonSegment=&SeasonType=Regular+Season&ShotClockRange=&' \
                   'StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision='

        # Fetch and prepare data
        raw_data = fetch_json_data(data_url)
        df = convert_json_to_df(raw_data)

        # Create games list from odds
        games = [(teams.split(':')[0], teams.split(':')[1]) for teams in odds.keys()]

        # 2. Prepare game data
        print("Preparing game data for prediction")
        data, todays_games_uo, frame_ml, home_team_odds, away_team_odds = create_today_game(games, df, odds)

        # 3. Load models
        print(f"Loading {model_type.upper()} models")
        ml_model, ou_model = load_models(model_type)

        # 4. Make predictions
        print("Running predictions")
        ml_predictions = ml_model.predict_proba(data)

        # Prepare OU data
        frame_uo = frame_ml.copy()
        frame_uo['OU'] = np.asarray(todays_games_uo)
        ou_data = frame_uo.values.astype(float)
        ou_predictions = ou_model.predict_proba(ou_data)

        # 5. Display Predictions
        print(f"{Fore.GREEN}{Style.BRIGHT}------------- NBA Game Predictions -------------{Style.RESET_ALL}")

        for count, (home_team, away_team) in enumerate(games):
            display_prediction(
                home_team, away_team,
                ml_predictions[count],
                ou_predictions[count],
                todays_games_uo[count]
            )

        # 6. Calculate Expected Value and Kelly Criterion
        if use_kelly_criterion:
            print(
                f"{Style.BRIGHT}{Fore.YELLOW}------------Expected Value & Kelly Criterion-----------{Style.RESET_ALL}")

            for i, (home_team, away_team) in enumerate(games):
                ml_prediction = ml_predictions[i]

                # Calculate EV and Kelly
                ev_home = ev_away = 0
                if home_team_odds[i] and away_team_odds[i]:
                    ev_home = float(expected_value(ml_prediction[1], float(home_team_odds[i])))
                    ev_away = float(expected_value(ml_prediction[0], float(away_team_odds[i])))

                bankroll_home = kc.calculate_kelly_criterion(home_team_odds[i], ml_prediction[1])
                bankroll_away = kc.calculate_kelly_criterion(away_team_odds[i], ml_prediction[0])

                display_betting_analysis(
                    home_team, away_team,
                    ml_prediction,
                    (home_team_odds[i], away_team_odds[i]),
                    (ev_home, ev_away),
                    (bankroll_home, bankroll_away)
                )

        print("Prediction pipeline completed successfully")

    except Exception as e:
        print(f"Prediction pipeline failed: {e}")
    finally:
        deinit()


if __name__ == "__main__":
    prediction_pipeline()