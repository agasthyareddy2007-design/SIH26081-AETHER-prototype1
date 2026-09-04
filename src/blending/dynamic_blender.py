"""
Phase 6 / 10 — Dynamic Blending (Selected Architecture)
Machine learning-based adaptive model weighting via PyTorch MLP Gating.
Explicitly maps causal features to Softmax convex combination weights.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging
from pathlib import Path
import torch
import torch.nn as nn
import torch.optim as optim
import json
from tqdm import tqdm

class MLPGatingNet(nn.Module):
    def __init__(self, in_features):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, 16),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(16, 3)
        )
    def forward(self, features, candidates):
        logits = self.net(features)
        weights = torch.softmax(logits, dim=1)
        return torch.sum(weights * candidates, dim=1), weights

class DynamicBlender:
    """
    PyTorch MLP-based dynamic blending model.
    Learns explicitly to output normalized weights mapping directly to expected
    candidate reliability via Softmax formulation, optimized globally for final RMSE.
    """

    def __init__(self, config=None):
        self.logger = logging.getLogger("aether.blending.dynamic")
        self.config = config or {}

        self.model = None
        self.feature_means = None
        self.feature_stds = None
        self.feature_cols = None
        self.candidates = ['IFS', 'ICON', 'GFS']

    def prepare_features(self, df):
        """Extract feature columns"""
        # Features validated in ablation study as non-leaky
        temporal_cols = ['hour_sin', 'hour_cos', 'doy_sin', 'doy_cos', 'lead_time', 'lead_time_sqrt']
        loc_cols = ['latitude', 'longitude']
        forecast_cols = self.candidates

        self.feature_cols = [c for c in (forecast_cols + temporal_cols + loc_cols) if c in df.columns]
        return df[self.feature_cols].values

    def train(self, df_train, df_val=None, params=None):
        """Train the MLP Gating Model using concatenated train and val sets."""
        if df_val is not None:
            df = pd.concat([df_train, df_val], ignore_index=True)
        else:
            df = df_train

        X = self.prepare_features(df)
        C = df[self.candidates].values
        y = df['reference_value'].values

        # Standardize features
        self.feature_means = X.mean(axis=0)
        self.feature_stds = X.std(axis=0) + 1e-8

        X_norm = (X - self.feature_means) / self.feature_stds

        t_X = torch.FloatTensor(X_norm.copy())
        t_C = torch.FloatTensor(C.copy())
        t_y = torch.FloatTensor(y.copy())

        self.model = MLPGatingNet(in_features=X.shape[1])
        opt = optim.Adam(self.model.parameters(), lr=0.005, weight_decay=1e-2)
        loss_fn = nn.MSELoss()

        epochs = self.config.get('epochs', 800)
        self.logger.info(f"Training PyTorch MLP Gating for {epochs} epochs...")

        for epoch in tqdm(range(epochs), desc="Training MLP Gating Network on RTX 5080"):
            self.model.train()
            opt.zero_grad()
            pred, _ = self.model(t_X, t_C)
            loss = loss_fn(pred, t_y)
            loss.backward()
            opt.step()

        # Measure Training blended score
        self.model.eval()
        with torch.no_grad():
            final_pred, _ = self.model(t_X, t_C)
            train_rmse = np.sqrt(mean_squared_error(y, final_pred.numpy()))

        self.logger.info(f"Training Complete. Blended RMSE on train/val: {train_rmse:.4f}")

    def _get_normalized_inputs(self, df):
        X = self.prepare_features(df)
        if self.feature_means is None or self.feature_stds is None:
            raise ValueError("Blender not trained.")
        X_norm = (X - self.feature_means) / self.feature_stds
        C = df[self.candidates].values
        return torch.FloatTensor(X_norm.copy()), torch.FloatTensor(C.copy())

    def predict_weights(self, df, return_logits=False):
        """Produce normalized array of weights: w_IFS, w_ICON, w_GFS

        Args:
            df: Input dataframe with features
            return_logits: If True, also return pre-softmax logits for explainability

        Returns:
            dict with weights, and optionally logits if return_logits=True
        """
        if self.model is None:
            raise ValueError("Model not trained.")

        t_X, t_C = self._get_normalized_inputs(df)

        self.model.eval()
        with torch.no_grad():
            logits = self.model.net(t_X)
            weights = torch.softmax(logits, dim=1)

        w_np = weights.numpy()
        result = {
            'IFS': w_np[:, 0],
            'ICON': w_np[:, 1],
            'GFS': w_np[:, 2]
        }

        if return_logits:
            logits_np = logits.numpy()
            result['logits'] = {
                'IFS': logits_np[:, 0],
                'ICON': logits_np[:, 1],
                'GFS': logits_np[:, 2]
            }

        return result

    def predict(self, df):
        """Generate final blended forecast."""
        if self.model is None:
            raise ValueError("Model not trained.")

        t_X, t_C = self._get_normalized_inputs(df)

        self.model.eval()
        with torch.no_grad():
            pred, _ = self.model(t_X, t_C)

        return pred.numpy()

    def save(self, path):
        """Save trained models and statistics"""
        if self.model is None:
            raise ValueError("Model not trained.")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        torch.save(self.model.state_dict(), str(path) + '.pth')
        np.save(str(path) + '_stats.npy', np.vstack([self.feature_means, self.feature_stds]))

        with open(str(path) + '_meta.json', 'w') as f:
            json.dump({
                'feature_cols': self.feature_cols,
                'candidates': self.candidates
            }, f)

        self.logger.info(f"Model saved to {path}.pth")

    def load(self, path):
        """Load trained models"""
        meta_path = str(path) + '_meta.json'
        stats_path = str(path) + '_stats.npy'
        pth_path = str(path) + '.pth'

        with open(meta_path, 'r') as f:
            meta = json.load(f)

        self.feature_cols = meta['feature_cols']
        self.candidates = meta['candidates']

        stats = np.load(stats_path)
        self.feature_means = stats[0]
        self.feature_stds = stats[1]

        self.model = MLPGatingNet(len(self.feature_cols))
        self.model.load_state_dict(torch.load(pth_path))
        self.model.eval()

        self.logger.info(f"Model loaded from {path}.pth")
