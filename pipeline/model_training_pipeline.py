"""
Machine Learning Model Training Pipeline for NBA Predictions
"""
import os
import pickle
from datetime import datetime
import numpy as np
import pandas as pd
import sqlite3
import lightgbm as lgb
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import precision_score
from prefect import flow


@flow(log_prints=True)
def model_training_pipeline(
        dataset_path='../data/Dataset.db',
        model_output_path='../model'
):
    """
    Comprehensive Machine Learning Model Training Pipeline

    Phases:
    1. Load and preprocess data
    2. Train Money Line prediction model
    3. Train Over/Under prediction model
    4. Save best performing models
    """
    # Ensure model output directory exists
    os.makedirs(model_output_path, exist_ok=True)

    # Load dataset
    conn = sqlite3.connect(dataset_path)
    data = pd.read_sql('SELECT * FROM dataset', conn)

    # Prepare Money Line Model
    def train_ml_model():
        print("Training Money Line Prediction Model")

        # Prepare data
        y = data['Home-Team-Win']
        X = data.drop(['Home-Team-Win', 'Score', 'OU', 'OU-Cover',
                       'TEAM_NAME.1','TEAM_NAME', 'Date','index','Date.1'], axis=1)
        X = X.values.astype(float)

        best_precision = 0
        best_model = None

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=100)

        for iteration in range(100):  # Multiple iterations for model robustness
            for train_index, test_index in cv.split(X, y):
                X_train, X_test = X[train_index], X[test_index]
                y_train, y_test = y.iloc[train_index], y.iloc[test_index]

                # LightGBM parameters
                params = {
                    'objective': 'binary',
                    'learning_rate': 0.05,
                    'max_depth': 10,
                    'min_child_samples': 20,
                    'n_estimators': 500,
                    'num_leaves': 30,
                    'boosting_type': 'gbdt',
                    'is_unbalance': False,
                    'n_jobs': 4,
                    'force_row_wise': True
                }

                model = lgb.LGBMClassifier(**params)
                model.fit(X_train, y_train)

                y_pred = model.predict(X_test)
                precision = precision_score(y_test, y_pred)

                if precision > best_precision:
                    best_precision = precision
                    best_model = model

        # Save best model
        model_filename = f'{model_output_path}/LGBM_{best_precision * 100:.2f}%_ML_model.pkl'
        with open(model_filename, 'wb') as f:
            pickle.dump(best_model, f)

        print(f"Money Line Model trained with {best_precision * 100:.2f}% precision")
        return best_precision

    # Prepare Over/Under Model
    def train_ou_model():
        print("Training Over/Under Prediction Model")

        # Prepare data
        y = data['OU-Cover']
        X = data.drop(['OU-Cover', 'Score', 'Home-Team-Win',
                       'TEAM_NAME1','TEAM_NAME', 'Date', 'index','Date.1'], axis=1)
        X = X.values.astype(float)

        best_precision = 0
        best_model = None

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=100)

        for iteration in range(100):  # Multiple iterations for model robustness
            for train_index, test_index in cv.split(X, y):
                X_train, X_test = X[train_index], X[test_index]
                y_train, y_test = y.iloc[train_index], y.iloc[test_index]

                # LightGBM parameters
                params = {
                    'objective': 'binary',
                    'learning_rate': 0.05,
                    'max_depth': 10,
                    'min_child_samples': 20,
                    'n_estimators': 500,
                    'num_leaves': 30,
                    'boosting_type': 'gbdt',
                    'is_unbalance': False,
                    'n_jobs': 4,
                    'force_row_wise': True
                }

                model = lgb.LGBMClassifier(**params)
                model.fit(X_train, y_train)

                y_pred = model.predict(X_test)
                precision = precision_score(y_test, y_pred)

                if precision > best_precision:
                    best_precision = precision
                    best_model = model

        # Save best model
        model_filename = f'{model_output_path}/LGBM_{best_precision * 100:.2f}%_OU_model.pkl'
        with open(model_filename, 'wb') as f:
            pickle.dump(best_model, f)

        print(f"Over/Under Model trained with {best_precision * 100:.2f}% precision")
        return best_precision

    # Execute model training
    ml_precision = train_ml_model()
    ou_precision = train_ou_model()


def main():
    """
    Entry point for model training pipeline
    """
    model_training_pipeline()

if __name__ == "__main__":
    main()