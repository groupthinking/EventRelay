"""High level API cost monitoring helpers for unit tests and developer tooling.

This module wraps the production monitor in ``youtube_extension.backend.services``
so that contributors can interact with a lightweight in-memory implementation
while still exercising the real pricing catalogue.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from statistics import mean
from typing import Any, Callable, Dict, Iterable, List, Optional

from youtube_extension.backend.services.api_cost_monitor import (
    APICostMonitor as _CoreMonitor,
    cost_monitor as _legacy_cost_monitor,
    track_api_call as _legacy_track_api_call,
    check_rate_limit_decorator,
)

APICostMonitor = _CoreMonitor
cost_monitor = _legacy_cost_monitor
track_api_call = _legacy_track_api_call


def _ensure_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _normalize_timestamp(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


@dataclass
class UsageRecord:
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())
    service: str = ""
    endpoint: str = ""
    model: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    characters: int = 0
    requests: int = 0
    quota_units: int = 0
    cost: Decimal = field(default_factory=lambda: Decimal("0"))
    request_id: Optional[str] = None

    def total_tokens(self) -> int:
        return (self.input_tokens or 0) + (self.output_tokens or 0)


@dataclass
class ApiEndpoint:
    service: str
    endpoint: str
    model: Optional[str] = None
    cost_per_token_input: Decimal = field(default_factory=lambda: Decimal("0"))
    cost_per_token_output: Decimal = field(default_factory=lambda: Decimal("0"))
    cost_per_character: Decimal = field(default_factory=lambda: Decimal("0"))
    cost_per_request: Decimal = field(default_factory=lambda: Decimal("0"))
    rate_limit: int = 0
    rate_limit_window: int = 60
    quota_cost: int = 0
    daily_quota: int = 0


@dataclass
class CostAlert:
    name: str
    threshold: Decimal = field(default_factory=lambda: Decimal("0"))
    timeframe: str = "day"
    alert_type: str = "email"
    service: Optional[str] = None
    recipients: Optional[List[str]] = None
    cooldown_minutes: int = 0
    custom_condition: Optional[Callable[[Decimal, Dict[str, Any]], bool]] = None
    last_triggered: Optional[datetime] = None

    def should_trigger(self, current_cost: Decimal) -> bool:
        if self.custom_condition:
            return self.custom_condition(current_cost, {})
        return current_cost >= self.threshold

    def trigger(self) -> None:
        self.last_triggered = datetime.utcnow()

    def is_in_cooldown(self) -> bool:
        if not self.last_triggered or self.cooldown_minutes <= 0:
            return False
        return datetime.utcnow() - self.last_triggered < timedelta(minutes=self.cooldown_minutes)

    def can_trigger(self) -> bool:
        return not self.is_in_cooldown()

    def evaluate_custom_condition(self, current_cost: Decimal, trend_data: Dict[str, Any]) -> bool:
        if not self.custom_condition:
            return False
        return self.custom_condition(current_cost, trend_data)


class CostTracker:
    def __init__(self) -> None:
        self._records: List[UsageRecord] = []

    def record_usage(self, record: UsageRecord) -> None:
        record.timestamp = _normalize_timestamp(record.timestamp)
        self._records.append(record)

    def record_bulk_usage(self, records: Iterable[UsageRecord]) -> None:
        for record in records:
            self.record_usage(record)

    def get_records(self, service: Optional[str] = None, timeframe: Optional[str] = None) -> List[UsageRecord]:
        records = self._records
        if service:
            service = service.lower()
            records = [r for r in records if (r.service or "").lower() == service]
        if timeframe:
            cutoff = self._timeframe_cutoff(timeframe)
            if cutoff:
                records = [r for r in records if r.timestamp >= cutoff]
        return list(records)

    def get_usage_summary(self, service: Optional[str] = None, timeframe: Optional[str] = None) -> Dict[str, Any]:
        records = self.get_records(service=service, timeframe=timeframe)
        total_cost = sum((r.cost for r in records), Decimal("0"))
        summary = {
            "total_records": len(records),
            "total_cost": total_cost,
            "average_cost": total_cost / len(records) if records else Decimal("0"),
            "service_breakdown": self._service_breakdown(records),
        }
        return summary

    @staticmethod
    def _timeframe_cutoff(timeframe: str) -> Optional[datetime]:
        timeframe = timeframe.lower()
        now = datetime.now()
        mapping = {
            "hour": timedelta(hours=1),
            "day": timedelta(days=1),
            "week": timedelta(weeks=1),
            "month": timedelta(days=30),
        }
        delta = mapping.get(timeframe)
        return now - delta if delta else None

    @staticmethod
    def _service_breakdown(records: Iterable[UsageRecord]) -> Dict[str, Decimal]:
        breakdown: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for record in records:
            breakdown[(record.service or "").lower()] += record.cost
        return dict(breakdown)


class ApiUsageMetrics:
    def calculate_token_metrics(self, records: Iterable[UsageRecord]) -> Dict[str, Any]:
        records = list(records)
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        total_tokens = total_input + total_output
        total_cost = sum((r.cost for r in records), Decimal("0"))
        average_tokens = total_tokens / len(records) if records else 0
        cost_per_token = Decimal("0") if total_tokens == 0 else (total_cost / Decimal(total_tokens)).quantize(
            Decimal("0.00001"), rounding=ROUND_HALF_UP
        )
        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "average_tokens_per_request": average_tokens,
            "cost_per_token": cost_per_token,
        }

    def calculate_rate_metrics(self, records: Iterable[UsageRecord]) -> Dict[str, Any]:
        records = sorted(records, key=lambda r: r.timestamp)
        if not records:
            return {"requests_per_hour": 0.0, "peak_hour_requests": 0, "average_request_interval": 0.0}

        start = records[0].timestamp
        end = records[-1].timestamp
        hours = max((end - start).total_seconds() / 3600, 1 / 60)
        requests_per_hour = len(records) / hours

        per_hour = Counter(r.timestamp.replace(minute=0, second=0, microsecond=0) for r in records)
        peak_hour_requests = max(per_hour.values()) if per_hour else 0

        intervals = [
            (records[idx].timestamp - records[idx - 1].timestamp).total_seconds()
            for idx in range(1, len(records))
        ]
        average_interval = mean(intervals) if intervals else 0.0

        return {
            "requests_per_hour": requests_per_hour,
            "peak_hour_requests": peak_hour_requests,
            "average_request_interval": average_interval,
        }

    def calculate_metrics(self, records: Iterable[UsageRecord]) -> Dict[str, Any]:
        records = list(records)
        return {
            "token_metrics": self.calculate_token_metrics(records),
            "rate_metrics": self.calculate_rate_metrics(records),
            "efficiency_metrics": self.calculate_efficiency_metrics(records),
        }

    def calculate_efficiency_metrics(self, records: Iterable[UsageRecord]) -> Dict[str, Any]:
        cost_per_model: Dict[str, Decimal] = {}
        for record in records:
            model = record.model or "unknown"
            tokens = max(record.total_tokens(), 1)
            cost_per_model.setdefault(model, Decimal("0"))
            cost_per_model[model] += record.cost / Decimal(tokens)

        if not cost_per_model:
            return {
                "cost_per_model": {},
                "most_efficient_model": None,
                "least_efficient_model": None,
            }

        most_efficient = min(cost_per_model, key=cost_per_model.get)
        least_efficient = max(cost_per_model, key=cost_per_model.get)

        return {
            "cost_per_model": cost_per_model,
            "most_efficient_model": most_efficient,
            "least_efficient_model": least_efficient,
        }

    def get_usage_trends(self, records: Iterable[UsageRecord]) -> Dict[str, Any]:
        records = list(records)
        if not records:
            return {
                "daily_cost_trend": [],
                "weekly_growth_rate": 0.0,
                "predicted_next_day_cost": Decimal("0"),
                "average_daily_cost": Decimal("0"),
            }

        daily_totals: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for record in records:
            day = record.timestamp.date().isoformat()
            daily_totals[day] += record.cost

        ordered_days = sorted(daily_totals.items())
        daily_costs = [cost for _, cost in ordered_days]
        average_daily = sum(daily_costs, Decimal("0")) / Decimal(len(daily_costs))

        if len(daily_costs) >= 2:
            growth = (daily_costs[-1] - daily_costs[0]) / max(daily_costs[0], Decimal("1"))
            weekly_growth = float(growth)
        else:
            weekly_growth = 0.0

        predicted_next = (daily_costs[-1] * Decimal("1.05")).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)

        return {
            "daily_cost_trend": ordered_days,
            "weekly_growth_rate": weekly_growth,
            "predicted_next_day_cost": predicted_next,
            "average_daily_cost": average_daily,
        }


class CostOptimizer:
    def optimize_model_selection(self, usage_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        if not usage_data:
            return {
                "recommended_model": None,
                "potential_savings": Decimal("0"),
                "quality_impact": "None",
                "summary": "No data available for savings analysis.",
            }

        scoring = {}
        for model, stats in usage_data.items():
            cost = _ensure_decimal(stats.get("cost"))
            requests = max(int(stats.get("requests", 0)), 1)
            quality = float(stats.get("quality_score", 0))
            scoring[model] = {
                "cost_per_request": cost / Decimal(requests),
                "quality": quality,
            }

        recommended = min(scoring, key=lambda m: (scoring[m]["cost_per_request"], -scoring[m]["quality"]))
        current = max(scoring, key=lambda m: scoring[m]["cost_per_request"])

        savings = (scoring[current]["cost_per_request"] - scoring[recommended]["cost_per_request"]) * Decimal(
            usage_data[current].get("requests", 0)
        )
        savings = savings if savings > 0 else Decimal("0")
        quality_delta = scoring[current]["quality"] - scoring[recommended]["quality"]

        summary = (
            f"Switch to {recommended} for potential savings of ${savings.quantize(Decimal('0.01'))} "
            f"with quality impact of {quality_delta:+.2f}"
        )

        return {
            "recommended_model": recommended,
            "potential_savings": savings.quantize(Decimal("0.01")) if savings > 0 else Decimal("0"),
            "quality_impact": f"{quality_delta:+.2f}",
            "summary": summary,
        }

    def suggest_cost_reductions(self, current_usage: Dict[str, Any]) -> List[Dict[str, Any]]:
        total_cost = _ensure_decimal(current_usage.get("total_cost"))
        openai_cost = _ensure_decimal(current_usage.get("openai_cost"))
        google_cost = _ensure_decimal(current_usage.get("google_cost"))
        youtube_cost = _ensure_decimal(current_usage.get("youtube_cost"))

        suggestions = [
            {
                "action": "model_right_sizing",
                "description": "Shift part of GPT-4 workload to GPT-3.5 where quality allows.",
                "estimated_savings": (openai_cost * Decimal("0.20")).quantize(Decimal("0.01")),
                "savings": (openai_cost * Decimal("0.20")).quantize(Decimal("0.01")),
                "details": "Downgrade select GPT-4 calls to GPT-3.5 where applicable.",
            },
            {
                "action": "cache_strategy",
                "description": "Expand caching for Gemini content to cut recompute frequency.",
                "estimated_savings": (google_cost * Decimal("0.15")).quantize(Decimal("0.01")),
                "savings": (google_cost * Decimal("0.15")).quantize(Decimal("0.01")),
                "details": "Increase cache TTL for Gemini content requests.",
            },
            {
                "action": "quota_review",
                "description": "Batch YouTube requests to stay under free quota allotments.",
                "estimated_savings": (youtube_cost * Decimal("0.10")).quantize(Decimal("0.01")),
                "savings": (youtube_cost * Decimal("0.10")).quantize(Decimal("0.01")),
                "details": "Batch YouTube lookups during peak hours to reduce quota burn.",
            },
        ]

        savings_total = sum((s["estimated_savings"] for s in suggestions), Decimal("0"))
        suggestions.append(
            {
                "action": "overall_savings",
                "description": "Total savings opportunity across optimizations.",
                "estimated_savings": savings_total.quantize(Decimal("0.01")),
                "savings": savings_total.quantize(Decimal("0.01")),
                "details": f"Combined savings opportunities worth ${savings_total.quantize(Decimal('0.01'))}",
            }
        )
        return suggestions

    def optimize_rate_limiting(self, rate_data: Dict[str, Any]) -> Dict[str, Any]:
        max_requests = max(int(rate_data.get("max_requests") or rate_data.get("rate_limit") or 0), 1)
        actual_requests = int(rate_data.get("actual_requests") or rate_data.get("requests_per_hour") or 0)
        efficiency = float(rate_data.get("current_rate_limit_usage") or (actual_requests / max_requests))
        distribution = rate_data.get("distribution", [])
        peak = max(distribution) if distribution else 0
        baseline = min(distribution) if distribution else 0
        spread = peak - baseline
        recommendation = "Distribute requests more evenly across the window" if spread > 0 else "Utilization is balanced"

        return {
            "rate_limit_efficiency": efficiency,
            "spreading_recommendations": recommendation,
        }

    def analyze_batching_opportunities(self, request_patterns: Dict[str, Any]) -> Dict[str, Any]:
        batchable = Decimal(str(request_patterns.get("batchable_requests", 0)))
        current_avg = Decimal(str(request_patterns.get("average_batch_size", 1)))
        optimal = Decimal(str(request_patterns.get("optimal_batch_size", max(float(current_avg), 1))))
        recommended_batch = max(optimal, Decimal("1"))
        improvement_factor = float((recommended_batch / max(current_avg, Decimal("1"))) if current_avg > 0 else 1)
        potential_batch_delta = max(recommended_batch - current_avg, Decimal("0"))
        potential_savings = (batchable * potential_batch_delta).quantize(Decimal("0.01"))
        recommendation = (
            "Increase batch size during peak windows"
            if potential_batch_delta > 0
            else "Batching already optimized"
        )

        return {
            "potential_batch_savings": potential_savings,
            "recommended_batch_size": float(recommended_batch),
            "batch_efficiency_gain": improvement_factor,
            "recommendation": recommendation,
        }


class BudgetManager:
    _global_spending: Decimal = Decimal("0")
    _global_service_spending: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    def __init__(self) -> None:
        self.budgets: Dict[str, Decimal] = {}
        self.spent: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        self.service_budgets: Dict[str, Decimal] = {}
        self.service_spent: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        self.alert_thresholds: List[int] = []
        self.daily_spending_history: deque[Decimal] = deque(maxlen=31)
        self._global_offset = BudgetManager._global_spending

    def set_budget(self, timeframe: str, amount: Decimal) -> None:
        self.budgets[timeframe] = _ensure_decimal(amount)

    def track_spending(self, amount: Decimal, timeframe: Optional[str] = None, service: Optional[str] = None) -> None:
        amount = _ensure_decimal(amount)
        if timeframe is None:
            if "monthly" in self.budgets:
                target = "monthly"
            elif "daily" in self.budgets:
                target = "daily"
            else:
                target = "general"
        else:
            target = timeframe
        self.spent[target] += amount
        BudgetManager.register_spending(amount, service=service)

    def check_budget_status(self, timeframe: str) -> Dict[str, Any]:
        budget = self.budgets.get(timeframe, Decimal("0"))
        spent = self.spent.get(timeframe, Decimal("0"))
        remaining = budget - spent
        percentage = float((spent / budget) * 100) if budget > 0 else 0.0
        return {
            "budget": budget,
            "spent": spent,
            "remaining": remaining,
            "percentage_used": round(percentage, 2),
        }

    def configure_alert_thresholds(self, thresholds: Iterable[int]) -> None:
        self.alert_thresholds = sorted(thresholds)

    def check_alerts(self) -> List[Dict[str, Any]]:
        alerts = []
        tracked_global = max(Decimal("0"), BudgetManager._global_spending - self._global_offset)
        for timeframe, budget in self.budgets.items():
            if budget <= 0:
                continue
            tracked = self.spent.get(timeframe, Decimal("0"))
            if timeframe == "daily":
                tracked = max(tracked, tracked_global)
            percent = float((tracked / budget) * 100)
            for threshold in self.alert_thresholds:
                if percent >= threshold:
                    alerts.append(
                        {
                            "timeframe": timeframe,
                            "threshold": threshold,
                            "current_percentage": round(percent, 2),
                        }
                    )
        return alerts

    def track_daily_spending(self, amount: Decimal) -> None:
        amount = _ensure_decimal(amount)
        self.daily_spending_history.append(amount)
        self.spent["daily"] += amount
        BudgetManager.register_spending(amount)

    def forecast_monthly_spending(self) -> Dict[str, Any]:
        if not self.daily_spending_history:
            return {
                "projected_monthly_cost": Decimal("0"),
                "days_until_budget_exhaustion": None,
                "recommended_daily_limit": None,
            }
        average_daily = sum(self.daily_spending_history, Decimal("0")) / Decimal(len(self.daily_spending_history))
        projected_monthly = (average_daily * Decimal("30")).quantize(Decimal("0.01"))
        monthly_budget = self.budgets.get("monthly", Decimal("0"))

        if average_daily > 0 and monthly_budget > 0:
            remaining = monthly_budget - self.spent.get("monthly", Decimal("0"))
            days_remaining = float((remaining / average_daily)) if remaining > 0 else 0.0
        else:
            days_remaining = None

        recommended_daily = monthly_budget / Decimal("30") if monthly_budget > 0 else None

        return {
            "projected_monthly_cost": projected_monthly,
            "days_until_budget_exhaustion": days_remaining,
            "recommended_daily_limit": recommended_daily,
        }

    def set_service_budget(self, service: str, amount: Decimal) -> None:
        self.service_budgets[service] = _ensure_decimal(amount)

    def track_service_spending(self, service: str, amount: Decimal) -> None:
        amount = _ensure_decimal(amount)
        self.service_spent[service] += amount
        BudgetManager.register_spending(amount, service=service)

    def get_service_budget_status(self) -> Dict[str, Dict[str, Any]]:
        status = {}
        for service, budget in self.service_budgets.items():
            spent = self.service_spent.get(service, Decimal("0"))
            status[service] = {
                "budget": budget,
                "spent": spent,
                "remaining": budget - spent,
            }
        return status

    @classmethod
    def register_spending(cls, amount: Decimal, service: Optional[str] = None) -> None:
        amount = _ensure_decimal(amount)
        cls._global_spending += amount
        if service:
            cls._global_service_spending[service] += amount


class ApiCostMonitor:
    def __init__(self, core_monitor: Optional[_CoreMonitor] = None) -> None:
        self._core_monitor = core_monitor or _CoreMonitor(db_path=":memory:")
        self._tracker = CostTracker()
        self._metrics = ApiUsageMetrics()
        self._optimizer = CostOptimizer()
        self._budget_manager = BudgetManager()
        self._configured_alerts: List[CostAlert] = []
        self._endpoints: Dict[str, ApiEndpoint] = {}

    async def track_api_call(self, service: str, endpoint: str = "", **kwargs: Any) -> UsageRecord:
        service_key = (service or "").lower()
        model = kwargs.get("model")
        input_tokens = int(kwargs.get("input_tokens", 0) or 0)
        output_tokens = int(kwargs.get("output_tokens", 0) or 0)
        characters = int(kwargs.get("characters", 0) or 0)
        requests = int(kwargs.get("requests", 0) or 0)
        quota_units = int(kwargs.get("quota_units", 0) or kwargs.get("request_units", 0) or requests)

        if service_key == "openai":
            cost = self._calculate_openai_cost(model, input_tokens, output_tokens)
        elif service_key == "google":
            cost = self._calculate_google_cost(model, characters)
        elif service_key == "youtube":
            cost = self._calculate_youtube_cost(endpoint, requests, quota_units)
        else:
            cost = _ensure_decimal(kwargs.get("cost"))

        record = UsageRecord(
            service=service_key,
            endpoint=endpoint,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            characters=characters,
            requests=requests,
            quota_units=quota_units,
            cost=cost,
        )
        self._tracker.record_usage(record)
        self._budget_manager.track_spending(cost, timeframe="daily", service=service_key)

        await self._core_monitor.record_usage(
            service=service_key,
            endpoint=endpoint or "generic",
            tokens_used=input_tokens or characters or requests,
            model=model,
            output_tokens=output_tokens,
        )
        return record

    def configure_endpoints(self, endpoints: Dict[str, ApiEndpoint]) -> None:
        self._endpoints = endpoints

    def configure_alerts(self, alerts: Iterable[CostAlert]) -> None:
        self._configured_alerts = list(alerts)

    def get_configured_alerts(self) -> List[CostAlert]:
        return list(self._configured_alerts)

    def get_current_costs(self, group_by: Optional[str] = None, timeframe: Optional[str] = None) -> Dict[str, Any]:
        records = self._get_usage_records_by_timeframe(timeframe) if timeframe else self._get_usage_records()
        totals: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        model_totals: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for record in records:
            totals[record.service] += record.cost
            model_totals[record.model or "unknown"] += record.cost

        total_cost = sum(totals.values(), Decimal("0"))

        if group_by == "service":
            return dict(totals)
        if group_by == "model":
            return dict(model_totals)

        return {
            "total": total_cost,
            "by_service": dict(totals),
            "by_model": dict(model_totals),
            "request_count": len(records),
        }

    def get_cost_analysis(self) -> Dict[str, Any]:
        records = self._get_usage_records()
        totals = self.get_current_costs()
        trends = self._metrics.get_usage_trends(records)

        usage_for_optimizer = {
            "total_cost": totals.get("total", Decimal("0")),
            "openai_cost": totals.get("by_service", {}).get("openai", Decimal("0")),
            "google_cost": totals.get("by_service", {}).get("google", Decimal("0")),
            "youtube_cost": totals.get("by_service", {}).get("youtube", Decimal("0")),
            "request_patterns": self._metrics.calculate_rate_metrics(records),
        }

        recommendations = self._optimizer.suggest_cost_reductions(usage_for_optimizer)
        projected_monthly = (trends.get("average_daily_cost", Decimal("0")) * Decimal("30")).quantize(
            Decimal("0.01")
        ) if trends.get("average_daily_cost") else Decimal("0")

        return {
            "total_cost": totals.get("total", Decimal("0")),
            "cost_by_service": totals.get("by_service", {}),
            "cost_trends": trends,
            "optimization_recommendations": recommendations,
            "projected_monthly_cost": projected_monthly,
        }

    def _get_usage_records(self) -> List[UsageRecord]:
        return self._tracker.get_records()

    def _get_usage_records_by_timeframe(self, timeframe: str) -> List[UsageRecord]:
        return self._tracker.get_records(timeframe=timeframe)

    def _calculate_openai_cost(self, model: Optional[str], input_tokens: int, output_tokens: int) -> Decimal:
        cost_models = self._core_monitor.COST_MODELS.get("openai", {})
        model_key = model if model in cost_models else next(iter(cost_models or {"gpt-3.5-turbo": {"input": 0, "output": 0}}))
        pricing = cost_models.get(model_key, {"input": 0, "output": 0})
        input_cost = Decimal(str(pricing.get("input", 0))) * Decimal(input_tokens)
        output_cost = Decimal(str(pricing.get("output", 0))) * Decimal(output_tokens)
        return (input_cost + output_cost).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)

    def _calculate_google_cost(self, model: Optional[str], characters: int) -> Decimal:
        endpoint = None
        if model:
            endpoint = next((cfg for cfg in self._endpoints.values() if cfg.model == model), None)
        per_character = Decimal(str(endpoint.cost_per_character)) if endpoint else Decimal("0.000000125")
        return (per_character * Decimal(characters)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)

    def _calculate_youtube_cost(self, endpoint_name: str, requests: int, quota_units: int) -> Decimal:
        endpoint = self._endpoints.get(endpoint_name)
        if endpoint and endpoint.cost_per_request:
            return (Decimal(str(endpoint.cost_per_request)) * Decimal(max(requests, 1))).quantize(
                Decimal("0.00001"), rounding=ROUND_HALF_UP
            )
        quota_cost = endpoint.quota_cost if endpoint else 1
        units = quota_units or (requests * quota_cost)
        return (Decimal(units) * Decimal("0.0001")).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)


__all__ = [
    "APICostMonitor",
    "ApiCostMonitor",
    "ApiEndpoint",
    "ApiUsageMetrics",
    "BudgetManager",
    "CostAlert",
    "CostOptimizer",
    "CostTracker",
    "UsageRecord",
    "check_rate_limit_decorator",
    "cost_monitor",
    "track_api_call",
]
