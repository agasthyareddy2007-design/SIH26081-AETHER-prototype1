"""
Phase 9 — Uncertainty Estimation
Estimates and validates forecast uncertainty
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json

class UncertaintyEstimator:
    def __init__(self):
        self.logger = logging.getLogger("aether.uncertainty")

    def estimate(self, model_forecasts: dict, env_factors: dict = None) -> dict:
        """
        Estimate uncertainty for a single forecast instance.

        Args:
            model_forecasts: dict of {'IFS': x, 'ICON': y, 'GFS': z}
            env_factors: Optional additional context (e.g., lead_time)

        Returns:
            dict containing uncertainty metrics
        """
        values = list(model_forecasts.values())
        spread = float(np.std(values))
        range_val = float(np.max(values) - np.min(values))

        # Base uncertainty on spread, heavily inflated by lead time if available
        lead_time = env_factors.get('lead_time', 24) if env_factors else 24

        # Simple heuristic scaling for V1: Base model spread + time penalty
        uncertainty = spread + (0.01 * lead_time)

        # Confidence classification
        if uncertainty < 1.0:
            confidence = "High"
        elif uncertainty < 2.5:
            confidence = "Medium"
        else:
            confidence = "Low"

        return {
            'uncertainty_value': float(uncertainty),
            'model_spread_std': spread,
            'model_range': range_val,
            'confidence_level': confidence
        }

    def validate(self, df_test: pd.DataFrame, xgboost_model, output_dir: Path) -> dict:
        """Validate the relationship between uncertainty and actual error."""
        self.logger.info("Validating uncertainty estimation on test set...")

        y_true = df_test['reference_value'].values
        y_pred = xgboost_model.predict(df_test)
        actual_errors = np.abs(y_true - y_pred)

        # Calculate uncertainty for dataset
        uncertainties = []
        for _, row in df_test.iterrows():
            forecasts = {'IFS': row['IFS'], 'ICON': row['ICON'], 'GFS': row['GFS']}
            env = {'lead_time': row['lead_time']}
            u = self.estimate(forecasts, env)
            uncertainties.append(u['uncertainty_value'])

        uncertainties = np.array(uncertainties)

        # Bin by uncertainty quantiles
        q_bins = np.quantile(uncertainties, [0, 0.33, 0.66, 1.0])
        labels = ["Low Uncertainty", "Medium Uncertainty", "High Uncertainty"]

        results = {}
        for i in range(3):
            mask = (uncertainties >= q_bins[i]) & (uncertainties <= q_bins[i+1])
            results[labels[i]] = {
                'mean_uncertainty_score': float(np.mean(uncertainties[mask])),
                'actual_mae': float(np.mean(actual_errors[mask])),
                'count': int(np.sum(mask))
            }

        corr = float(np.corrcoef(uncertainties, actual_errors)[0,1])
        results['correlation'] = corr

        self.logger.info(f"Uncertainty vs Error Correlation: {corr:.3f}")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "uncertainty_validation.json", 'w') as f:
            json.dump(results, f, indent=2)

        return results
