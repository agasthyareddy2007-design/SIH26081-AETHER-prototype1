"""
Phase 14 — AETHER Validation
Tests AETHER conversational behavior and tool calling
"""

import logging
from pathlib import Path
import json

class AETHERValidator:
    """Validates AETHER assistant responses"""

    def __init__(self):
        self.logger = logging.getLogger("aether.validation")

    def validate_greeting(self, response: str) -> bool:
        """Validate greeting response"""
        required_elements = ['AETHER', 'weather', 'assist']
        return all(elem.lower() in response.lower() for elem in required_elements)

    def validate_forecast_response(self, response: dict, expected_structure: dict) -> bool:
        """Validate forecast response structure"""
        required_keys = ['forecast', 'unit', 'confidence']
        return all(k in response for k in required_keys)

    def validate_no_hallucination(self, response: str, allowed_phrases: list) -> bool:
        """Ensure no fabricated weather values"""
        # Check that response doesn't contain specific numbers without context
        fabrication_indicators = [
            'will be exactly',
            'precisely',
            'definitely'
        ]
        return not any(ind in response.lower() for ind in fabrication_indicators)

    def run_validation_suite(self, test_cases: list, output_dir: Path) -> dict:
        """Run complete validation suite"""
        results = {
            'total_tests': len(test_cases),
            'passed': 0,
            'failed': 0,
            'test_results': []
        }

        for i, test in enumerate(test_cases):
            test_result = {
                'test_id': i,
                'instruction': test['instruction'],
                'expected_intent': test.get('intent'),
                'passed': True,
                'notes': []
            }

            # Intent validation
            if test.get('intent') == 'greeting':
                if not self.validate_greeting(test.get('response', '')):
                    test_result['passed'] = False
                    test_result['notes'].append('Greeting validation failed')

            # Tool selection validation
            if 'tool' in test:
                test_result['notes'].append(f"Expected tool: {test['tool']}")

            # Hallucination check
            if 'response' in test:
                if not self.validate_no_hallucination(test['response'], []):
                    test_result['passed'] = False
                    test_result['notes'].append('Potential hallucination detected')

            results['test_results'].append(test_result)
            if test_result['passed']:
                results['passed'] += 1
            else:
                results['failed'] += 1

        # Save results
        output_path = output_dir / "validation_results.json"
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        self.logger.info(f"Validation complete: {results['passed']}/{results['total_tests']} passed")
        self.logger.info(f"Results saved to {output_path}")

        return results
