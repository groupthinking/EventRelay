# Performance Optimization Quick Reference

## 🎯 Quick Wins - Implement These First

### 1. Replace Blocking Sleep in Async Functions (5 minutes each)

**Files to fix:**
- `src/youtube_extension/integrations/cloud_ai/providers/azure_vision.py` (lines 273, 296)

**Find:** `time.sleep(N)`  
**Replace:** `await asyncio.sleep(N)`

**Impact:** 10-30x improvement in concurrent request handling

---

### 2. Replace Synchronous Requests with Async HTTP (15-30 minutes each)

**Files to fix:**
- `src/youtube_extension/backend/deployment_manager.py` (lines 494, 512, 523, 550, 587)

**Find:**
```python
import requests
response = requests.get(url, headers=headers)
```

**Replace:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(url, headers=headers)
```

**Impact:** 70-80% improvement in deployment throughput

---

### 3. Use Async File I/O (10 minutes each)

**Files to fix:** 45 instances across codebase (see `performance_analysis_results.json`)

**Find:**
```python
with open(path, 'r') as f:
    content = f.read()
```

**Replace:**
```python
import aiofiles

async with aiofiles.open(path, 'r') as f:
    content = await f.read()
```

**Impact:** 50-60% improvement in file operation throughput

---

## 🛠️ Use Performance Utilities

### Rate Limiting
```python
from youtube_extension.utils.performance import AsyncRateLimiter

limiter = AsyncRateLimiter(rate=10, per=1.0)  # 10 requests/second

async def api_call():
    async with limiter:
        return await external_api.call()
```

### Caching with LRU
```python
from youtube_extension.utils.performance import AsyncLRUCache

cache = AsyncLRUCache(maxsize=100, ttl=300)  # 100 items, 5 min TTL

result = await cache.get(key)
if result is None:
    result = await expensive_operation()
    await cache.set(key, result)
```

### Circuit Breaker for Fault Tolerance
```python
from youtube_extension.utils.performance import CircuitBreaker

breaker = CircuitBreaker(failure_threshold=5, timeout=60)

async def call_external_service():
    async with breaker:
        return await service.call()
```

### Automatic Retry with Backoff
```python
from youtube_extension.utils.performance import async_retry

@async_retry(max_attempts=3, backoff_base=2.0)
async def flaky_api_call():
    return await api.call()
```

### Performance Monitoring
```python
from youtube_extension.utils.performance import PerformanceMonitor

monitor = PerformanceMonitor()

async with monitor.measure("database_query"):
    results = await db.query()

# Get statistics
stats = await monitor.get_stats("database_query")
print(f"Mean: {stats['mean']:.3f}s, P95: {stats['p95']:.3f}s")
```

---

## 📊 Run Performance Analysis

```bash
# Analyze codebase for performance issues
python scripts/analyze_performance.py

# View detailed results
cat performance_analysis_results.json
```

---

## 🔍 Priority Matrix

| Issue | Files | Impact | Effort | Priority |
|-------|-------|--------|--------|----------|
| Blocking sleep in async | 2 | Critical | 5 min | 🔴 P0 |
| Sync HTTP in async | 6 | Critical | 30 min | 🔴 P0 |
| Sync file I/O in async | 45 | High | 2 hours | 🟡 P1 |
| No connection pooling | 10 | Medium | 1 hour | 🟡 P1 |
| Inefficient cache lookup | 1 | Medium | 2 hours | 🟢 P2 |
| Large files | 1 | Low | 4 hours | 🟢 P3 |

---

## 📈 Expected Results

### Phase 1 (P0 fixes - 1 hour)
- ✅ 3-5x improvement in concurrent request handling
- ✅ No more event loop blocking
- ✅ Better system responsiveness

### Phase 2 (P1 fixes - 3 hours)
- ✅ 2-3x improvement in I/O operations
- ✅ Better connection reuse
- ✅ Reduced latency

### Phase 3 (P2-P3 - ongoing)
- ✅ 90%+ cache hit rate improvements
- ✅ Better code maintainability
- ✅ Easier monitoring and debugging

### Overall Expected Improvement
- **Requests per second:** 5-10x increase
- **P95 latency:** 60-70% reduction
- **Resource usage:** 30-40% reduction
- **Concurrent capacity:** 10x increase (10 → 100 concurrent requests)

---

## 🧪 Testing Strategy

### 1. Unit Tests
```bash
# Test performance utilities
pytest tests/unit/test_performance_utils.py -v
```

### 2. Load Testing
```python
import asyncio
import time

async def load_test():
    """Test concurrent processing capacity"""
    tasks = [process_video(url) for _ in range(100)]
    
    start = time.monotonic()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.monotonic() - start
    
    success = sum(1 for r in results if not isinstance(r, Exception))
    print(f"Processed {success}/100 in {elapsed:.1f}s")
    print(f"Throughput: {success/elapsed:.1f} req/s")
```

### 3. Performance Monitoring
```python
# Add to your application startup
from youtube_extension.utils.performance import PerformanceMonitor

monitor = PerformanceMonitor()

# Instrument critical paths
async with monitor.measure("video_processing"):
    await process_video(url)

# Log metrics periodically
async def log_metrics():
    while True:
        for metric in ["video_processing", "api_calls", "cache_lookups"]:
            stats = await monitor.get_stats(metric)
            if stats:
                logger.info(
                    f"{metric}: mean={stats['mean']:.3f}s, "
                    f"p95={stats['p95']:.3f}s, count={stats['count']}"
                )
        await asyncio.sleep(60)
```

---

## 📚 Resources

- **Full Analysis:** [docs/PERFORMANCE_IMPROVEMENTS.md](./PERFORMANCE_IMPROVEMENTS.md)
- **Example Fix:** [docs/PERFORMANCE_FIX_EXAMPLE.md](./PERFORMANCE_FIX_EXAMPLE.md)
- **Performance Utilities:** `src/youtube_extension/utils/performance.py`
- **Analysis Script:** `scripts/analyze_performance.py`
- **Test Suite:** `tests/unit/test_performance_utils.py`

---

## 🎓 Best Practices

### ✅ DO
- Use `await asyncio.sleep()` in async functions
- Use `httpx.AsyncClient()` for async HTTP calls
- Use `aiofiles` for async file I/O
- Implement caching for expensive operations
- Add rate limiting for external APIs
- Use circuit breakers for fault tolerance
- Monitor performance metrics

### ❌ DON'T
- Use `time.sleep()` in async functions (blocks event loop)
- Use `requests` library in async functions (blocks)
- Use `open()` in async functions (blocks)
- Forget to close resources (use context managers)
- Ignore performance metrics
- Skip load testing
- Hardcode timeouts

---

## 🚀 Implementation Checklist

- [ ] Run performance analysis script
- [ ] Fix P0 issues (blocking sleep, sync HTTP)
- [ ] Add performance utilities to critical paths
- [ ] Run tests to validate changes
- [ ] Measure performance improvements
- [ ] Fix P1 issues (file I/O, connection pooling)
- [ ] Add monitoring to production
- [ ] Document performance characteristics
- [ ] Schedule P2-P3 improvements
- [ ] Conduct load testing

---

## 💡 Pro Tips

1. **Start with low-hanging fruit:** Fix blocking sleep first (5 min, huge impact)
2. **Measure before and after:** Use PerformanceMonitor to track improvements
3. **Test concurrency:** Use `asyncio.gather()` to verify parallel execution
4. **Monitor in production:** Track P95 latency, throughput, error rates
5. **Iterate:** Performance optimization is continuous, not one-time

---

Last updated: 2025-12-03
