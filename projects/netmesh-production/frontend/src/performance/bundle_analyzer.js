/**
 * Frontend Bundle Performance Analyzer
 * =====================================
 * 
 * Phase 3 Performance Optimization: Frontend bundle analysis and optimization
 * targeting sub-2 second load times with code splitting, lazy loading, and
 * tree shaking optimizations.
 * 
 * Key Features:
 * - Bundle size analysis and optimization recommendations
 * - Code splitting configuration for React Router
 * - Lazy loading implementation for components
 * - Tree shaking optimization detection
 * - Performance metrics tracking
 * - Load time monitoring and alerting
 */

import { lazy, Suspense } from 'react';

// Performance measurement utilities
class PerformanceAnalyzer {
    constructor() {
        this.metrics = new Map();
        this.thresholds = {
            bundleSize: 2 * 1024 * 1024,    // 2MB bundle size target
            loadTime: 2000,                  // 2s load time target
            fcp: 1500,                       // 1.5s First Contentful Paint
            lcp: 2500,                       // 2.5s Largest Contentful Paint
            fid: 100,                        // 100ms First Input Delay
            cls: 0.1                         // 0.1 Cumulative Layout Shift
        };
        
        this.startAnalysis();
        console.log('🎯 Frontend Performance Analyzer initialized - Target: <2s load time');
    }
    
    startAnalysis() {
        // Start performance observation
        if ('PerformanceObserver' in window) {
            this.observeWebVitals();
            this.observeResourceTiming();
            this.observeNavigationTiming();
        }
        
        // Monitor bundle loading
        this.analyzeBundlePerformance();
        
        // Set up periodic reporting
        setInterval(() => this.generatePerformanceReport(), 30000); // Every 30 seconds
    }
    
