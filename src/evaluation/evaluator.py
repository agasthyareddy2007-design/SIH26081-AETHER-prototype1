"""
Phase 8 — Evaluation
Evaluates final models on the test set and breakdown by conditions
"""

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging
from pathlib import Path
import json

class Evaluator:
    def __init__(self, output_dir: Path):
        self.logger = logging.getLogger("aether.evaluation")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def calculate_metrics(self, y_true, y_pred) -> dict:
        return {
            'mae': float(mean_absolute_error(y_true, y_pred)),
            'rmse': float(np.sqrt(mean_squared_error(y_true, y_pred))),
            'bias': float(np.mean(y_pred - y_true))
        }

    def evaluate_test_set(self, df_test: pd.DataFrame, xgboost_model, static_weights: dict) -> dict:
        self.logger.info("Evaluating on untouched test set...")
        y_true = df_test['reference_value'].values

        results = {}

        # 1. Baselines
        for model in ['IFS', 'ICON', 'GFS']:
            if model in df_test.columns:
                results[f"{model}_alone"] = self.calculate_metrics(y_true, df_test[model].values)

        # 2. Simple Average
        available_models = [m for m in ['IFS', 'ICON', 'GFS'] if m in df_test.columns]
        y_pred_avg = df_test[available_models].mean(axis=1).values
        results["simple_average"] = self.calculate_metrics(y_true, y_pred_avg)

        # 3. Static Blend
        static_w = np.array([static_weights.get(m, 0) for m in available_models])
        y_pred_static = df_test[available_models].values @ static_w
        results["static_blend"] = self.calculate_metrics(y_true, y_pred_static)

        # 4. XGBoost Dynamic
        y_pred_xgb = xgboost_model.predict(df_test)
        results["xgboost_dynamic"] = self.calculate_metrics(y_true, y_pred_xgb)

        # Calculate Error Reduction vs Simple Average
        rmse_avg = results["simple_average"]["rmse"]
        rmse_xgb = results["xgboost_dynamic"]["rmse"]
        reduction = ((rmse_avg - rmse_xgb) / rmse_avg) * 100
        self.logger.info(f"XGBoost vs Simple Average RMSE reduction: {reduction:.2f}%")
        results["error_reduction_pct"] = reduction

        # Lead Time Breakdown
        breakdown = {}
        for lt in df_test['lead_time'].unique():
            mask = df_test['lead_time'] == lt
            lt_true = y_true[mask]
            lt_xgb = y_pred_xgb[mask]
            lt_avg = y_pred_avg[mask]
            breakdown[str(lt)] = {
                'samples': int(mask.sum()),
                'xgboost_rmse': float(np.sqrt(mean_squared_error(lt_true, lt_xgb))),
                'average_rmse': float(np.sqrt(mean_squared_error(lt_true, lt_avg)))
            }

        # Save metrics
        metrics = {
            'overall': results,
            'lead_time_breakdown': breakdown
        }

        metrics_file = self.output_dir / "test_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)

        self.logger.info(f"Evaluation metrics saved to {metrics_file}")
        return metrics
