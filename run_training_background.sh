#!/bin/bash
# AETHER Training — Background Execution Script
# Launches training pipeline in persistent tmux session

set -e

PROJECT_DIR="/home/agasthya/ai models"
VENV_DIR="$PROJECT_DIR/.venv"
LOG_DIR="$PROJECT_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/training_${TIMESTAMP}.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

echo "============================================================"
echo "AETHER — BACKGROUND TRAINING LAUNCHER"
echo "SIH26081 — Hybrid AI/NWP Multi-Model Forecast Blending"
echo "============================================================"
echo ""
echo "Project: $PROJECT_DIR"
echo "Log file: $LOG_FILE"
echo ""

# Check if tmux session already exists
if tmux has-session -t aether_train 2>/dev/null; then
    echo "ERROR: tmux session 'aether_train' already exists."
    echo ""
    echo "To attach to existing session:"
    echo "  tmux attach -t aether_train"
    echo ""
    echo "To kill existing session and start fresh:"
    echo "  tmux kill-session -t aether_train"
    echo "  bash run_training_background.sh"
    echo ""
    exit 1
fi

# Create tmux session and run training
echo "Creating tmux session 'aether_train'..."
echo "Training will run in background and log to: $LOG_FILE"
echo ""

tmux new-session -d -s aether_train "cd '$PROJECT_DIR' && source '$VENV_DIR/bin/activate' && python train_pipeline.py 2>&1 | tee '$LOG_FILE'"

echo "✓ Training session started in background"
echo ""
echo "============================================================"
echo "MONITORING COMMANDS"
echo "============================================================"
echo ""
echo "Attach to training session (Ctrl+B then D to detach):"
echo "  tmux attach -t aether_train"
echo ""
echo "Monitor log file in real-time:"
echo "  tail -f $LOG_FILE"
echo ""
echo "Check if training is still running:"
echo "  tmux list-sessions | grep aether_train"
echo ""
echo "Stop training:"
echo "  tmux kill-session -t aether_train"
echo ""
echo "============================================================"
echo "IMPORTANT: Training must complete before proceeding to"
echo "           Phase 8 (Evaluation)."
echo ""
echo "The training will:"
echo "  1. Generate 30 days of multi-model forecast data"
echo "  2. Engineer features (disagreement, temporal, lead time)"
echo "  3. Create chronological train/val/test splits"
echo "  4. Evaluate baselines (IFS/AIFS/GFS alone, simple average)"
echo "  5. Optimize static blend weights"
echo "  6. Run Optuna hyperparameter search (~25 trials)"
echo "  7. Train final XGBoost dynamic blending model"
echo ""
echo "Estimated time: 10-30 minutes (depending on GPU)"
echo "============================================================"
