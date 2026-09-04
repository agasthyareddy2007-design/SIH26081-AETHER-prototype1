"""
Phase 13 — AETHER Model Configuration
Configures local LLM for weather intelligence assistant
"""

import logging
from pathlib import Path
import yaml

class AETHERModelConfig:
    """
    Configures AETHER conversational assistant.

    For V1: Uses system prompting + structured tool calls rather than fine-tuning.
    """

    def __init__(self):
        self.logger = logging.getLogger("aether.model_config")

    def get_system_prompt(self) -> str:
        """System prompt for AETHER assistant"""
        return """You are AETHER, an AI weather intelligence assistant.

Your purpose is to help users understand weather forecasts by:
1. Providing blended forecasts from multiple models (IFS, ICON, GFS)
2. Explaining model disagreement and uncertainty
3. Answering questions about forecast reliability
4. Explaining why particular model weights were chosen

Key principles:
- NEVER fabricate weather values or forecasts
- Always use the forecasting engine tools to get real data
- If data is unavailable, say so clearly
- Explain uncertainty honestly
- Focus on the Hyderabad region (current V1 scope)
- Forecast horizon: up to 24 hours

Available tools:
- predict_forecast: Get blended forecast for a location/time
- get_model_comparison: Compare model performance
- get_forecast_explanation: Explain why a forecast was generated
- get_uncertainty: Get confidence/uncertainty estimates

When uncertain, ask clarifying questions rather than guessing."""

    def get_tool_schemas(self) -> list:
        """Tool schemas for function calling"""
        return [
            {
                "name": "predict_forecast",
                "description": "Generate a blended weather forecast for a specific location and time",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_time_hours": {
                            "type": "integer",
                            "description": "Forecast lead time in hours (6, 12, or 24)",
                            "enum": [6, 12, 24]
                        },
                        "latitude": {
                            "type": "number",
                            "description": "Latitude (Hyderabad region: 16.8-17.8)"
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Longitude (Hyderabad region: 78.0-79.0)"
                        }
                    },
                    "required": ["lead_time_hours"]
                }
            },
            {
                "name": "get_forecast_explanation",
                "description": "Get explanation for why a forecast was generated",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_time_hours": {"type": "integer"}
                    },
                    "required": ["lead_time_hours"]
                }
            },
            {
                "name": "get_model_comparison",
                "description": "Get comparison of model performance",
                "parameters": {"type": "object", "properties": {}}
            }
        ]

    def save_config(self, output_path: Path):
        """Save AETHER configuration"""
        config = {
            'model_type': 'system_prompt_based',
            'system_prompt': self.get_system_prompt(),
            'tools': self.get_tool_schemas(),
            'parameters': {
                'temperature': 0.7,
                'max_tokens': 512,
                'top_p': 0.9
            }
        }

        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        self.logger.info(f"AETHER configuration saved to {output_path}")
        return config
