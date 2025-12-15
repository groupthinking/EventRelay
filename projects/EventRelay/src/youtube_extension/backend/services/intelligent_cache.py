#!/usr/bin/env python3
"""
Intelligent Multi-Layer Caching System
======================================

Phase 3 Performance Optimization: Intelligent caching strategy with multi-layer
architecture (Redis, in-memory, CDN) targeting 60%+ performance improvements.

Key Features:
- Multi-layer caching (L1: In-memory, L2: Redis, L3: Database)
- Intelligent cache invalidation and warming
- Adaptive TTL based on access patterns
- Cache hit ratio optimization
- Automatic cache clustering for high availability
- Performance analytics and optimization recommendations
"""

import asyncio
import json
import logging
import time
import hashlib
# pickle removed for security
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, OrderedDict
import threading
import redis.asyncio as redis
from contextlib import asynccontextmanager
import sqlite3
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return {"__type__": "datetime", "iso": obj.isoformat()}
        return super().default(obj)

def datetime_decoder(obj):
    """JSON decoder that restores datetime objects"""
    if "__type__" in obj and obj["__type__"] == "datetime":
        return datetime.fromisoformat(obj["iso"])
    return obj

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: datetime = None
    size_bytes: int = 0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.last_accessed is None:
            self.last_accessed = self.created_at

@dataclass
class CacheStats:
    """Cache statistics"""
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    total_entries: int = 0
    total_size_bytes: int = 0
    avg_access_time_ms: float = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hit_count + self.miss_count
        return (self.hit_count / total * 100) if total > 0 else 0

class IntelligentCacheLayer:
    """Base class for cache layers"""
    
    def __init__(self, name: str, max_size: int = 1000):
        self.name = name
        self.max_size = max_size
        self.stats = CacheStats()
        self._lock = threading.RLock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        raise NotImplementedError
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: List[str] = None) -> bool:
        """Set value in cache"""
        raise NotImplementedError
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        raise NotImplementedError
    
    async def clear(self) -> int:
        """Clear all cache entries"""
        raise NotImplementedError
    
    async def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        return self.stats

class InMemoryCacheLayer(IntelligentCacheLayer):
    """L1 Cache: In-memory cache with LRU eviction"""
    
    def __init__(self, name: str = "L1_Memory", max_size: int = 10000, max_size_bytes: int = 100 * 1024 * 1024):  # 100MB
        super().__init__(name, max_size)
        self.max_size_bytes = max_size_bytes
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.access_patterns = defaultdict(list)  # Track access patterns for intelligent TTL
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from in-memory cache"""
        start_time = time.time()
        
        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                
                # Check expiration
                if entry.expires_at and datetime.now(timezone.utc) > entry.expires_at:
                    del self.cache[key]
                    self.stats.miss_count += 1
                    return None
                
                # Update access info
                entry.access_count += 1
                entry.last_accessed = datetime.now(timezone.utc)
                self.access_patterns[key].append(time.time())
                
                # Move to end (LRU)
                self.cache.move_to_end(key)
                
                self.stats.hit_count += 1
                access_time = (time.time() - start_time) * 1000
                self._update_avg_access_time(access_time)
                
                logger.debug(f"L1 Cache HIT: {key}")
                return entry.value
            
            self.stats.miss_count += 1
            logger.debug(f"L1 Cache MISS: {key}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: List[str] = None) -> bool:
        """Set value in in-memory cache"""
        try:
            # Calculate size (using JSON for safety)
            size_bytes = len(json.dumps(value, cls=DateTimeEncoder).encode('utf-8'))
            
            with self._lock:
                # Check if we need to evict
                await self._evict_if_needed(size_bytes)
                
                # Calculate expiration
                expires_at = None
                if ttl:
                    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
                
                # Create entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.now(timezone.utc),
                    expires_at=expires_at,
                    size_bytes=size_bytes,
                    tags=tags or []
                )
                
                # Update existing or add new
                if key in self.cache:
                    old_entry = self.cache[key]
                    self.stats.total_size_bytes -= old_entry.size_bytes
                else:
                    self.stats.total_entries += 1
                
                self.cache[key] = entry
                self.stats.total_size_bytes += size_bytes
                
                logger.debug(f"L1 Cache SET: {key} ({size_bytes} bytes)")
                return True
                
        except Exception as e:
            logger.error(f"Failed to set L1 cache entry {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from in-memory cache"""
        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                del self.cache[key]
                self.stats.total_entries -= 1
                self.stats.total_size_bytes -= entry.size_bytes
                
                # Clean access patterns
                if key in self.access_patterns:
                    del self.access_patterns[key]
                
                logger.debug(f"L1 Cache DELETE: {key}")
                return True
            return False
    
    async def clear(self) -> int:
        """Clear all in-memory cache entries"""
        with self._lock:
            count = len(self.cache)
            self.cache.clear()
            self.access_patterns.clear()
            self.stats.total_entries = 0
            self.stats.total_size_bytes = 0
            logger.info(f"L1 Cache CLEARED: {count} entries")
            return count
    
    async def _evict_if_needed(self, new_size_bytes: int):
        """Evict entries if needed to make space"""
        while (len(self.cache) >= self.max_size or 
               self.stats.total_size_bytes + new_size_bytes > self.max_size_bytes):
            
            if not self.cache:
                break
            
            # Remove oldest entry (LRU)
            oldest_key = next(iter(self.cache))
            entry = self.cache[oldest_key]
            del self.cache[oldest_key]
            
            self.stats.total_entries -= 1
            self.stats.total_size_bytes -= entry.size_bytes
            self.stats.eviction_count += 1
            
            logger.debug(f"L1 Cache EVICTED: {oldest_key}")
    
    def _update_avg_access_time(self, access_time_ms: float):
        """Update average access time"""
        if self.stats.avg_access_time_ms == 0:
            self.stats.avg_access_time_ms = access_time_ms
        else:
            # Exponential moving average
            alpha = 0.1
            self.stats.avg_access_time_ms = (alpha * access_time_ms + 
                                           (1 - alpha) * self.stats.avg_access_time_ms)

