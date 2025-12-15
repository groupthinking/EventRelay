#!/usr/bin/env python3
"""
API Cost Tracker - Multi-Model Cost Monitoring
Direct cost tracking without orchestrator layers (Anti-Bloat Compliant)
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Cost per 1M tokens (as of 2025-10-27)
API_COSTS = {
    "gemini-2.0-flash-exp": {
        "input": 0.0,  # Free during preview
        "output": 0.0
    },
    "gpt-4-turbo": {
        "input": 10.00,
        "output": 30.00
    },
    "gpt-3.5-turbo": {
        "input": 0.50,
        "output": 1.50
    },
    "claude-3-5-sonnet": {
        "input": 3.00,
        "output": 15.00
    },
    "perplexity-sonar": {
        "input": 1.00,
        "output": 1.00
    },
    "groq-llama3-70b": {
        "input": 0.59,
        "output": 0.79
    },
    "youtube-transcript-api": {
        "per_request": 0.0  # Free
    }
}

# Rate limits (requests per minute)
RATE_LIMITS = {
    "gemini-2.0-flash-exp": 60,
    "youtube-data-api": 10000,  # Per day
    "youtube-transcript-api": None,  # No official limit
    "gpt-4-turbo": 10000,  # Per minute
    "claude-3-5-sonnet": 50,
    "perplexity-sonar": 20,
    "groq-llama3-70b": 30
}

class CostTracker:
    """Simple cost tracking without orchestration layers"""

    def __init__(self, data_file: str = "api_usage_data.json"):
        self.data_file = Path(data_file)
        self.current_session = {
            "session_id": datetime.now().isoformat(),
            "start_time": time.time(),
            "api_calls": [],
            "total_cost": 0.0
        }
        self.load_historical_data()

    def load_historical_data(self):
        """Load historical usage data"""
        if self.data_file.exists():
            with open(self.data_file, 'r') as f:
                self.historical_data = json.load(f)
        else:
            self.historical_data = {"sessions": []}

    def track_api_call(
        self,
        api_name: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        request_latency: float = 0.0,
        status: str = "success"
    ) -> Dict:
        """Track a single API call"""

        # Calculate cost
        cost = 0.0
        if model in API_COSTS:
            model_costs = API_COSTS[model]
            if "input" in model_costs:
                cost = (input_tokens / 1_000_000) * model_costs["input"]
                cost += (output_tokens / 1_000_000) * model_costs["output"]
            elif "per_request" in model_costs:
                cost = model_costs["per_request"]

        # Record call
        call_data = {
            "timestamp": datetime.now().isoformat(),
            "api_name": api_name,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost,
            "latency_seconds": request_latency,
            "status": status
        }

        self.current_session["api_calls"].append(call_data)
        self.current_session["total_cost"] += cost

        return call_data

    def get_session_summary(self) -> Dict:
        """Get current session summary"""
        total_calls = len(self.current_session["api_calls"])
        successful_calls = sum(1 for call in self.current_session["api_calls"]
                             if call["status"] == "success")

        return {
            "session_id": self.current_session["session_id"],
            "duration_seconds": time.time() - self.current_session["start_time"],
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": total_calls - successful_calls,
            "total_cost_usd": self.current_session["total_cost"],
            "avg_latency": sum(call["latency_seconds"]
                              for call in self.current_session["api_calls"]) / total_calls if total_calls > 0 else 0
        }

    def get_cost_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by model"""
        breakdown = {}
        for call in self.current_session["api_calls"]:
            model = call["model"]
            cost = call["cost_usd"]
            breakdown[model] = breakdown.get(model, 0.0) + cost
        return breakdown

    def check_rate_limit(self, model: str, calls_last_minute: int) -> Dict:
        """Check if rate limit exceeded"""
        limit = RATE_LIMITS.get(model)
        if limit is None:
            return {"status": "ok", "limit": None}

        if calls_last_minute >= limit:
            return {
                "status": "exceeded",
                "limit": limit,
                "current": calls_last_minute,
                "wait_seconds": 60
            }

        return {
            "status": "ok",
            "limit": limit,
            "current": calls_last_minute,
            "remaining": limit - calls_last_minute
        }

    def save_session(self):
        """Save current session to historical data"""
        self.historical_data["sessions"].append(self.current_session)
        with open(self.data_file, 'w') as f:
            json.dump(self.historical_data, f, indent=2)

    def export_report(self, output_file: str = "cost_report.json"):
        """Export detailed cost report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "current_session": self.get_session_summary(),
            "cost_breakdown": self.get_cost_breakdown(),
            "detailed_calls": self.current_session["api_calls"],
            "rate_limits": RATE_LIMITS,
            "api_costs": API_COSTS
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        return report

# Example usage
if __name__ == "__main__":
    tracker = CostTracker()

    # Simulate API calls from our live integration test
    print("🔍 API Cost Tracking Example\n")

    # YouTube transcript extraction
    tracker.track_api_call(
        api_name="YouTube Transcript API",
        model="youtube-transcript-api",
        request_latency=1.56,
        status="success"
    )

    # Gemini 2.0 Flash analysis
    tracker.track_api_call(
        api_name="Gemini 2.0 Flash",
        model="gemini-2.0-flash-exp",
        input_tokens=750,  # ~3000 chars
        output_tokens=328,  # ~1312 chars
        request_latency=2.71,
        status="success"
    )

    # Print summary
    summary = tracker.get_session_summary()
    print("📊 Session Summary:")
    print(f"   - Total calls: {summary['total_calls']}")
    print(f"   - Successful: {summary['successful_calls']}")
    print(f"   - Total cost: ${summary['total_cost_usd']:.4f}")
    print(f"   - Avg latency: {summary['avg_latency']:.2f}s")

    print("\n💰 Cost Breakdown:")
    for model, cost in tracker.get_cost_breakdown().items():
        print(f"   - {model}: ${cost:.4f}")

    # Save session
    tracker.save_session()

    # Export report
    report = tracker.export_report()
    print(f"\n✅ Cost report exported to: cost_report.json")