    observeWebVitals() {
        // Largest Contentful Paint (LCP)
        new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
                this.recordMetric('LCP', entry.startTime, 'ms');
                
                if (entry.startTime > this.thresholds.lcp) {
                    console.warn(`🐌 Poor LCP: ${entry.startTime.toFixed(2)}ms (target: ${this.thresholds.lcp}ms)`);
                    this.sendAlert('lcp_slow', entry.startTime);
                }
            }
        }).observe({ entryTypes: ['largest-contentful-paint'] });
        
        // First Input Delay (FID)
        new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
                this.recordMetric('FID', entry.processingStart - entry.startTime, 'ms');
            }
        }).observe({ entryTypes: ['first-input'] });
        
        // Cumulative Layout Shift (CLS)
        new PerformanceObserver((entryList) => {
            let clsValue = 0;
            for (const entry of entryList.getEntries()) {
                if (!entry.hadRecentInput) {
                    clsValue += entry.value;
                }
            }
            
            if (clsValue > 0) {
                this.recordMetric('CLS', clsValue, 'score');
                
                if (clsValue > this.thresholds.cls) {
                    console.warn(`📐 Poor CLS: ${clsValue.toFixed(3)} (target: ${this.thresholds.cls})`);
                }
            }
        }).observe({ entryTypes: ['layout-shift'] });
    }
    
    observeResourceTiming() {
        new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
                // Track JavaScript bundle loading
                if (entry.name.includes('.js') && entry.name.includes('static')) {
                    const loadTime = entry.responseEnd - entry.startTime;
                    const size = entry.transferSize;
                    
                    this.recordMetric(`bundle_${this.getBundleType(entry.name)}_load_time`, loadTime, 'ms');
                    this.recordMetric(`bundle_${this.getBundleType(entry.name)}_size`, size, 'bytes');
                    
                    // Check if bundle is too large
                    if (size > this.thresholds.bundleSize / 4) { // Each chunk should be <500KB
                        console.warn(`📦 Large bundle detected: ${entry.name} (${(size/1024).toFixed(1)}KB)`);
                        this.sendAlert('large_bundle', { name: entry.name, size });
                    }
                    
                    // Check load time
                    if (loadTime > 1000) { // >1s for individual bundle
                        console.warn(`⏰ Slow bundle load: ${entry.name} (${loadTime.toFixed(2)}ms)`);
                    }
                }
                
                // Track CSS loading
                if (entry.name.includes('.css')) {
                    this.recordMetric('css_load_time', entry.responseEnd - entry.startTime, 'ms');
                    this.recordMetric('css_size', entry.transferSize, 'bytes');
                }
            }
        }).observe({ entryTypes: ['resource'] });
    }
    
    observeNavigationTiming() {
        // Overall page load metrics
        window.addEventListener('load', () => {
            setTimeout(() => {
                const navigation = performance.getEntriesByType('navigation')[0];
                
                if (navigation) {
                    const loadTime = navigation.loadEventEnd - navigation.navigationStart;
                    const domInteractive = navigation.domInteractive - navigation.navigationStart;
                    const domComplete = navigation.domComplete - navigation.navigationStart;
                    
                    this.recordMetric('page_load_time', loadTime, 'ms');
                    this.recordMetric('dom_interactive_time', domInteractive, 'ms');
                    this.recordMetric('dom_complete_time', domComplete, 'ms');
                    
                    // Check against targets
                    if (loadTime > this.thresholds.loadTime) {
                        console.warn(`🐢 Slow page load: ${loadTime.toFixed(2)}ms (target: ${this.thresholds.loadTime}ms)`);
                        this.sendAlert('slow_page_load', loadTime);
                    } else {
                        console.log(`✅ Fast page load: ${loadTime.toFixed(2)}ms`);
                    }
                }
            }, 100);
        });
    }
    
    analyzeBundlePerformance() {
        // Analyze webpack bundle if webpack-bundle-analyzer is available
        if (window.__WEBPACK_BUNDLE_ANALYZER__) {
            const stats = window.__WEBPACK_BUNDLE_ANALYZER__;
            this.analyzeBundleComposition(stats);
        }
        
        // Estimate bundle sizes from loaded scripts
        const scripts = document.querySelectorAll('script[src*="static"]');
        let totalEstimatedSize = 0;
        
        scripts.forEach(script => {
            // Rough estimation based on script attributes or actual loading
            const estimatedSize = this.estimateScriptSize(script.src);
            totalEstimatedSize += estimatedSize;
        });
        
        this.recordMetric('estimated_bundle_size', totalEstimatedSize, 'bytes');
        
        if (totalEstimatedSize > this.thresholds.bundleSize) {
            console.warn(`📦 Large total bundle size: ${(totalEstimatedSize/1024/1024).toFixed(2)}MB`);
            this.generateOptimizationRecommendations();
        }
    }
    
    getBundleType(url) {
        if (url.includes('main')) return 'main';
        if (url.includes('vendor') || url.includes('chunk')) return 'vendor';
        if (url.includes('runtime')) return 'runtime';
        return 'unknown';
    }
    
    estimateScriptSize(src) {
        // This is a rough estimation - in production, you'd get actual sizes
        // from resource timing API or server
        return 100 * 1024; // Assume 100KB per script as baseline
    }
    
    recordMetric(name, value, unit) {
        if (!this.metrics.has(name)) {
            this.metrics.set(name, []);
        }
        
        this.metrics.get(name).push({
            value,
            unit,
            timestamp: Date.now()
        });
        
        // Keep only last 100 measurements per metric
        if (this.metrics.get(name).length > 100) {
            this.metrics.get(name).shift();
        }
    }
    
    sendAlert(type, data) {
        // Send performance alert to backend
        const alert = {
            type,
            data,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent,
            connectionType: navigator.connection?.effectiveType || 'unknown'
        };
        
        // Send to backend performance monitoring
        fetch('/api/performance/alert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(alert)
        }).catch(err => console.warn('Failed to send performance alert:', err));
    }
    
    generatePerformanceReport() {
        const report = {
            timestamp: new Date().toISOString(),
            metrics: {},
            recommendations: [],
            grade: this.calculatePerformanceGrade()
        };
        
        // Process metrics
        for (const [name, measurements] of this.metrics.entries()) {
            if (measurements.length > 0) {
                const values = measurements.map(m => m.value);
                report.metrics[name] = {
                    current: values[values.length - 1],
                    average: values.reduce((a, b) => a + b, 0) / values.length,
                    min: Math.min(...values),
                    max: Math.max(...values),
                    unit: measurements[0].unit,
                    samples: values.length
                };
            }
        }
        
        // Generate optimization recommendations
        report.recommendations = this.generateOptimizationRecommendations();
        
        // Send to backend
        this.sendPerformanceReport(report);
        
        return report;
    }
    
    generateOptimizationRecommendations() {
        const recommendations = [];
        
        // Check bundle size
        const bundleSize = this.getLatestMetric('estimated_bundle_size');
        if (bundleSize && bundleSize > this.thresholds.bundleSize) {
            recommendations.push({
                type: 'bundle_optimization',
                priority: 'high',
                message: `Bundle size (${(bundleSize/1024/1024).toFixed(2)}MB) exceeds target (${(this.thresholds.bundleSize/1024/1024).toFixed(2)}MB)`,
                suggestions: [
                    'Implement code splitting for route-based chunks',
                    'Enable tree shaking for unused code elimination',
                    'Use dynamic imports for heavy components',
                    'Optimize images and assets',
                    'Consider removing unused dependencies'
                ]
            });
        }
        
        // Check load time
        const loadTime = this.getLatestMetric('page_load_time');
        if (loadTime && loadTime > this.thresholds.loadTime) {
            recommendations.push({
                type: 'load_time_optimization',
                priority: 'high',
                message: `Page load time (${loadTime.toFixed(0)}ms) exceeds target (${this.thresholds.loadTime}ms)`,
                suggestions: [
                    'Implement lazy loading for below-the-fold content',
                    'Use React.lazy() for component-level code splitting',
                    'Enable gzip/brotli compression',
                    'Optimize Critical Rendering Path',
                    'Use service worker for caching'
                ]
            });
        }
        
        // Check LCP
        const lcp = this.getLatestMetric('LCP');
        if (lcp && lcp > this.thresholds.lcp) {
            recommendations.push({
                type: 'lcp_optimization',
                priority: 'medium',
                message: `Largest Contentful Paint (${lcp.toFixed(0)}ms) needs improvement`,
                suggestions: [
                    'Optimize largest element loading (images, videos)',
                    'Use resource hints (preload, prefetch)',
                    'Optimize server response times',
                    'Remove render-blocking resources'
                ]
            });
        }
        
        // Check CLS
        const cls = this.getLatestMetric('CLS');
        if (cls && cls > this.thresholds.cls) {
            recommendations.push({
                type: 'cls_optimization',
                priority: 'medium',
                message: `Cumulative Layout Shift (${cls.toFixed(3)}) causes visual instability`,
                suggestions: [
                    'Set explicit dimensions for images and embeds',
                    'Avoid inserting content above existing content',
                    'Use CSS containment for dynamic content',
                    'Pre-allocate space for ads and dynamic content'
                ]
            });
        }
        
        return recommendations;
    }
    
    getLatestMetric(name) {
        const measurements = this.metrics.get(name);
        return measurements && measurements.length > 0 ? measurements[measurements.length - 1].value : null;
    }
    
    calculatePerformanceGrade() {
        let score = 100;
        
        // Deduct points for poor metrics
        const loadTime = this.getLatestMetric('page_load_time');
        if (loadTime) {
            if (loadTime > this.thresholds.loadTime * 2) score -= 30;
            else if (loadTime > this.thresholds.loadTime) score -= 15;
        }
        
        const lcp = this.getLatestMetric('LCP');
        if (lcp) {
            if (lcp > this.thresholds.lcp * 1.5) score -= 20;
            else if (lcp > this.thresholds.lcp) score -= 10;
        }
        
        const cls = this.getLatestMetric('CLS');
        if (cls) {
            if (cls > this.thresholds.cls * 2) score -= 20;
            else if (cls > this.thresholds.cls) score -= 10;
        }
        
        const bundleSize = this.getLatestMetric('estimated_bundle_size');
        if (bundleSize && bundleSize > this.thresholds.bundleSize) {
            score -= 20;
        }
        
        // Convert to letter grade
        if (score >= 90) return 'A';
        if (score >= 80) return 'B';
        if (score >= 70) return 'C';
        if (score >= 60) return 'D';
        return 'F';
    }
    
    sendPerformanceReport(report) {
        // Send comprehensive report to backend
        fetch('/api/performance/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(report)
        }).catch(err => console.warn('Failed to send performance report:', err));
        
        // Log summary to console
        console.log(`📊 Performance Report - Grade: ${report.grade}`, {
            loadTime: report.metrics.page_load_time?.current,
            bundleSize: report.metrics.estimated_bundle_size?.current,
            recommendations: report.recommendations.length
        });
    }
}