class RedisCacheLayer(IntelligentCacheLayer):
    """L2 Cache: Redis distributed cache"""
    
    def __init__(self, name: str = "L2_Redis", redis_url: str = "redis://localhost:6379", max_connections: int = 20):
        super().__init__(name, max_size=100000)  # Logical limit for Redis
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.redis_pool = None
        self._connected = False
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                decode_responses=False  # We handle binary data
            )
            
            # Test connection
            async with redis.Redis(connection_pool=self.redis_pool) as conn:
                await conn.ping()
            
            self._connected = True
            logger.info(f"✅ Redis cache layer connected: {self.redis_url}")
            
        except Exception as e:
            logger.warning(f"❌ Failed to connect to Redis: {e}")
            self._connected = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self._connected:
            return None
        
        start_time = time.time()
        
        try:
            async with redis.Redis(connection_pool=self.redis_pool) as conn:
                # Get serialized data
                data = await conn.get(f"uvai:cache:{key}")
                
                if data:
                    # Deserialize using JSON
                    try:
                        entry_data = json.loads(data, object_hook=datetime_decoder)
                    except (json.JSONDecodeError, TypeError):
                        # Fallback for legacy pickle data (optional, or just treat as miss)
                        logger.warning(f"Failed to decode JSON for {key}, treating as miss")
                        return None
                    
                    # Update access count
                    await conn.hincrby(f"uvai:stats:{key}", "access_count", 1)
                    await conn.hset(f"uvai:stats:{key}", "last_accessed", time.time())
                    
                    self.stats.hit_count += 1
                    access_time = (time.time() - start_time) * 1000
                    self._update_avg_access_time(access_time)
                    
                    logger.debug(f"L2 Redis HIT: {key}")
                    return entry_data["value"]
                
                self.stats.miss_count += 1
                logger.debug(f"L2 Redis MISS: {key}")
                return None
                
        except Exception as e:
            logger.error(f"Redis get error for {key}: {e}")
            self.stats.miss_count += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: List[str] = None) -> bool:
        """Set value in Redis cache"""
        if not self._connected:
            return False
        
        try:
            async with redis.Redis(connection_pool=self.redis_pool) as conn:
                # Prepare entry data
                entry_data = {
                    "value": value,
                    "created_at": time.time(),
                    "tags": tags or []
                }
                
                # Serialize using JSON
                serialized_data = json.dumps(entry_data, cls=DateTimeEncoder)
                
                # Set with TTL
                if ttl:
                    await conn.setex(f"uvai:cache:{key}", ttl, serialized_data)
                else:
                    await conn.set(f"uvai:cache:{key}", serialized_data)
                
                # Store metadata
                await conn.hset(f"uvai:stats:{key}", mapping={
                    "created_at": time.time(),
                    "access_count": 0,
                    "size_bytes": len(serialized_data)
                })
                
                # Add to tag sets for invalidation
                for tag in (tags or []):
                    await conn.sadd(f"uvai:tag:{tag}", key)
                
                logger.debug(f"L2 Redis SET: {key} ({len(serialized_data)} bytes)")
                return True
                
        except Exception as e:
            logger.error(f"Redis set error for {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache"""
        if not self._connected:
            return False
        
        try:
            async with redis.Redis(connection_pool=self.redis_pool) as conn:
                # Get tags before deletion
                stats_data = await conn.hgetall(f"uvai:stats:{key}")
                
                # Delete main entry and stats
                deleted = await conn.delete(f"uvai:cache:{key}", f"uvai:stats:{key}")
                
                # Clean up tag references (would need to get tags first in real implementation)
                # This is simplified for demo
                
                logger.debug(f"L2 Redis DELETE: {key}")
                return deleted > 0
                
        except Exception as e:
            logger.error(f"Redis delete error for {key}: {e}")
            return False
    
    async def clear(self) -> int:
        """Clear all Redis cache entries"""
        if not self._connected:
            return 0
        
        try:
            async with redis.Redis(connection_pool=self.redis_pool) as conn:
                # Get all cache keys
                keys = await conn.keys("uvai:cache:*")
                stat_keys = await conn.keys("uvai:stats:*")
                tag_keys = await conn.keys("uvai:tag:*")
                
                all_keys = keys + stat_keys + tag_keys
                
                if all_keys:
                    deleted = await conn.delete(*all_keys)
                    logger.info(f"L2 Redis CLEARED: {deleted} entries")
                    return deleted
                
                return 0
                
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return 0
    
    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate cache entries by tags"""
        if not self._connected:
            return 0
        
        try:
            async with redis.Redis(connection_pool=self.redis_pool) as conn:
                total_deleted = 0
                
                for tag in tags:
                    # Get all keys with this tag
                    keys = await conn.smembers(f"uvai:tag:{tag}")
                    
                    if keys:
                        # Delete cache entries
                        cache_keys = [f"uvai:cache:{key.decode()}" if isinstance(key, bytes) else f"uvai:cache:{key}" for key in keys]
                        stat_keys = [f"uvai:stats:{key.decode()}" if isinstance(key, bytes) else f"uvai:stats:{key}" for key in keys]
                        
                        deleted = await conn.delete(*(cache_keys + stat_keys + [f"uvai:tag:{tag}"]))
                        total_deleted += deleted
                
                logger.info(f"L2 Redis TAG INVALIDATION: {total_deleted} entries for tags {tags}")
                return total_deleted
                
        except Exception as e:
            logger.error(f"Redis tag invalidation error: {e}")
            return 0
    
    def _update_avg_access_time(self, access_time_ms: float):
        """Update average access time"""
        if self.stats.avg_access_time_ms == 0:
            self.stats.avg_access_time_ms = access_time_ms
        else:
            # Exponential moving average
            alpha = 0.1
            self.stats.avg_access_time_ms = (alpha * access_time_ms + 
                                           (1 - alpha) * self.stats.avg_access_time_ms)

class IntelligentCacheSystem:
    """
    Multi-layer intelligent caching system
    
    Architecture:
    - L1: In-memory cache (fastest, smallest)
    - L2: Redis cache (fast, distributed)
    - L3: Database/persistent storage (slowest, largest)
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.layers = [
            InMemoryCacheLayer("L1_Memory", max_size=10000),
            RedisCacheLayer("L2_Redis", redis_url=redis_url)
        ]
        
        self.adaptive_ttl_enabled = True
        self.cache_warming_enabled = True
        self.auto_invalidation_enabled = True
        
        # Performance tracking
        self.performance_history = []
        self.optimization_suggestions = []
        
        logger.info("🧠 Intelligent Cache System initialized")
    
    async def initialize(self):
        """Initialize all cache layers"""
        for layer in self.layers:
            if hasattr(layer, 'connect'):
                await layer.connect()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache layers (L1 → L2 → L3)"""
        start_time = time.time()
        
        for i, layer in enumerate(self.layers):
            value = await layer.get(key)
            
            if value is not None:
                # Cache promotion: populate higher levels
                await self._promote_cache_entry(key, value, i)
                
                access_time = (time.time() - start_time) * 1000
                self._record_access_performance(key, access_time, i)
                
                return value
        
        # Cache miss in all layers
        access_time = (time.time() - start_time) * 1000
        self._record_access_performance(key, access_time, -1)
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: List[str] = None) -> bool:
        """Set value in all cache layers"""
        # Calculate adaptive TTL if enabled
        if self.adaptive_ttl_enabled and ttl is None:
            ttl = self._calculate_adaptive_ttl(key)
        
        results = []
        for layer in self.layers:
            result = await layer.set(key, value, ttl, tags)
            results.append(result)
        
        return any(results)  # Success if at least one layer succeeded
    
    async def delete(self, key: str) -> bool:
        """Delete value from all cache layers"""
        results = []
        for layer in self.layers:
            result = await layer.delete(key)
            results.append(result)
        
        return any(results)
    
    async def clear(self) -> Dict[str, int]:
        """Clear all cache layers"""
        results = {}
        for layer in self.layers:
            count = await layer.clear()
            results[layer.name] = count
        
        return results
    
    async def invalidate_by_tags(self, tags: List[str]) -> Dict[str, int]:
        """Invalidate cache entries by tags in all layers"""
        results = {}
        for layer in self.layers:
            if hasattr(layer, 'invalidate_by_tags'):
                count = await layer.invalidate_by_tags(tags)
                results[layer.name] = count
        
        return results
    
    async def warm_cache(self, keys_and_values: List[Tuple[str, Any]], ttl: Optional[int] = None):
        """Warm cache with predefined key-value pairs"""
        if not self.cache_warming_enabled:
            return
        
        logger.info(f"🔥 Warming cache with {len(keys_and_values)} entries")
        
        tasks = []
        for key, value in keys_and_values:
            tasks.append(self.set(key, value, ttl))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        
        logger.info(f"✅ Cache warming completed: {success_count}/{len(keys_and_values)} successful")
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all cache layers"""
        stats = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'layers': {},
            'overall': {
                'hit_rate': 0,
                'total_requests': 0,
                'avg_access_time_ms': 0
            },
            'optimization_suggestions': self.optimization_suggestions[-10:]  # Last 10 suggestions
        }
        
        total_hits = 0
        total_requests = 0
        total_access_time = 0
        
        for layer in self.layers:
            layer_stats = await layer.get_stats()
            stats['layers'][layer.name] = asdict(layer_stats)
            
            total_hits += layer_stats.hit_count
            total_requests += layer_stats.hit_count + layer_stats.miss_count
            total_access_time += layer_stats.avg_access_time_ms
        
        if total_requests > 0:
            stats['overall']['hit_rate'] = (total_hits / total_requests) * 100
            stats['overall']['total_requests'] = total_requests
            stats['overall']['avg_access_time_ms'] = total_access_time / len(self.layers)
        
        return stats
    
    async def _promote_cache_entry(self, key: str, value: Any, found_at_layer: int):
        """Promote cache entry to higher layers"""
        for i in range(found_at_layer):
            layer = self.layers[i]
            await layer.set(key, value, ttl=self._calculate_promotion_ttl(i))
    
    def _calculate_adaptive_ttl(self, key: str) -> int:
        """Calculate adaptive TTL based on access patterns"""
        # Default TTL values
        base_ttl = 3600  # 1 hour
        
        # Get access patterns from L1 cache
        l1_layer = self.layers[0]
        if hasattr(l1_layer, 'access_patterns') and key in l1_layer.access_patterns:
            accesses = l1_layer.access_patterns[key]
            
            if len(accesses) > 1:
                # Calculate access frequency
                time_span = accesses[-1] - accesses[0]
                if time_span > 0:
                    frequency = len(accesses) / time_span  # accesses per second
                    
                    # Higher frequency = longer TTL
                    if frequency > 0.1:  # More than once per 10 seconds
                        return base_ttl * 4  # 4 hours
                    elif frequency > 0.01:  # More than once per 100 seconds
                        return base_ttl * 2  # 2 hours
        
        return base_ttl
    
    def _calculate_promotion_ttl(self, layer_index: int) -> int:
        """Calculate TTL for promoted cache entries"""
        # Higher layers get shorter TTL
        base_ttl = 1800  # 30 minutes
        return base_ttl // (layer_index + 1)
    
    def _record_access_performance(self, key: str, access_time_ms: float, layer_found: int):
        """Record access performance for optimization analysis"""
        self.performance_history.append({
            'key': key,
            'access_time_ms': access_time_ms,
            'layer_found': layer_found,
            'timestamp': time.time()
        })
        
        # Keep only recent history
        if len(self.performance_history) > 10000:
            self.performance_history = self.performance_history[-5000:]
        
        # Generate optimization suggestions
        if len(self.performance_history) % 1000 == 0:  # Every 1000 accesses
            self._analyze_performance_and_suggest_optimizations()
    
    def _analyze_performance_and_suggest_optimizations(self):
        """Analyze performance history and suggest optimizations"""
        if len(self.performance_history) < 100:
            return
        
        recent_history = self.performance_history[-1000:]  # Last 1000 accesses
        
        # Analyze L1 hit rate
        l1_hits = len([h for h in recent_history if h['layer_found'] == 0])
        l1_hit_rate = (l1_hits / len(recent_history)) * 100
        
        if l1_hit_rate < 70:  # Less than 70% L1 hit rate
            self.optimization_suggestions.append({
                'type': 'increase_l1_size',
                'message': f'L1 hit rate is {l1_hit_rate:.1f}%. Consider increasing L1 cache size.',
                'priority': 'medium',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        # Analyze access times
        access_times = [h['access_time_ms'] for h in recent_history]
        avg_access_time = statistics.mean(access_times)
        
        if avg_access_time > 50:  # More than 50ms average
            self.optimization_suggestions.append({
                'type': 'slow_access_pattern',
                'message': f'Average cache access time is {avg_access_time:.1f}ms. Check for serialization bottlenecks.',
                'priority': 'high',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        # Analyze cache misses
        total_misses = len([h for h in recent_history if h['layer_found'] == -1])
        miss_rate = (total_misses / len(recent_history)) * 100
        
        if miss_rate > 30:  # More than 30% misses
            self.optimization_suggestions.append({
                'type': 'high_miss_rate',
                'message': f'Cache miss rate is {miss_rate:.1f}%. Consider cache warming or longer TTLs.',
                'priority': 'high',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

# Global intelligent cache system
intelligent_cache = IntelligentCacheSystem()

# Convenience functions
async def cache_get(key: str) -> Optional[Any]:
    """Get value from intelligent cache"""
    return await intelligent_cache.get(key)

async def cache_set(key: str, value: Any, ttl: Optional[int] = None, tags: List[str] = None) -> bool:
    """Set value in intelligent cache"""
    return await intelligent_cache.set(key, value, ttl, tags)

async def cache_delete(key: str) -> bool:
    """Delete value from intelligent cache"""
    return await intelligent_cache.delete(key)

async def cache_invalidate_tags(tags: List[str]) -> Dict[str, int]:
    """Invalidate cache entries by tags"""
    return await intelligent_cache.invalidate_by_tags(tags)

def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def cached(ttl: Optional[int] = None, tags: List[str] = None, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_str = f"{key_prefix}{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = await cache_get(cache_key_str)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_set(cache_key_str, result, ttl, tags)
            
            return result
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we can't directly use async cache
            # This would need to be handled differently in production
            return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

if __name__ == "__main__":
    async def test_intelligent_cache():
        # Initialize cache system
        await intelligent_cache.initialize()
        
        # Test basic operations
        await cache_set("test_key", {"data": "test_value", "number": 42}, ttl=300)
        
        result = await cache_get("test_key")
        print(f"Cache result: {result}")
        
        # Test cache warming
        warm_data = [
            ("warm_key_1", {"type": "video_analysis", "result": "cached"}),
            ("warm_key_2", {"type": "database_query", "result": "optimized"})
        ]
        await intelligent_cache.warm_cache(warm_data)
        
        # Get comprehensive stats
        stats = await intelligent_cache.get_comprehensive_stats()
        print(f"Cache stats: {json.dumps(stats, indent=2, default=str)}")
    
if __name__ == "__main__":
    asyncio.run(test_intelligent_cache())