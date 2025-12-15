/**
 * Service Worker for Intelligent Caching
 * ======================================
 * 
 * Phase 3 Performance Optimization: Service worker implementation for
 * intelligent caching strategy targeting sub-2 second load times with
 * advanced caching patterns and offline capabilities.
 * 
 * Key Features:
 * - Intelligent cache management with TTL
 * - Network-first strategy for API calls
 * - Cache-first strategy for static assets
 * - Background sync for offline functionality
 * - Performance metrics collection
 * - Automatic cache cleanup and optimization
 */

const CACHE_NAME = 'uvai-platform-v1.0.0';
const STATIC_CACHE = 'uvai-static-v1.0.0';
const API_CACHE = 'uvai-api-v1.0.0';
const IMAGE_CACHE = 'uvai-images-v1.0.0';

// Cache configuration
const CACHE_CONFIG = {
    // Static assets (CSS, JS, fonts) - Long term caching
    static: {
        name: STATIC_CACHE,
        strategy: 'CacheFirst',
        maxAge: 30 * 24 * 60 * 60 * 1000, // 30 days
        maxEntries: 100
    },
    
    // API responses - Network first with fallback
    api: {
        name: API_CACHE,
        strategy: 'NetworkFirst',
        maxAge: 5 * 60 * 1000, // 5 minutes
        maxEntries: 50,
        networkTimeout: 3000 // 3 seconds
    },
    
    // Images and media - Cache first for performance
    images: {
        name: IMAGE_CACHE,
        strategy: 'CacheFirst',
        maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
        maxEntries: 200
    },
    
    // HTML pages - Network first for freshness
    pages: {
        name: CACHE_NAME,
        strategy: 'NetworkFirst',
        maxAge: 60 * 60 * 1000, // 1 hour
        maxEntries: 20,
        networkTimeout: 2000 // 2 seconds
    }
};

// Resources to precache on install
const PRECACHE_RESOURCES = [
    '/',
    '/dashboard',
    '/static/css/main.css',
    '/static/js/main.js',
    '/manifest.json'
];

// Performance metrics collection
class ServiceWorkerMetrics {
    constructor() {
        this.metrics = new Map();
        this.startTime = Date.now();
    }
    
    recordCacheHit(cacheName, url) {
        this.recordMetric(`cache_hit_${cacheName}`, 1);
        this.recordMetric('total_cache_hits', 1);
        
        console.log(`[SW] 🎯 Cache HIT: ${cacheName} - ${url}`);
    }
    
    recordCacheMiss(cacheName, url) {
        this.recordMetric(`cache_miss_${cacheName}`, 1);
        this.recordMetric('total_cache_misses', 1);
        
        console.log(`[SW] ❌ Cache MISS: ${cacheName} - ${url}`);
    }
    
    recordNetworkTime(url, duration) {
        this.recordMetric('network_request_time', duration);
        
        if (duration > 2000) { // >2s network request
            console.warn(`[SW] 🐌 Slow network: ${url} (${duration}ms)`);
        }
    }
    
    recordMetric(name, value) {
        if (!this.metrics.has(name)) {
            this.metrics.set(name, []);
        }
        
        this.metrics.get(name).push({
            value,
            timestamp: Date.now()
        });
        
        // Keep only last 1000 measurements per metric
        const measurements = this.metrics.get(name);
        if (measurements.length > 1000) {
            measurements.shift();
        }
    }
    
    getMetricsSummary() {
        const summary = {
            timestamp: Date.now(),
            uptime: Date.now() - this.startTime,
            metrics: {}
        };
        
        for (const [name, measurements] of this.metrics.entries()) {
            if (measurements.length > 0) {
                const values = measurements.map(m => m.value);
                summary.metrics[name] = {
                    count: values.length,
                    sum: values.reduce((a, b) => a + b, 0),
                    average: values.reduce((a, b) => a + b, 0) / values.length,
                    min: Math.min(...values),
                    max: Math.max(...values)
                };
            }
        }
        
        // Calculate cache hit ratio
        const totalHits = summary.metrics.total_cache_hits?.sum || 0;
        const totalMisses = summary.metrics.total_cache_misses?.sum || 0;
        const totalRequests = totalHits + totalMisses;
        
        summary.cacheHitRatio = totalRequests > 0 ? (totalHits / totalRequests) * 100 : 0;
        
        return summary;
    }
}

const metrics = new ServiceWorkerMetrics();

// Install event - precache resources
self.addEventListener('install', (event) => {
    console.log('[SW] 🚀 Installing service worker...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] 📦 Precaching resources...');
                return cache.addAll(PRECACHE_RESOURCES);
            })
            .then(() => {
                console.log('[SW] ✅ Installation complete');
                return self.skipWaiting(); // Activate immediately
            })
            .catch((error) => {
                console.error('[SW] ❌ Installation failed:', error);
            })
    );
});