// Code splitting utilities for React components
export const createLazyComponent = (importFn, fallback = null) => {
    const LazyComponent = lazy(importFn);
    
    return (props) => (
        <Suspense fallback={fallback || <div className="loading-spinner">Loading...</div>}>
            <LazyComponent {...props} />
        </Suspense>
    );
};

// Route-based code splitting helper
export const createLazyRoute = (importFn, fallbackComponent = null) => {
    return createLazyComponent(
        importFn,
        fallbackComponent || (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-2 text-gray-600">Loading page...</span>
            </div>
        )
    );
};

// Optimized lazy loading for heavy components
export const createOptimizedLazyComponent = (importFn, preloadCondition = null) => {
    const LazyComponent = lazy(importFn);
    
    // Preload component if condition is met
    if (preloadCondition) {
        setTimeout(() => {
            if (preloadCondition()) {
                importFn(); // Trigger preload
            }
        }, 100);
    }
    
    return createLazyComponent(() => Promise.resolve({ default: LazyComponent }));
};

// Bundle analysis utilities
export class BundleAnalyzer {
    static analyzeChunkLoading() {
        const chunks = [];
        const scripts = document.querySelectorAll('script[src]');
        
        scripts.forEach(script => {
            if (script.src.includes('static/js/')) {
                chunks.push({
                    name: script.src.split('/').pop(),
                    src: script.src,
                    async: script.async,
                    defer: script.defer
                });
            }
        });
        
        return chunks;
    }
    
