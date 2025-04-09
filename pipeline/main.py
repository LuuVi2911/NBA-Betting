"""
NBA Prediction Pipeline Runner

This script provides a unified interface to run different stages
of the NBA prediction pipeline with Prefect integration.
"""
import argparse
import sys
import os
from colorama import init, deinit

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from pipeline.data_collection_pipeline import main as data_collection_main
from pipeline.model_training_pipeline import main as model_training_main
from pipeline.prediction_pipeline import prediction_pipeline
from pipeline.utils.today_odds import get_sbr_odds
from pipeline.utils.tools import (
    fetch_today_games_json,
    create_games_from_odds,
    create_todays_games_list
)


def check_odds_data(odds, games):
    """Helper function to validate odds data"""
    if len(games) == 0:
        print("No games found.")
        return None
    if (games[0][0] + ':' + games[0][1]) not in list(odds.keys()):
        print(f"Games list not up to date for today game")
        return None
    return odds


def main():
    """
    Main entry point for the NBA prediction pipeline
    Supports running individual stages or the entire pipeline
    """
    parser = argparse.ArgumentParser(description='NBA Prediction Pipeline')

    # Stage selection
    parser.add_argument('--stage',
                        choices=['collect', 'train', 'predict', 'all'],
                        default='predict',
                        help='Pipeline stage to run')

    # Prediction-specific options
    parser.add_argument('--sportsbook',
                        default='fanduel',
                        choices=['fanduel', 'draftkings', 'betmgm', 'pointsbet',
                                 'caesars', 'wynn', 'bet_rivers_ny'],
                        help='Sportsbook to fetch odds from')

    parser.add_argument('--kc',
                        action='store_true',
                        help='Use Kelly Criterion for betting recommendations')

    # Logging and verbosity
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Increase output verbosity')

    args = parser.parse_args()
    init()

    try:
        if args.stage in ['collect', 'all']:
            print("🏀 Starting Data Collection Pipeline...")
            data_collection_main()

        if args.stage in ['train', 'all']:
            print("📊 Starting Model Training Pipeline...")
            model_training_main()

        if args.stage in ['predict', 'all']:
            print("🎲 Starting Prediction Pipeline...")

            # Get odds data
            odds = None
            if args.sportsbook:
                odds = get_sbr_odds(sportsbook=args.sportsbook)
                if odds:
                    games = create_games_from_odds(odds)
                    odds = check_odds_data(odds, games)
            else:
                today_games_url = 'https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/2024/scores/00_todays_scores.json'
                data = fetch_today_games_json(today_games_url)
                games = create_todays_games_list(data)

            # Run prediction pipeline with appropriate model
            prediction_pipeline(
                sportsbook=args.sportsbook,
                use_kelly_criterion=args.kc,
            )

        print("🏆 Pipeline Completed Successfully!")

    except Exception as e:
        print(f"❌ Pipeline Execution Failed: {e}")
        sys.exit(1)
    finally:
        deinit()


if __name__ == "__main__":
    main()