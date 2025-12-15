#!/usr/bin/env python3
import os
import asyncio
import json
import time

os.environ.setdefault("PYTHONPATH", "/workspace/src")

from youtube_extension.backend.services.performance_benchmark_system import run_performance_benchmark


async def main():
    start = time.time()
    results = await run_performance_benchmark(iterations=1)
    assessment = results.get('overall_assessment', {})
    print(json.dumps({
        'overall_grade': assessment.get('overall_grade'),
        'targets_met': assessment.get('targets_met'),
        'total_targets': assessment.get('total_targets'),
        'summary': assessment.get('summary'),
        'components': {k: (v.get('error') or v.get('performance_summary')) for k, v in results.get('components', {}).items()},
        'duration_s': round(time.time() - start, 3)
    }, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

