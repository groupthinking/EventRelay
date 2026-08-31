import sys
from unittest.mock import MagicMock

# Mock missing dependencies
sys.modules['asyncpg'] = MagicMock()
sys.modules['psutil'] = MagicMock()

from typing import Any, Dict

from infrastructure.database.index_analysis import (
    DatabaseHealthMetrics,
    DatabaseOptimizer,
)


def create_targets(sub_achieved: bool, sub_percent: float,
                   cache_achieved: bool, cache_percent: float,
                   index_achieved: bool, index_percent: float) -> Dict[str, Any]:
    return {
        'sub_100ms_queries': {
            'achieved': sub_achieved,
            'current_percent': sub_percent
        },
        'cache_hit_ratio': {
            'achieved': cache_achieved,
            'current_percent': cache_percent
        },
        'index_utilization': {
            'achieved': index_achieved,
            'current_percent': index_percent
        }
    }

def create_metrics(connection_count: int) -> DatabaseHealthMetrics:
    # Most fields are not used by _calculate_performance_grade
    return DatabaseHealthMetrics(
        total_queries=100,
        avg_query_time=10.0,
        slow_query_count=5,
        slow_query_percent=5.0,
        connection_count=connection_count,
        cache_hit_ratio=95.0,
        table_bloat_percent=5.0,
        index_usage_percent=90.0
    )

def test_calculate_performance_grade_a():
    optimizer = DatabaseOptimizer("postgresql://user:pass@localhost/db")

    # Grade A: All targets achieved, connections < 50
    # 40 + 30 + 20 + 10 = 100
    metrics = create_metrics(connection_count=10)
    targets = create_targets(True, 100, True, 100, True, 100)
    assert optimizer._calculate_performance_grade(metrics, targets) == 'A'

    # Grade A: Edge case exactly 90
    # sub: 40 (achieved), cache: 30 (achieved), index: 10 (not achieved, 50%), conn: 10 (<50)
    # Total: 40 + 30 + 10 + 10 = 90
    metrics = create_metrics(connection_count=10)
    targets = create_targets(True, 100, True, 100, False, 50.0)
    assert optimizer._calculate_performance_grade(metrics, targets) == 'A'

def test_calculate_performance_grade_b():
    optimizer = DatabaseOptimizer("postgresql://user:pass@localhost/db")

    # Grade B: Score between 80 and 89
    # sub: 36 (not achieved, 90%), cache: 30 (achieved), index: 15 (not achieved, 75%), conn: 60 (5 points)
    # Total: 36 + 30 + 15 + 5 = 86
    metrics = create_metrics(connection_count=60)
    targets = create_targets(False, 90.0, True, 100.0, False, 75.0)
    assert optimizer._calculate_performance_grade(metrics, targets) == 'B'

    # Grade B: Edge case exactly 80
    # sub: 40 (achieved), cache: 30 (achieved), index: 0 (not achieved, 0%), conn: 10 (<50)
    # Total: 40 + 30 + 0 + 10 = 80
    metrics = create_metrics(connection_count=10)
    targets = create_targets(True, 100, True, 100, False, 0.0)
    assert optimizer._calculate_performance_grade(metrics, targets) == 'B'

def test_calculate_performance_grade_c():
    optimizer = DatabaseOptimizer("postgresql://user:pass@localhost/db")

    # Grade C: Score between 70 and 79
    # sub: 32 (not achieved, 80%), cache: 24 (not achieved, 80%), index: 16 (not achieved, 80%), conn: 70 (5 points)
    # Total: 32 + 24 + 16 + 5 = 77
    metrics = create_metrics(connection_count=70)
    targets = create_targets(False, 80.0, False, 80.0, False, 80.0)
    assert optimizer._calculate_performance_grade(metrics, targets) == 'C'

    # Grade C: Edge case exactly 70
    # sub: 40 (achieved), cache: 20 (not achieved, 66.66...%), index: 0 (not achieved, 0%), conn: 10 (<50)
    # Total: 40 + 20 + 0 + 10 = 70
    metrics = create_metrics(connection_count=10)
    targets = create_targets(True, 100, False, 66.66666666666667, False, 0.0)
    assert optimizer._calculate_performance_grade(metrics, targets) == 'C'

def test_calculate_performance_grade_d():
    optimizer = DatabaseOptimizer("postgresql://user:pass@localhost/db")

    # Grade D: Score between 60 and 69
    # sub: 24 (not achieved, 60%), cache: 18 (not achieved, 60%), index: 12 (not achieved, 60%), conn: 10 (10 points)
    # Total: 24 + 18 + 12 + 10 = 64
    metrics = create_metrics(connection_count=10)
    targets = create_targets(False, 60.0, False, 60.0, False, 60.0)
    assert optimizer._calculate_performance_grade(metrics, targets) == 'D'

    # Grade D: Edge case exactly 60
    # sub: 20 (not achieved, 50%), cache: 20 (not achieved, 66.66...%), index: 10 (not achieved, 50%), conn: 10 (10 points)
    # Total: 20 + 20 + 10 + 10 = 60
    metrics = create_metrics(connection_count=10)
    targets = create_targets(False, 50.0, False, 66.66666666666667, False, 50.0)
    assert optimizer._calculate_performance_grade(metrics, targets) == 'D'

def test_calculate_performance_grade_f():
    optimizer = DatabaseOptimizer("postgresql://user:pass@localhost/db")

    # Grade F: Score below 60
    # sub: 20 (not achieved, 50%), cache: 15 (not achieved, 50%), index: 10 (not achieved, 50%), conn: 150 (0 points)
    # Total: 20 + 15 + 10 + 0 = 45
    metrics = create_metrics(connection_count=150)
    targets = create_targets(False, 50.0, False, 50.0, False, 50.0)
    assert optimizer._calculate_performance_grade(metrics, targets) == 'F'

    # Grade F: Very poor performance
    metrics = create_metrics(connection_count=200)
    targets = create_targets(False, 0.0, False, 0.0, False, 0.0)
    assert optimizer._calculate_performance_grade(metrics, targets) == 'F'
