#!/usr/bin/env python3
"""
AETHER Training Pipeline
Complete training workflow: Data → Features → Baselines → Blending → Optuna → Final Model
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import yaml
import pandas as pd
from tqdm import tqdm
import numpy as np

# Setup paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.orchestrator import DataOrchestrator
from src.features.engineer import FeatureEngineer
from src.baselines.evaluator import BaselineModels
from src.blending.static_blender import StaticBlender
from src.blending.dynamic_blender import DynamicBlender
from src.blending.optuna_optimizer import OptunaOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'logs' / f'training_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("aether.training")

def load_config():
    """Load all configuration files"""
    config_dir = PROJECT_ROOT / "config"

    with open(config_dir / "data_config.yaml") as f:
        data_config = yaml.safe_load(f)

    with open(config_dir / "model_config.yaml") as f:
        model_config = yaml.safe_load(f)

    with open(config_dir / "environment.yaml") as f:
        env_config = yaml.safe_load(f)

    return data_config, model_config, env_config

def generate_training_data(data_config, n_init_times=30):
    """
    Load pre-built training dataset from bulk fetcher.
    """
    logger.info("="*80)
    logger.info("PHASE 1-2: LOADING PRE-BUILT BULK DATA")
    logger.info("="*80)

    input_path = PROJECT_ROOT / "data" / "processed" / "training_aligned.csv"

    # Actually, the bulk script output already split them, but to keep the pipeline
    # flowing sequentially with feature engineering, we'll load the raw alignment and
    # let it re-split. Wait, the bulk script didn't save training_aligned.csv, only
    # training_features.csv, train.csv, val.csv, test.csv. We'll skip generate_training_data
    # and engineer_features, and just load train/val/test directly.
    pass

def engineer_features(df):
    """Apply feature engineering"""
    logger.info("="*80)
    logger.info("PHASE 3: FEATURE ENGINEERING")
    logger.info("="*80)

    engineer = FeatureEngineer()
    features_df = engineer.create_features(df)

    # Save feature-engineered data
    output_path = PROJECT_ROOT / "data" / "processed" / "training_features.csv"
    features_df.to_csv(output_path, index=False)
    logger.info(f"Feature-engineered data saved to: {output_path}")

    return features_df

def chronological_split(df, train_frac=0.7, val_frac=0.15, test_frac=0.15):
    """
    Chronological train/validation/test split.

    CRITICAL: No future data leakage. Split by initialization_time.
    """
    logger.info("Creating chronological train/validation/test split...")

    # Sort by initialization_time
    df = df.sort_values('initialization_time').reset_index(drop=True)

    n = len(df)
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))

    df_train = df.iloc[:train_end].copy()
    df_val = df.iloc[train_end:val_end].copy()
    df_test = df.iloc[val_end:].copy()

    logger.info(f"Train: {len(df_train)} samples ({100*train_frac:.0f}%)")
    logger.info(f"Validation: {len(df_val)} samples ({100*val_frac:.0f}%)")
    logger.info(f"Test: {len(df_test)} samples ({100*test_frac:.0f}%)")

    logger.info(f"Train period: {df_train['initialization_time'].min()} to {df_train['initialization_time'].max()}")
    logger.info(f"Val period: {df_val['initialization_time'].min()} to {df_val['initialization_time'].max()}")
    logger.info(f"Test period: {df_test['initialization_time'].min()} to {df_test['initialization_time'].max()}")

    return df_train, df_val, df_test

def evaluate_baselines(df_train, df_val, df_test):
    """Evaluate baseline models"""
    logger.info("="*80)
    logger.info("PHASE 4: BASELINES")
    logger.info("="*80)

    baseline = BaselineModels()

    train_metrics = baseline.evaluate_baselines(df_train)
    val_metrics = baseline.evaluate_baselines(df_val)
    test_metrics = baseline.evaluate_baselines(df_test)

    logger.info("\n--- Training Set ---")
    for model, metrics in train_metrics.items():
        logger.info(f"{model}: MAE={metrics['mae']:.4f}, RMSE={metrics['rmse']:.4f}")

    logger.info("\n--- Validation Set ---")
    for model, metrics in val_metrics.items():
        logger.info(f"{model}: MAE={metrics['mae']:.4f}, RMSE={metrics['rmse']:.4f}")

    logger.info("\n--- Test Set (BASELINE REFERENCE ONLY) ---")
    for model, metrics in test_metrics.items():
        logger.info(f"{model}: MAE={metrics['mae']:.4f}, RMSE={metrics['rmse']:.4f}")

    return train_metrics, val_metrics, test_metrics

def train_static_blend(df_train, df_val):
    """Train static weighted blend"""
    logger.info("="*80)
    logger.info("PHASE 5: STATIC BLENDING")
    logger.info("="*80)

    blender = StaticBlender()
    weights = blender.optimize_weights(df_train)

    # Evaluate on validation
    y_true_val = df_val['reference_value']
    y_pred_val = blender.predict(df_val)

    from sklearn.metrics import mean_absolute_error, mean_squared_error
    val_mae = mean_absolute_error(y_true_val, y_pred_val)
    val_rmse = np.sqrt(mean_squared_error(y_true_val, y_pred_val))

    logger.info(f"Static blend validation MAE: {val_mae:.4f}, RMSE: {val_rmse:.4f}")

    # Save weights safely
    native_weights = {k: float(v) for k, v in weights.items()}
    output_path = PROJECT_ROOT / "models" / "blender" / "static_weights.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        yaml.dump(native_weights, f)

    logger.info(f"Static weights saved to: {output_path}")

    return blender, weights

def run_optuna_optimization(df_train, df_val, model_config, device='cuda'):
    """Run Optuna hyperparameter optimization"""
    logger.info("="*80)
    logger.info("PHASE 7: OPTUNA HYPERPARAMETER OPTIMIZATION")
    logger.info("="*80)

    optimizer = OptunaOptimizer(config_path=PROJECT_ROOT / "config" / "model_config.yaml")

    # Determine feature columns
    forecast_cols = ['IFS', 'ICON', 'GFS']
    disagreement_cols = ['disagreement_std', 'disagreement_range', 'diff_ifs_icon', 'diff_ifs_gfs']
    temporal_cols = ['hour_sin', 'hour_cos', 'doy_sin', 'doy_cos']
    lead_cols = ['lead_time', 'lead_time_sqrt']

    feature_cols = [c for c in (forecast_cols + disagreement_cols + temporal_cols + lead_cols) if c in df_train.columns]

    logger.info(f"Features: {feature_cols}")

    # Run optimization
    best_params, best_value = optimizer.optimize(df_train, df_val, feature_cols, device=device)

    # Save results
    optimizer.save_results(PROJECT_ROOT / "experiments")

    return best_params, best_value, feature_cols

def train_final_model(df_train, df_val, best_params, feature_cols, device='cuda'):
    """Train final XGBoost model with best hyperparameters"""
    logger.info("="*80)
    logger.info("PHASE 6: TRAINING FINAL XGBOOST MODEL")
    logger.info("="*80)

    logger.info("Training fresh XGBoost model with Optuna-optimized hyperparameters...")

    # Create config with best params
    config = {'mlp': {**best_params, 'device': device}}

    blender = DynamicBlender(config)
    blender.train(df_train, df_val, params=config['mlp'])

    # Save model
    model_path = PROJECT_ROOT / "models" / "blender" / "mlp_gating_model"
    blender.save(model_path)

    logger.info(f"Final model saved to: {model_path}")

    return blender

def test_dynamic_weights_smoke_test(blender, df_test):
    """Smoke test to verify dynamic blending explicit weights calculations."""
    logger.info("="*80)
    logger.info("VALIDATION SMOKE TEST: EXPLICIT DYNAMIC WEIGHTS")
    logger.info("="*80)

    # Take a few samples
    sample = df_test.head(5).copy()

    weights_dict = blender.predict_weights(sample)
    predictions = blender.predict(sample)

    for i in range(len(sample)):
        logger.info(f"--- Sample {i+1} ---")
        ifs, icon, gfs = sample['IFS'].iloc[i], sample['ICON'].iloc[i], sample['GFS'].iloc[i]
        ref = sample['reference_value'].iloc[i]

        logger.info(f"Inputs: IFS={ifs:.4f}, ICON={icon:.4f}, GFS={gfs:.4f} | Target (ERA5-Land)={ref:.4f}")
        
        w_ifs, w_icon, w_gfs = weights_dict['IFS'][i], weights_dict['ICON'][i], weights_dict['GFS'][i]
        logger.info(f"Explicit Weights: w_IFS={w_ifs:.4f}, w_ICON={w_icon:.4f}, w_GFS={w_gfs:.4f}")
        logger.info(f"Sum of Weights = {(w_ifs + w_icon + w_gfs):.6f}")

        explicit_sum = w_ifs * ifs + w_icon * icon + w_gfs * gfs
        logger.info(f"Final Blended Forecast = {predictions[i]:.4f} (Weighted Sum = {explicit_sum:.4f})")
        logger.info("Match?" + (" YES" if np.isclose(predictions[i], explicit_sum, atol=1e-4) else " NO"))

    return sample

def main():
    """Main training pipeline"""
    logger.info("="*80)
    logger.info("AETHER TRAINING PIPELINE")
    logger.info("SIH26081 — Hybrid AI/NWP Multi-Model Forecast Blending")
    logger.info("="*80)

    # Load configuration
    data_config, model_config, env_config = load_config()

    device = env_config.get('gpu', {}).get('device', 'cuda')
    logger.info(f"Using device: {device}")

    # Load pre-built chronological splits
    df_train = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "train.csv")
    df_val = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "val.csv")
    df_test = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "test.csv")

    logger.info(f"Loaded Train: {len(df_train)} rows")
    logger.info(f"Loaded Val: {len(df_val)} rows")
    logger.info(f"Loaded Test: {len(df_test)} rows")

    # Evaluate baselines
    baseline_metrics = evaluate_baselines(df_train, df_val, df_test)

    # Train static blend
    static_blender, static_weights = train_static_blend(df_train, df_val)

    # Train final PyTorch MLPGatingNet model directly
    logger.info("="*80)
    logger.info("PHASE 6: TRAINING FINAL PYTORCH MLPGATINGNET MODEL")
    logger.info("="*80)

    # We use a purely PyTorch Softmax Gating Network Architecture
    # Bypassing XGBoost Optuna optimization to enforce explicit differentiable weighting
    config = {'epochs': 150}
    final_blender = DynamicBlender(config)
    final_blender.train(df_train, df_val)

    # Save model
    model_path = PROJECT_ROOT / "models" / "blender" / "mlp_gating_model"
    final_blender.save(model_path)

    # Smoke Test
    test_dynamic_weights_smoke_test(final_blender, df_test)

    # Final Test Set Evaluation
    logger.info("="*80)
    logger.info("PHASE 8: FINAL TEST EVALUATION")
    logger.info("="*80)

    # Calculate actual predictions
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    y_true_test = df_test['reference_value']

    pred_dynamic = final_blender.predict(df_test)
    test_rmse_dynamic = np.sqrt(mean_squared_error(y_true_test, pred_dynamic))
    test_mae_dynamic = mean_absolute_error(y_true_test, pred_dynamic)

    # Log individual models
    for cand in ['IFS', 'ICON', 'GFS']:
        rmse = np.sqrt(mean_squared_error(y_true_test, df_test[cand]))
        logger.info(f"{cand} Test RMSE: {rmse:.4f}")

    # Simple average
    pred_avg = df_test[['IFS', 'ICON', 'GFS']].mean(axis=1)
    rmse_avg = np.sqrt(mean_squared_error(y_true_test, pred_avg))
    logger.info(f"Simple Average Test RMSE: {rmse_avg:.4f}")

    # Final Blender
    logger.info(f"Dynamic Blend Test RMSE: {test_rmse_dynamic:.4f} (MAE: {test_mae_dynamic:.4f})")

    improvement = (rmse_avg - test_rmse_dynamic) / rmse_avg * 100
    logger.info(f"Dynamic Blend Improvement vs Average: {improvement:.2f}%")

    logger.info("="*80)
    logger.info("TRAINING PIPELINE COMPLETE")
    logger.info("="*80)
    logger.info(f"Final Test RMSE: {test_rmse_dynamic:.4f}")
    logger.info(f"Model saved to: models/blender/mlp_gating_model.pth")
    logger.info("="*80)

if __name__ == "__main__":
    main()
