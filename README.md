# NBA Betting Prediction Pipeline

A comprehensive machine learning pipeline for NBA game predictions and betting analysis. This project combines data collection, model training, and prediction capabilities with betting analytics including Expected Value and Kelly Criterion calculations.

## Features

- 🏀 Automated data collection from NBA stats and various sportsbooks
- 📊 Machine learning model training (LGBM)
- 🎲 Game predictions with confidence scores
- 💰 Betting analysis with Expected Value calculations
- 📈 Kelly Criterion for optimal bet sizing
- 🎯 Support for multiple sportsbooks
- 🔄 Prefect integration for workflow management
- 🌈 Colorful terminal interface for results

## Project Structure

```
├── config.toml                            
├── pipeline/
│   ├── data_collection_pipeline.py  
│   ├── model_training_pipeline.py   
│   ├── prediction_pipeline.py   
│   ├── main.py   
│   ├── utils/
│       ├── kelly_criterion.py       
│       ├── expected_value.py        
│       ├── team_code_index.py       
│       ├── today_game.py           
│       ├── today_odds.py            
│       └── tools.py                 
├── data/                 
└── model/                           
```

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Running the Full Pipeline

```bash
python main.py --stage all
```

### Running Individual Stages

Data Collection:
```bash
python main.py --stage collect
```

Model Training:
```bash
python main.py --stage train
```

Game Prediction:
```bash
python main.py --stage predict --sportsbook fanduel --kelly-criterion
```

### Command Line Arguments

- `--stage`: Pipeline stage to run (`collect`, `train`, `predict`, or `all`)
- `--model`: Model to use for predictions (currently supports `lgbm`)
- `--sportsbook`: Sportsbook to fetch odds from (options: `fanduel`, `draftkings`, `betmgm`, `pointsbet`, `caesars`, `wynn`, `bet_rivers_ny`)
- `--kelly-criterion`: Enable Kelly Criterion for betting recommendations
- `--verbose`: Increase output verbosity

## Notes

- To save time during data collection, comment out older seasons in the `config.toml` file. The relevant sections are under `[fetch-data]`.
- In the `model_training_pipeline.py`, you can adjust the hyperparameters if you want to improve the existing models. Look for the `params` dictionaries in the training functions.
- Models are saved with their precision percentage in the filename for easy tracking of improvements.
- My 2 pre-train models have ~55% for under/over and ~73% for moneyline 

## Data Flow

1. **Data Collection**:
   - Team statistics from NBA API
   - Betting odds from sportsbooks
   - Rest days calculation

2. **Data Processing**:
   - Merging team and odds data
   - Feature engineering
   - Database storage

3. **Model Training**:
   - LightGBM classifier models
   - Cross-validation for model selection
   - Separate models for Money Line and Over/Under

4. **Prediction**:
   - Current game matchup analysis
   - Probability-based predictions
   - Expected value calculation
   - Kelly Criterion for bet sizing

## Disclaimer

This system is for educational purposes only.