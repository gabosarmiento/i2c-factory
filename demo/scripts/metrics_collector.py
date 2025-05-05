# demo/scripts/metrics_collector.py
import json
from pathlib import Path

class DemoMetricsCollector:
    def __init__(self):
        self.metrics = {
            'generation_times': [],
            'modification_times': [],
            'api_calls': 0,
            'tokens_used': 0,
            'errors_recovered': 0
        }
    
    def record_operation(self, operation_type, duration, tokens):
        if operation_type == 'generation':
            self.metrics['generation_times'].append(duration)
        elif operation_type == 'modification':
            self.metrics['modification_times'].append(duration)

        self.metrics['tokens_used'] += tokens
        self.metrics['api_calls'] += 1
        
    def record_error_recovery(self):
        self.metrics['errors_recovered'] += 1
    
    def save_metrics(self):
        metrics_path = Path(__file__).parent.parent / "demo" / "metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)