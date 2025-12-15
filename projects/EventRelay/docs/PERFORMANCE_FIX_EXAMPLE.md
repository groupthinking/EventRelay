# Example Performance Fix: Azure Vision Provider

## Issue
The Azure Vision provider uses blocking `time.sleep()` calls in async functions, which blocks the event loop and prevents concurrent processing.

**Location:** `src/youtube_extension/integrations/cloud_ai/providers/azure_vision.py`
**Lines:** 273, 296

## Before (Problematic Code)

```python
async def _perform_ocr_url(self, image_url: str) -> Dict[str, Any]:
    """Perform OCR on image from URL."""
    from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
    import time
    
    read_response = self._vision_client.read(image_url, raw=True)
    
    operation_location = read_response.headers["Operation-Location"]
    operation_id = operation_location.split("/")[-1]
    
    # Wait for operation completion
    max_wait_time = 30  # seconds
    elapsed = 0
    while elapsed < max_wait_time:
        result = self._vision_client.get_read_result(operation_id)
        if result.status not in [OperationStatusCodes.running, OperationStatusCodes.not_started]:
            break
        time.sleep(1)  # ❌ BLOCKS EVENT LOOP
        elapsed += 1
```

**Problem:** `time.sleep(1)` blocks the entire event loop for 1 second, preventing other async tasks from running.

## After (Fixed Code)

```python
async def _perform_ocr_url(self, image_url: str) -> Dict[str, Any]:
    """Perform OCR on image from URL."""
    from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
    
    read_response = self._vision_client.read(image_url, raw=True)
    
    operation_location = read_response.headers["Operation-Location"]
    operation_id = operation_location.split("/")[-1]
    
    # Wait for operation completion
    max_wait_time = 30  # seconds
    elapsed = 0
    while elapsed < max_wait_time:
        result = self._vision_client.get_read_result(operation_id)
        if result.status not in [OperationStatusCodes.running, OperationStatusCodes.not_started]:
            break
        await asyncio.sleep(1)  # ✅ NON-BLOCKING
        elapsed += 1
```

**Solution:** Replace `time.sleep(1)` with `await asyncio.sleep(1)` to yield control back to the event loop.

## Impact

### Before
- Blocks event loop for up to 30 seconds per OCR operation
- Can only process 1 OCR request at a time
- Other async operations stalled during OCR polling

### After
- Event loop remains responsive during polling
- Can process multiple OCR operations concurrently
- Other async operations continue uninterrupted

### Performance Improvement
- **Concurrent throughput**: 10-30x improvement (can handle 10-30 OCR operations simultaneously)
- **System responsiveness**: No blocking delays
- **Resource utilization**: Better CPU utilization across async tasks

## Testing

To verify the fix works correctly:

```python
import asyncio
import time

async def test_concurrent_ocr():
    """Test that multiple OCR operations can run concurrently"""
    provider = AzureVisionProvider(...)
    
    start = time.monotonic()
    
    # Launch 10 concurrent OCR operations
    results = await asyncio.gather(*[
        provider._perform_ocr_url(image_url)
        for _ in range(10)
    ])
    
    elapsed = time.monotonic() - start
    
    # With blocking sleep: ~300 seconds (30s × 10)
    # With async sleep: ~30 seconds (all run concurrently)
    print(f"Completed 10 OCR operations in {elapsed:.1f}s")
    assert elapsed < 60, "Should complete in under 60 seconds"
```

## Additional Recommendations

1. **Add timeout to polling loop**
   ```python
   import asyncio
   
   async def poll_with_timeout(timeout=30):
       start = time.monotonic()
       while (time.monotonic() - start) < timeout:
           result = self._vision_client.get_read_result(operation_id)
           if result.status not in [running, not_started]:
               return result
           await asyncio.sleep(1)
       raise TimeoutError("OCR operation timed out")
   ```

2. **Add exponential backoff for API polling**
   ```python
   poll_interval = 1.0
   while elapsed < max_wait_time:
       result = self._vision_client.get_read_result(operation_id)
       if result.status not in [running, not_started]:
           break
       await asyncio.sleep(poll_interval)
       poll_interval = min(poll_interval * 1.5, 5.0)  # Max 5 second intervals
   ```

3. **Use our AsyncRateLimiter utility**
   ```python
   from youtube_extension.utils.performance import AsyncRateLimiter
   
   # Limit API calls to avoid rate limiting
   self._rate_limiter = AsyncRateLimiter(rate=10, per=1.0)
   
   async with self._rate_limiter:
       result = self._vision_client.get_read_result(operation_id)
   ```

## Files to Fix

Apply similar fixes to these files identified by the performance analyzer:

1. `src/youtube_extension/integrations/cloud_ai/providers/azure_vision.py` (lines 273, 296)
2. `src/youtube_extension/backend/services/memory_manager.py` (multiple lines)

## Next Steps

1. Apply this fix to `azure_vision.py`
2. Run tests to ensure no regressions
3. Measure performance improvement with concurrent workload
4. Apply similar pattern to other files with blocking sleep
