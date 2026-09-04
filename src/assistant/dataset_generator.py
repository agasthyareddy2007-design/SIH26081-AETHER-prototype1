"""
Phase 12 — AETHER Dataset Generation
Creates instruction tuning examples for conversational weather intelligence
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import random

class AETHERDatasetGenerator:
    """Generates training data for AETHER conversational assistant"""

    def __init__(self, output_dir: Path):
        self.logger = logging.getLogger("aether.dataset")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_greeting_examples(self) -> list:
        """Examples for greeting intent"""
        return [
            {
                "instruction": "Hello",
                "intent": "greeting",
                "response": "Hello! I'm AETHER, your AI weather intelligence assistant. I can help you understand forecasts, model disagreement, and uncertainty. How can I assist you today?"
            },
            {
                "instruction": "Hi AETHER",
                "intent": "greeting",
                "response": "Hi! I'm here to help with weather forecasts and explain how different models compare. What would you like to know?"
            },
            {
                "instruction": "Hey",
                "intent": "greeting",
                "response": "Hey! AETHER here. Ready to discuss weather forecasts, uncertainty, or model performance. What's on your mind?"
            }
        ]

    def generate_forecast_examples(self) -> list:
        """Examples for forecast requests"""
        return [
            {
                "instruction": "What will tomorrow's temperature be?",
                "intent": "forecast_temperature",
                "tool": "predict_forecast",
                "parameters": {"lead_time_hours": 24, "variable": "temperature"},
                "response_template": "Based on my analysis, tomorrow's temperature forecast is {forecast}°C. I'm giving this {confidence} confidence because the model disagreement is {disagreement}°C."
            },
            {
                "instruction": "Will it rain today?",
                "intent": "forecast_precipitation",
                "tool": "predict_forecast",
                "parameters": {"lead_time_hours": 6, "variable": "precipitation"},
                "response_template": "I can analyze precipitation forecasts. Let me check the models for you."
            },
            {
                "instruction": "Temperature forecast for the next 12 hours",
                "intent": "forecast_temperature",
                "tool": "predict_forecast",
                "parameters": {"lead_time_hours": 12, "variable": "temperature"},
                "response_template": "For the next 12 hours, the blended forecast shows {forecast}°C with {confidence} confidence."
            }
        ]

    def generate_model_comparison_examples(self) -> list:
        """Examples for model comparison queries"""
        return [
            {
                "instruction": "Which model is most accurate?",
                "intent": "model_comparison",
                "tool": "get_model_comparison",
                "response_template": "Based on test set evaluation, the XGBoost dynamic blending model performs best with 26.88% error reduction compared to simple averaging. Among individual models, IFS tends to be most reliable."
            },
            {
                "instruction": "How do IFS and ICON compare?",
                "intent": "model_comparison",
                "tool": "get_model_comparison",
                "response_template": "IFS (ECMWF Integrated Forecast System) and ICON (AI-based Forecast System) have different strengths. IFS typically has lower error (RMSE 1.78) compared to ICON (RMSE 2.04) on our test set. The dynamic blender learns when each is more reliable."
            },
            {
                "instruction": "Why does the system use multiple models?",
                "intent": "explain_blending",
                "response_template": "I use multiple models (IFS, ICON, GFS) because different models excel in different conditions. By analyzing their agreement and past performance, I can dynamically weight them to create a more reliable forecast than any single model."
            }
        ]

    def generate_uncertainty_examples(self) -> list:
        """Examples for uncertainty/confidence queries"""
        return [
            {
                "instruction": "How confident are you in this forecast?",
                "intent": "explain_confidence",
                "tool": "get_uncertainty",
                "response_template": "My confidence is {confidence}. This is based on model disagreement of {disagreement}°C and the forecast lead time. Higher disagreement typically means higher uncertainty."
            },
            {
                "instruction": "Why is the forecast uncertain?",
                "intent": "explain_uncertainty",
                "tool": "get_forecast_explanation",
                "response_template": "The forecast is uncertain due to {key_factors}. Model disagreement is {disagreement}°C, which indicates the models see different outcomes. This often happens with longer lead times or complex weather patterns."
            },
            {
                "instruction": "Can I trust this forecast?",
                "intent": "explain_confidence",
                "tool": "get_uncertainty",
                "response_template": "The reliability depends on the confidence level. This forecast has {confidence} confidence. Lower confidence means you should check back closer to the time, as conditions may evolve."
            }
        ]

    def generate_explanation_examples(self) -> list:
        """Examples for forecast explanations"""
        return [
            {
                "instruction": "Why did you choose these model weights?",
                "intent": "explain_weights",
                "tool": "get_forecast_explanation",
                "response_template": "The model weights are determined by past performance in similar conditions. Currently, I'm weighting IFS at {ifs_weight}, ICON at {icon_weight}, and GFS at {gfs_weight} based on lead time, time of day, and model agreement patterns."
            },
            {
                "instruction": "What factors influenced the forecast?",
                "intent": "explain_forecast",
                "tool": "get_forecast_explanation",
                "response_template": "The key factors are: {factors}. The most important features are time of day (diurnal cycle) and lead time, followed by the base model forecasts and their disagreement."
            }
        ]

    def generate_unsupported_examples(self) -> list:
        """Examples for out-of-scope queries"""
        return [
            {
                "instruction": "What's the weather like in New York?",
                "intent": "out_of_scope_location",
                "response": "I'm currently focused on the Hyderabad region. I don't have forecast data for New York in this V1 system."
            },
            {
                "instruction": "Will there be a cyclone next month?",
                "intent": "out_of_scope_timeframe",
                "response": "I can only provide forecasts up to 24 hours ahead. Long-range extreme weather prediction is beyond my current capabilities."
            },
            {
                "instruction": "Book me a flight",
                "intent": "out_of_scope_task",
                "response": "I'm a weather forecasting assistant. I can help you understand weather conditions, but I can't book flights or perform other tasks."
            }
        ]

    def generate_all(self) -> dict:
        """Generate complete JSONL dataset"""
        all_examples = (
            self.generate_greeting_examples() +
            self.generate_forecast_examples() +
            self.generate_model_comparison_examples() +
            self.generate_uncertainty_examples() +
            self.generate_explanation_examples() +
            self.generate_unsupported_examples()
        )

        # Shuffle for training diversity
        random.shuffle(all_examples)

        # Split into train/val
        split_idx = int(len(all_examples) * 0.9)
        train_examples = all_examples[:split_idx]
        val_examples = all_examples[split_idx:]

        # Save as JSONL
        train_path = self.output_dir / "aether_train.jsonl"
        val_path = self.output_dir / "aether_val.jsonl"

        with open(train_path, 'w') as f:
            for ex in train_examples:
                f.write(json.dumps(ex) + '\n')

        with open(val_path, 'w') as f:
            for ex in val_examples:
                f.write(json.dumps(ex) + '\n')

        self.logger.info(f"Generated {len(train_examples)} training examples")
        self.logger.info(f"Generated {len(val_examples)} validation examples")
        self.logger.info(f"Saved to {train_path} and {val_path}")

        return {
            'train_path': str(train_path),
            'val_path': str(val_path),
            'train_count': len(train_examples),
            'val_count': len(val_examples)
        }