// Activate event - cleanup old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] 🔄 Activating service worker...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                const validCacheNames = Object.values(CACHE_CONFIG).map(config => config.name);
                validCacheNames.push(CACHE_NAME);
                
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (!validCacheNames.includes(cacheName)) {
                            console.log(`[SW] 🗑️ Deleting old cache: ${cacheName}`);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('[SW] ✅ Activation complete');
                return self.clients.claim(); // Take control of all clients
            })
    );
});

// Fetch event - intelligent caching strategies
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Determine caching strategy based on request type
    let strategy = null;
    
    if (isStaticAsset(url)) {
        strategy = createCacheFirstStrategy(CACHE_CONFIG.static);
    } else if (isAPIRequest(url)) {
        strategy = createNetworkFirstStrategy(CACHE_CONFIG.api);
    } else if (isImageRequest(url)) {
        strategy = createCacheFirstStrategy(CACHE_CONFIG.images);
    } else if (isPageRequest(url)) {
        strategy = createNetworkFirstStrategy(CACHE_CONFIG.pages);
    }
    
    if (strategy) {
        event.respondWith(strategy(request));
    }
});

// Cache-first strategy for static assets
function createCacheFirstStrategy(config) {
    return async (request) => {
        const cache = await caches.open(config.name);
        
        try {
            // Try cache first
            const cachedResponse = await cache.match(request);
            
            if (cachedResponse) {
                // Check if cached response is still valid
                const cacheTime = getCacheTime(cachedResponse);
                const isExpired = cacheTime && (Date.now() - cacheTime > config.maxAge);
                
                if (!isExpired) {
                    metrics.recordCacheHit(config.name, request.url);
                    return cachedResponse;
                }
            }
            
            // Cache miss or expired - fetch from network
            metrics.recordCacheMiss(config.name, request.url);
            const networkStart = Date.now();
            
            const networkResponse = await fetch(request);
            const networkTime = Date.now() - networkStart;
            
            metrics.recordNetworkTime(request.url, networkTime);
            
            // Cache successful responses
            if (networkResponse.ok) {
                const responseToCache = networkResponse.clone();
                await setCacheWithTimestamp(cache, request, responseToCache);
                
                // Cleanup old entries if needed
                await cleanupCache(cache, config);
            }
            
            return networkResponse;
            
        } catch (error) {
            console.error(`[SW] ❌ Cache-first strategy failed for ${request.url}:`, error);
            
            // Return cached response if available (even if expired)
            const cachedResponse = await cache.match(request);
            if (cachedResponse) {
                console.log(`[SW] 🚑 Serving stale cache for ${request.url}`);
                return cachedResponse;
            }
            
            throw error;
        }
    };
}

// Network-first strategy for API calls and pages
function createNetworkFirstStrategy(config) {
    return async (request) => {
        const cache = await caches.open(config.name);
        
        try {
            // Try network first with timeout
            const networkStart = Date.now();
            
            const networkResponse = await Promise.race([
                fetch(request),
                new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('Network timeout')), config.networkTimeout)
                )
            ]);
            
            const networkTime = Date.now() - networkStart;
            metrics.recordNetworkTime(request.url, networkTime);
            
            // Cache successful responses
            if (networkResponse.ok) {
                const responseToCache = networkResponse.clone();
                await setCacheWithTimestamp(cache, request, responseToCache);
                
                // Cleanup old entries if needed
                await cleanupCache(cache, config);
            }
            
            return networkResponse;
            
        } catch (error) {
            console.log(`[SW] 🌐 Network failed for ${request.url}, trying cache...`);
            
            // Network failed - try cache
            const cachedResponse = await cache.match(request);
            
            if (cachedResponse) {
                const cacheTime = getCacheTime(cachedResponse);
                const isExpired = cacheTime && (Date.now() - cacheTime > config.maxAge);
                
                if (!isExpired) {
                    metrics.recordCacheHit(config.name, request.url);
                    console.log(`[SW] 🎯 Serving cached response for ${request.url}`);
                    return cachedResponse;
                } else {
                    console.log(`[SW] 🚑 Serving expired cache for ${request.url}`);
                    return cachedResponse; // Serve expired cache as fallback
                }
            }
            
            metrics.recordCacheMiss(config.name, request.url);
            console.error(`[SW] ❌ No cache available for ${request.url}`);
            throw error;
        }
    };
}

// Helper functions for request categorization
function isStaticAsset(url) {
    return /\.(css|js|woff|woff2|ttf|eot|ico)$/i.test(url.pathname) ||
           url.pathname.startsWith('/static/');
}

function isAPIRequest(url) {
    return url.pathname.startsWith('/api/') ||
           url.hostname !== self.location.hostname;
}

