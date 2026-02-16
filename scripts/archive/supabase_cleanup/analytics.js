/**
 * Analytics System
 * Tracks user interactions and measures success criteria from README
 */

class Analytics {
    static sessionId = null;
    static events = [];
    static startTime = Date.now();

    static init() {
        this.sessionId = this.generateSessionId();
        this.trackPageLoad();
        this.setupPerformanceTracking();
    }

    static generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    static trackEvent(eventType, data = {}) {
        const event = {
            sessionId: this.sessionId,
            eventType,
            timestamp: Date.now(),
            timeFromStart: Date.now() - this.startTime,
            url: window.location.href,
            userAgent: navigator.userAgent,
            ...data
        };

        this.events.push(event);

        // Store in localStorage for persistence
        this.saveToStorage();

        // Log for debugging
        console.log('Analytics Event:', event);

        // Check success criteria
        this.checkSuccessCriteria(event);
    }

    static trackPageLoad() {
        this.trackEvent('page_load', {
            pageTitle: document.title,
            referrer: document.referrer,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            }
        });
    }

    static setupPerformanceTracking() {
        // Track page performance
        window.addEventListener('load', () => {
            setTimeout(() => {
                const perfData = performance.getEntriesByType('navigation')[0];
                this.trackEvent('performance', {
                    loadTime: perfData.loadEventEnd - perfData.loadEventStart,
                    domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
                    networkTime: perfData.responseEnd - perfData.requestStart
                });
            }, 0);
        });

        // Track user engagement time
        let engagementStart = Date.now();
        let isEngaged = true;

        // Track when user becomes inactive
        ['blur', 'hidden'].forEach(event => {
            document.addEventListener(event, () => {
                if (isEngaged) {
                    this.trackEvent('engagement_pause', {
                        engagementDuration: Date.now() - engagementStart
                    });
                    isEngaged = false;
                }
            });
        });

        // Track when user becomes active again
        ['focus', 'visible'].forEach(event => {
            document.addEventListener(event, () => {
                if (!isEngaged) {
                    engagementStart = Date.now();
                    this.trackEvent('engagement_resume');
                    isEngaged = true;
                }
            });
        });
    }

    static checkSuccessCriteria(event) {
        // Phase 1 Success Criteria from README:
        // - User Engagement: 80%+ of visitors interact with agent recommendation
        // - Confidence Building: 90%+ positive feedback on first interaction
        // - Value Clarity: Users can explain the benefit in their own words
        // - Conversion Intent: 40%+ express interest in next steps

        switch (event.eventType) {
            case 'task_input':
                this.trackEvent('success_metric', {
                    metric: 'user_engagement',
                    achieved: true,
                    note: 'User interacted with agent recommendation system'
                });
                break;

            case 'agent_selected':
                this.trackEvent('success_metric', {
                    metric: 'conversion_intent',
                    achieved: true,
                    note: 'User showed interest in specific agent'
                });
                break;

            case 'recommendation_viewed':
                this.trackEvent('success_metric', {
                    metric: 'value_clarity',
                    achieved: true,
                    note: 'User viewed agent recommendations and benefits'
                });
                break;
        }
    }

    static getSessionStats() {
        const events = this.events;
        const sessionDuration = Date.now() - this.startTime;

        return {
            sessionId: this.sessionId,
            sessionDuration,
            totalEvents: events.length,
            eventTypes: [...new Set(events.map(e => e.eventType))],
            userEngagement: {
                taskInputs: events.filter(e => e.eventType === 'task_input').length,
                agentSelections: events.filter(e => e.eventType === 'agent_selected').length,
                recommendationsViewed: events.filter(e => e.eventType === 'recommendation_viewed').length
            },
            successMetrics: events.filter(e => e.eventType === 'success_metric'),
            timeToFirstInteraction: this.getTimeToFirstInteraction(),
            bounceRate: this.calculateBounceRate()
        };
    }

    static getTimeToFirstInteraction() {
        const firstInteraction = this.events.find(e =>
            ['task_input', 'agent_selected'].includes(e.eventType)
        );
        return firstInteraction ? firstInteraction.timeFromStart : null;
    }

    static calculateBounceRate() {
        // Consider it a bounce if user doesn't interact within 30 seconds
        const interactions = this.events.filter(e =>
            ['task_input', 'agent_selected'].includes(e.eventType)
        );
        return interactions.length === 0 && (Date.now() - this.startTime) > 30000;
    }

    static saveToStorage() {
        try {
            localStorage.setItem('analytics_events', JSON.stringify({
                sessionId: this.sessionId,
                events: this.events,
                startTime: this.startTime
            }));
        } catch (error) {
            console.warn('Failed to save analytics to localStorage:', error);
        }
    }

    static loadFromStorage() {
        try {
            const data = localStorage.getItem('analytics_events');
            if (data) {
                const parsed = JSON.parse(data);
                this.sessionId = parsed.sessionId;
                this.events = parsed.events || [];
                this.startTime = parsed.startTime || Date.now();
            }
        } catch (error) {
            console.warn('Failed to load analytics from localStorage:', error);
        }
    }

    static exportData() {
        const stats = this.getSessionStats();
        const blob = new Blob([JSON.stringify(stats, null, 2)], {
            type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analytics_${this.sessionId}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    static getPhase1Metrics() {
        // Calculate Phase 1 success criteria
        const events = this.events;
        const totalSessions = 1; // For demo, assume 1 session

        const userEngagementRate = events.filter(e => e.eventType === 'task_input').length > 0 ? 100 : 0;
        const conversionIntentRate = events.filter(e => e.eventType === 'agent_selected').length > 0 ? 100 : 0;
        const valueClarityRate = events.filter(e => e.eventType === 'recommendation_viewed').length > 0 ? 100 : 0;

        return {
            userEngagement: {
                current: userEngagementRate,
                target: 80,
                status: userEngagementRate >= 80 ? 'PASS' : 'FAIL'
            },
            conversionIntent: {
                current: conversionIntentRate,
                target: 40,
                status: conversionIntentRate >= 40 ? 'PASS' : 'FAIL'
            },
            valueClarity: {
                current: valueClarityRate,
                target: 70, // Estimated target
                status: valueClarityRate >= 70 ? 'PASS' : 'FAIL'
            },
            timeToValue: this.getTimeToFirstInteraction()
        };
    }
}

// Initialize analytics on page load
document.addEventListener('DOMContentLoaded', () => {
    Analytics.init();
});

// Track when user views recommendations
document.addEventListener('DOMContentLoaded', () => {
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList') {
                const recommendationsDiv = document.getElementById('recommendations');
                if (recommendationsDiv && recommendationsDiv.style.display !== 'none') {
                    Analytics.trackEvent('recommendation_viewed', {
                        timestamp: Date.now(),
                        hasResults: document.getElementById('agentList').children.length > 0
                    });
                }
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

// Expose analytics for debugging
window.Analytics = Analytics;