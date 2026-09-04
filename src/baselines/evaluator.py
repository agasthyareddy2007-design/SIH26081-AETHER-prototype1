"""
Phase 4 — Baselines
Trains and evaluates baseline forecasting models
"""

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging

class BaselineModels:
    """Manages baseline forecast evaluation"""

    def __init__(self):
        self.logger = logging.getLogger("aether.baselines")

    def evaluate_baselines(self, df: pd.DataFrame) -> dict:
        """
        Evaluates standard baselines against ERA5 reference.

        Args:
            df: Feature-engineered DataFrame with IFS, ICON, GFS, and reference_value
        """
        metrics = {}
        y_true = df['reference_value']

        # 1. Individual Model Baselines
        models = ['IFS', 'ICON', 'GFS']

        for model in models:
            if model in df.columns:
                y_pred = df[model]
                metrics[f"{model}_alone"] = {
                    'mae': mean_absolute_error(y_true, y_pred),
                    'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
                    'bias': np.mean(y_pred - y_true)
                }

        # 2. Simple Arithmetic Average
        available_models = [m for m in models if m in df.columns]
        if available_models:
            y_pred_avg = df[available_models].mean(axis=1)
            metrics['simple_average'] = {
                'mae': mean_absolute_error(y_true, y_pred_avg),
                'rmse': np.sqrt(mean_squared_error(y_true, y_pred_avg)),
                'bias': np.mean(y_pred_avg - y_true)
            }

            self.logger.info(f"Simple average MAE: {metrics['simple_average']['mae']:.4f}")

        return metrics