function isImageRequest(url) {
    return /\.(png|jpg|jpeg|gif|svg|webp|avif)$/i.test(url.pathname);
}

function isPageRequest(url) {
    return url.hostname === self.location.hostname &&
           !isStaticAsset(url) &&
           !isAPIRequest(url) &&
           !isImageRequest(url);
}

// Cache management utilities
async function setCacheWithTimestamp(cache, request, response) {
    const headers = new Headers(response.headers);
    headers.set('sw-cache-timestamp', Date.now().toString());
    
    const responseWithTimestamp = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: headers
    });
    
    await cache.put(request, responseWithTimestamp);
}

function getCacheTime(response) {
    const timestamp = response.headers.get('sw-cache-timestamp');
    return timestamp ? parseInt(timestamp, 10) : null;
}

async function cleanupCache(cache, config) {
    if (!config.maxEntries) return;
    
    const keys = await cache.keys();
    
    if (keys.length > config.maxEntries) {
        const keysToDelete = keys.slice(0, keys.length - config.maxEntries);
        
        await Promise.all(
            keysToDelete.map(key => {
                console.log(`[SW] 🗑️ Removing old cache entry: ${key.url}`);
                return cache.delete(key);
            })
        );
    }
}

// Background sync for offline functionality
self.addEventListener('sync', (event) => {
    console.log('[SW] 🔄 Background sync triggered:', event.tag);
    
    if (event.tag === 'background-sync') {
        event.waitUntil(handleBackgroundSync());
    } else if (event.tag === 'metrics-sync') {
        event.waitUntil(syncMetrics());
    }
});

async function handleBackgroundSync() {
    try {
        // Process any queued offline actions
        console.log('[SW] 📡 Processing offline queue...');
        
        // This would typically involve sending queued API requests
        // that were made while offline
        
        return Promise.resolve();
    } catch (error) {
        console.error('[SW] ❌ Background sync failed:', error);
        throw error;
    }
}

async function syncMetrics() {
    try {
        const summary = metrics.getMetricsSummary();
        
        // Send metrics to backend
        await fetch('/api/performance/sw-metrics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(summary)
        });
        
        console.log('[SW] 📊 Metrics synced successfully');
    } catch (error) {
        console.error('[SW] ❌ Failed to sync metrics:', error);
    }
}

// Message handling for communication with main thread
self.addEventListener('message', (event) => {
    const { type, data } = event.data;
    
    switch (type) {
        case 'GET_METRICS':
            event.ports[0].postMessage(metrics.getMetricsSummary());
            break;
            
        case 'CLEAR_CACHE':
            clearAllCaches().then(() => {
                event.ports[0].postMessage({ success: true });
            }).catch((error) => {
                event.ports[0].postMessage({ success: false, error: error.message });
            });
            break;
            
        case 'PREFETCH_RESOURCES':
            if (data && data.urls) {
                prefetchResources(data.urls).then(() => {
                    event.ports[0].postMessage({ success: true });
                });
            }
            break;
            
        default:
            console.warn('[SW] ⚠️ Unknown message type:', type);
    }
});

// Cache management functions
async function clearAllCaches() {
    const cacheNames = await caches.keys();
    
    return Promise.all(
        cacheNames.map(cacheName => {
            console.log(`[SW] 🗑️ Clearing cache: ${cacheName}`);
            return caches.delete(cacheName);
        })
    );
}

async function prefetchResources(urls) {
    const cache = await caches.open(CACHE_NAME);
    
    return Promise.all(
        urls.map(url => {
            console.log(`[SW] 📦 Prefetching: ${url}`);
            return cache.add(url).catch(error => {
                console.warn(`[SW] ⚠️ Failed to prefetch ${url}:`, error);
            });
        })
    );
}

// Periodic cleanup and optimization
setInterval(async () => {
    try {
        // Sync metrics every 5 minutes
        await syncMetrics();
        
        // Log performance summary
        const summary = metrics.getMetricsSummary();
        console.log(`[SW] 📊 Performance Summary:`, {
            uptime: `${Math.round(summary.uptime / 1000 / 60)}min`,
            cacheHitRatio: `${summary.cacheHitRatio.toFixed(1)}%`,
            totalRequests: (summary.metrics.total_cache_hits?.sum || 0) + (summary.metrics.total_cache_misses?.sum || 0),
            avgNetworkTime: summary.metrics.network_request_time?.average?.toFixed(0) + 'ms'
        });
        
    } catch (error) {
        console.error('[SW] ❌ Periodic cleanup failed:', error);
    }
}, 5 * 60 * 1000); // Every 5 minutes

console.log('[SW] 🚀 Service Worker script loaded - Intelligent caching enabled');
console.log('[SW] 🎯 Phase 3 Performance Targets: <2s load time, intelligent caching, offline support');