"""
Phase 7 — Optuna Hyperparameter Optimization
Efficient search for optimal XGBoost parameters
"""

import optuna
from optuna.samplers import TPESampler
from optuna.pruners import HyperbandPruner
import xgboost as xgb
from sklearn.metrics import mean_squared_error
import numpy as np
import pandas as pd
import yaml
import logging
from pathlib import Path
import joblib
from datetime import datetime

class OptunaOptimizer:
    """
    Optuna-based hyperparameter optimization for XGBoost dynamic blender.

    Strategy:
    - TPE Sampler (efficient Bayesian optimization)
    - Hyperband Pruner (early stopping of unpromising trials)
    - ~25 trials (hackathon time constraints)
    - Persistent SQLite study (resumable after interruption)
    """

    def __init__(self, config_path=None):
        self.logger = logging.getLogger("aether.optuna")

        # Load configuration
        if config_path:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                self.optuna_config = config.get('optuna', {})
        else:
            self.optuna_config = self._default_config()

        self.study = None
        self.best_params = None

    def _default_config(self):
        """Default Optuna configuration"""
        return {
            'n_trials': 25,
            'timeout_seconds': None,
            'sampler': {
                'type': 'TPESampler',
                'seed': 42,
                'n_startup_trials': 10
            },
            'pruner': {
                'type': 'HyperbandPruner',
                'min_resource': 10,
                'max_resource': 100,
                'reduction_factor': 3
            },
            'search_space': {
                'learning_rate': {'type': 'float', 'low': 0.01, 'high': 0.3, 'log': True},
                'max_depth': {'type': 'int', 'low': 3, 'high': 10},
                'min_child_weight': {'type': 'float', 'low': 0.5, 'high': 10.0},
                'subsample': {'type': 'float', 'low': 0.5, 'high': 1.0},
                'colsample_bytree': {'type': 'float', 'low': 0.5, 'high': 1.0},
                'reg_alpha': {'type': 'float', 'low': 0.0, 'high': 10.0},
                'reg_lambda': {'type': 'float', 'low': 0.0, 'high': 10.0},
                'n_estimators': {'type': 'int', 'low': 50, 'high': 200}
            },
            'study': {
                'storage': 'sqlite:///experiments/optuna_study.db',
                'study_name': 'aether_xgboost_v2_explicit',
                'direction': 'minimize',
                'load_if_exists': True
            }
        }

    def create_study(self):
        """Initialize Optuna study"""
        sampler_config = self.optuna_config['sampler']
        pruner_config = self.optuna_config['pruner']
        study_config = self.optuna_config['study']

        # Create sampler
        sampler = TPESampler(
            seed=sampler_config.get('seed', 42),
            n_startup_trials=sampler_config.get('n_startup_trials', 10)
        )

        # Create pruner
        pruner = HyperbandPruner(
            min_resource=pruner_config.get('min_resource', 10),
            max_resource=pruner_config.get('max_resource', 100),
            reduction_factor=pruner_config.get('reduction_factor', 3)
        )

        # Create study
        storage = study_config['storage']
        study_name = study_config['study_name']

        # Ensure experiments directory exists
        if 'sqlite:///' in storage:
            db_path = Path(storage.replace('sqlite:///', ''))
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self.study = optuna.create_study(
            study_name=study_name,
            storage=storage,
            sampler=sampler,
            pruner=pruner,
            direction=study_config['direction'],
            load_if_exists=study_config.get('load_if_exists', True)
        )

        self.logger.info(f"Optuna study created: {study_name}")
        self.logger.info(f"Storage: {storage}")
        self.logger.info(f"Sampler: TPESampler (seed={sampler_config.get('seed')})")
        self.logger.info(f"Pruner: HyperbandPruner")

    def objective(self, trial, X_train, y_train, X_val, y_val, feature_cols, device='cuda'):
        """
        Optuna objective function.

        Args:
            trial: Optuna trial object
            X_train, y_train: Training data
            X_val, y_val: Validation data
            feature_cols: List of feature column names
            device: 'cuda' or 'cpu'
        """
        # Sample hyperparameters from search space
        search_space = self.optuna_config['search_space']

        params = {}
        for param_name, param_config in search_space.items():
            if param_config['type'] == 'float':
                params[param_name] = trial.suggest_float(
                    param_name,
                    param_config['low'],
                    param_config['high'],
                    log=param_config.get('log', False)
                )
            elif param_config['type'] == 'int':
                params[param_name] = trial.suggest_int(
                    param_name,
                    param_config['low'],
                    param_config['high']
                )

        # Extract n_estimators for separate handling
        n_estimators = params.pop('n_estimators', 100)

        # XGBoost parameters
        xgb_params = {
            'objective': 'reg:squarederror',
            'device': device,
            'tree_method': 'hist',
            **params
        }

        # Train 3 models directly for evaluation
        # (Pruning removed since objective is complex multi-model blend)
        models = {}
        for candidate in ['IFS', 'ICON', 'GFS']:
            y_train_err = np.abs(X_train[:, feature_cols.index(candidate)] - y_train)

            model = xgb.XGBRegressor(
                n_estimators=n_estimators,
                **xgb_params
            )
            model.fit(X_train, y_train_err, verbose=False)
            models[candidate] = model

        # Evaluate on validation set
        blended = np.zeros(len(X_val))
        inv_weights = {}

        for candidate in ['IFS', 'ICON', 'GFS']:
            pred_err = models[candidate].predict(X_val)
            pred_err = np.clip(pred_err, 0.01, None)
            inv_weights[candidate] = 1.0 / pred_err

        total_inv = sum(inv_weights.values())

        for candidate in ['IFS', 'ICON', 'GFS']:
            w = inv_weights[candidate] / total_inv
            cand_val = X_val[:, feature_cols.index(candidate)]
            blended += w * cand_val

        rmse = np.sqrt(mean_squared_error(y_val, blended))

        return rmse

    def optimize(self, df_train, df_val, feature_cols, device='cuda'):
        """
        Run Optuna optimization.

        Args:
            df_train: Training DataFrame
            df_val: Validation DataFrame
            feature_cols: List of feature column names
            device: 'cuda' or 'cpu'
        """
        if self.study is None:
            self.create_study()

        # Prepare data
        X_train = df_train[feature_cols].values
        y_train = df_train['reference_value'].values
        X_val = df_val[feature_cols].values
        y_val = df_val['reference_value'].values

        self.logger.info(f"Starting Optuna optimization")
        self.logger.info(f"Training samples: {len(X_train)}, Validation samples: {len(X_val)}")
        self.logger.info(f"Features: {len(feature_cols)}")

        n_trials = self.optuna_config.get('n_trials', 25)
        timeout = self.optuna_config.get('timeout_seconds')

        self.logger.info(f"Target trials: {n_trials}")
        self.logger.info(f"Timeout: {timeout if timeout else 'None'}")

        # Run optimization
        self.study.optimize(
            lambda trial: self.objective(trial, X_train, y_train, X_val, y_val, feature_cols, device),
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=True
        )

        # Extract best parameters
        self.best_params = self.study.best_params
        best_value = self.study.best_value

        self.logger.info(f"Optimization complete!")
        self.logger.info(f"Best trial: {self.study.best_trial.number}")
        self.logger.info(f"Best validation RMSE: {best_value:.4f}")
        self.logger.info(f"Best parameters: {self.best_params}")

        return self.best_params, best_value

    def save_results(self, output_dir):
        """Save optimization results"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save best parameters
        params_path = output_dir / "best_params.yaml"
        with open(params_path, 'w') as f:
            yaml.dump(self.best_params, f)

        self.logger.info(f"Best parameters saved to {params_path}")

        # Save study summary
        summary = {
            'study_name': self.study.study_name,
            'best_trial': self.study.best_trial.number,
            'best_value': self.study.best_value,
            'n_trials': len(self.study.trials),
            'best_params': self.best_params,
            'completed_at': datetime.now().isoformat()
        }

        summary_path = output_dir / "optuna_summary.yaml"
        with open(summary_path, 'w') as f:
            yaml.dump(summary, f)

        self.logger.info(f"Study summary saved to {summary_path}")

        # Save full study object
        study_path = output_dir / "optuna_study.pkl"
        joblib.dump(self.study, study_path)

        self.logger.info(f"Study object saved to {study_path}")

        return params_path, summary_path, study_path
