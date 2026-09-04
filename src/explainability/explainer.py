"""
Phase 10 — Explainability
SHAP-based feature importance and weight explanations
"""

import shap
import numpy as np
import logging
from pathlib import Path
import json

class Explainer:
    def __init__(self):
        self.logger = logging.getLogger("aether.explainability")
        self.shap_explainer = None

    def build_explainer(self, xgboost_model, X_background):
        """Build SHAP TreeExplainer for XGBoost model"""
        self.logger.info("Building SHAP explainer...")
        self.shap_explainer = shap.TreeExplainer(xgboost_model.model)
        self.logger.info("SHAP explainer ready")

    def explain_instance(self, X_instance, feature_names: list) -> dict:
        """
        Generate SHAP explanation for a single prediction.

        Args:
            X_instance: Single row feature vector
            feature_names: List of feature names

        Returns:
            dict with feature contributions
        """
        if self.shap_explainer is None:
            raise ValueError("Explainer not built. Call build_explainer first.")

        shap_values = self.shap_explainer.shap_values(X_instance.reshape(1, -1))

        contributions = {}
        for i, name in enumerate(feature_names):
            contributions[name] = float(shap_values[0][i])

        # Sort by absolute contribution
        sorted_contrib = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)

        return {
            'contributions': contributions,
            'top_features': [{'feature': k, 'contribution': v} for k, v in sorted_contrib[:5]]
        }

    def global_feature_importance(self, df, xgboost_model, output_dir: Path) -> dict:
        """Calculate global feature importance across dataset"""
        self.logger.info("Calculating global feature importance...")

        X = xgboost_model.prepare_features(df)
        feature_names = xgboost_model.feature_cols

        # Use subsample for efficiency
        sample_size = min(500, len(X))
        X_sample = X.sample(n=sample_size, random_state=42)

        self.build_explainer(xgboost_model, X_sample)

        shap_values = self.shap_explainer.shap_values(X_sample)

        # Mean absolute SHAP values
        mean_abs_shap = np.abs(shap_values).mean(axis=0)

        importance = {}
        for i, name in enumerate(feature_names):
            importance[name] = float(mean_abs_shap[i])

        # Sort by importance
        sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

        result = {
            'feature_importance': importance,
            'ranked_features': [{'feature': k, 'importance': v} for k, v in sorted_importance]
        }

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "feature_importance.json", 'w') as f:
            json.dump(result, f, indent=2)

        self.logger.info("Feature importance saved")
        return result