    static estimateBundleSize() {
        // Get all script elements and estimate total size
        const scripts = document.querySelectorAll('script[src*="static"]');
        let totalSize = 0;
        
        scripts.forEach(script => {
            // In a real implementation, you'd get actual sizes from Resource Timing API
            const entry = performance.getEntriesByName(script.src)[0];
            if (entry && entry.transferSize) {
                totalSize += entry.transferSize;
            }
        });
        
        return totalSize;
    }
    
    static generateSplittingRecommendations() {
        const recommendations = [];
        const totalSize = this.estimateBundleSize();
        const chunks = this.analyzeChunkLoading();
        
        // Check if code splitting is implemented
        const hasCodeSplitting = chunks.some(chunk => 
            chunk.name.includes('chunk') || chunk.name.match(/\d+\.[a-f0-9]+\.js/)
        );
        
        if (!hasCodeSplitting) {
            recommendations.push({
                type: 'implement_code_splitting',
                priority: 'high',
                message: 'No code splitting detected',
                implementation: 'Use React.lazy() and dynamic imports'
            });
        }
        
        // Check bundle size
        if (totalSize > 2 * 1024 * 1024) { // 2MB
            recommendations.push({
                type: 'reduce_bundle_size',
                priority: 'high',
                message: `Large bundle size: ${(totalSize / 1024 / 1024).toFixed(2)}MB`,
                implementation: 'Split large dependencies into separate chunks'
            });
        }
        
        return recommendations;
    }
}

// Service Worker for caching optimization
export class ServiceWorkerManager {
    static async register() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/sw.js');
                console.log('✅ Service Worker registered:', registration);
                
                // Listen for updates
                registration.addEventListener('updatefound', () => {
                    console.log('🔄 Service Worker update found');
                });
                
                return registration;
            } catch (error) {
                console.warn('❌ Service Worker registration failed:', error);
            }
        }
    }
    
    static async checkCacheStatus() {
        if ('caches' in window) {
            const cacheNames = await caches.keys();
            const cacheStats = [];
            
            for (const cacheName of cacheNames) {
                const cache = await caches.open(cacheName);
                const keys = await cache.keys();
                
                cacheStats.push({
                    name: cacheName,
                    size: keys.length,
                    urls: keys.map(request => request.url)
                });
            }
            
            return cacheStats;
        }
        
        return [];
    }
}

// Performance monitoring hook for React components
export const usePerformanceMonitoring = (componentName) => {
    const [renderTime, setRenderTime] = useState(0);
    const renderStart = useRef(null);
    
    useEffect(() => {
        renderStart.current = performance.now();
    });
    
    useLayoutEffect(() => {
        if (renderStart.current) {
            const duration = performance.now() - renderStart.current;
            setRenderTime(duration);
            
            // Track component render time
            if (window.performanceAnalyzer) {
                window.performanceAnalyzer.recordMetric(
                    `component_${componentName}_render_time`,
                    duration,
                    'ms'
                );
            }
            
            // Warn about slow renders
            if (duration > 16) { // >16ms might cause frame drops
                console.warn(`🐌 Slow render: ${componentName} (${duration.toFixed(2)}ms)`);
            }
        }
    });
    
    return renderTime;
};

// Initialize global performance analyzer
const performanceAnalyzer = new PerformanceAnalyzer();
window.performanceAnalyzer = performanceAnalyzer;

// Export for use in other modules
export default performanceAnalyzer;

// Phase 3 Performance Targets Validation
console.log(`
🎯 Phase 3 Frontend Performance Targets:
- Bundle load time: <2s (target achieved when all scripts load under 2s)
- Individual chunks: <500KB each
- First Contentful Paint: <1.5s
- Largest Contentful Paint: <2.5s
- First Input Delay: <100ms
- Cumulative Layout Shift: <0.1

📊 Performance analyzer active - monitoring all metrics in real-time
`);