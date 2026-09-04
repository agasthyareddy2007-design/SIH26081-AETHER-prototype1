"""
Phase 5 — Static Blending
Optimizes fixed weights for multi-model ensemble
"""

import numpy as np
from scipy.optimize import minimize
from sklearn.metrics import mean_squared_error
import logging

class StaticBlender:
    """Optimizes static weights for multi-model blending"""

    def __init__(self):
        self.logger = logging.getLogger("aether.blending.static")
        self.weights = None

    def optimize_weights(self, df, sources=['IFS', 'ICON', 'GFS']):
        """
        Optimizes static weights to minimize RMSE.

        Args:
            df: DataFrame with columns for each source and 'reference_value'
            sources: List of model source column names

        Returns:
            dict: Optimized weights
        """
        y_true = df['reference_value'].values
        forecasts = df[sources].values

        def objective(weights):
            """RMSE objective function"""
            blend = forecasts @ weights
            return np.sqrt(mean_squared_error(y_true, blend))

        # Constraints: weights sum to 1, all non-negative
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
        bounds = [(0.0, 1.0) for _ in sources]

        # Initial guess: equal weights
        w0 = np.ones(len(sources)) / len(sources)

        result = minimize(
            objective,
            w0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if result.success:
            self.weights = dict(zip(sources, result.x))
            self.logger.info(f"Optimized weights: {self.weights}")
            self.logger.info(f"Static blend RMSE: {result.fun:.4f}")
        else:
            self.logger.error(f"Optimization failed: {result.message}")
            self.weights = dict(zip(sources, w0))

        return self.weights

    def predict(self, df, sources=['IFS', 'ICON', 'GFS']):
        """Apply static weights to generate blended forecast"""
        if self.weights is None:
            raise ValueError("Weights not optimized. Call optimize_weights first.")

        weights_array = np.array([self.weights[s] for s in sources])
        return df[sources].values @ weights_array
