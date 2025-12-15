import React, { useState, useEffect } from 'react';

interface SecurityEvent {
  id: string;
  type: 'auth_failure' | 'suspicious_activity' | 'data_breach_attempt' | 'api_abuse' | 'unauthorized_access';
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  source: string;
  timestamp: Date;
  resolved: boolean;
  actions: string[];
}

interface SecurityMetrics {
  totalEvents: number;
  criticalEvents: number;
  resolvedEvents: number;
  avgResponseTime: number;
  securityScore: number;
  activeThreats: number;
}

export function SecurityPanel() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<SecurityEvent | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');

  useEffect(() => {
    const generateMockEvents = () => {
      const eventTypes: SecurityEvent['type'][] = ['auth_failure', 'suspicious_activity', 'data_breach_attempt', 'api_abuse', 'unauthorized_access'];
      const severities: SecurityEvent['severity'][] = ['low', 'medium', 'high', 'critical'];

      const mockEvents: SecurityEvent[] = Array.from({ length: 20 }, (_, i) => {
        const type = eventTypes[Math.floor(Math.random() * eventTypes.length)];
        const severity = severities[Math.floor(Math.random() * severities.length)];

        return {
          id: `sec-${i + 1}`,
          type,
          severity,
          description: getEventDescription(type),
          source: `192.168.1.${Math.floor(Math.random() * 255)}`,
          timestamp: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000),
          resolved: Math.random() > 0.6,
          actions: getEventActions(type)
        };
      });

      setEvents(mockEvents.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()));
      setIsLoading(false);
    };

    generateMockEvents();

    // Update every 15 seconds
    const interval = setInterval(generateMockEvents, 15000);
    return () => clearInterval(interval);
  }, []);

  const getEventDescription = (type: string): string => {
    const descriptions = {
      auth_failure: 'Failed authentication attempt from unknown IP',
      suspicious_activity: 'Unusual API usage pattern detected',
      data_breach_attempt: 'Potential data exfiltration attempt blocked',
      api_abuse: 'Rate limit exceeded on API endpoints',
      unauthorized_access: 'Access attempt to restricted resource'
    };
    return descriptions[type as keyof typeof descriptions] || 'Security event detected';
  };

  const getEventActions = (type: string): string[] => {
    const actions = {
      auth_failure: ['IP blocked temporarily', 'User notified', 'Additional verification required'],
      suspicious_activity: ['Traffic analysis initiated', 'Account flagged for review'],
      data_breach_attempt: ['Connection terminated', 'Data access logged', 'Security team alerted'],
      api_abuse: ['Rate limiting applied', 'API key flagged', 'Usage monitoring increased'],
      unauthorized_access: ['Access denied', 'Audit log created', 'Permission review triggered']
    };
    return actions[type as keyof typeof actions] || ['Event logged', 'Monitoring increased'];
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900';
      case 'high':
        return 'text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900';
      case 'low':
        return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900';
      default:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900';
    }
  };

  const getEventTypeIcon = (type: string) => {
    switch (type) {
      case 'auth_failure':
        return '🔐';
      case 'suspicious_activity':
        return '👁️';
      case 'data_breach_attempt':
        return '🚨';
      case 'api_abuse':
        return '⚡';
      case 'unauthorized_access':
        return '🚫';
      default:
        return '⚠️';
    }
  };

  const filteredEvents = events.filter(event =>
    filter === 'all' || event.severity === filter
  );

  const metrics: SecurityMetrics = {
    totalEvents: events.length,
    criticalEvents: events.filter(e => e.severity === 'critical').length,
    resolvedEvents: events.filter(e => e.resolved).length,
    avgResponseTime: Math.floor(Math.random() * 300) + 60, // seconds
    securityScore: Math.floor(85 + Math.random() * 10), // 85-95
    activeThreats: events.filter(e => !e.resolved && (e.severity === 'high' || e.severity === 'critical')).length
  };

  const handleResolve = (event: SecurityEvent) => {
    console.log('Resolving security event:', event.id);
    // Implementation would resolve the security event
  };

  const handleInvestigate = (event: SecurityEvent) => {
    console.log('Investigating security event:', event.id);
    // Implementation would start investigation
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm animate-pulse">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
              <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
            </div>
          ))}
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm animate-pulse">
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Security Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <span className="text-2xl">🛡️</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Security Score</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{metrics.securityScore}/100</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-red-100 dark:bg-red-900 rounded-lg">
              <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Critical Events</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{metrics.criticalEvents}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
              <svg className="w-6 h-6 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Active Threats</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{metrics.activeThreats}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
              <svg className="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Resolved</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{metrics.resolvedEvents}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Security Events */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">Security Events</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">Monitor and respond to security incidents</p>
            </div>
            <div className="flex items-center space-x-4">
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as any)}
                className="rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="all">All Severity</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium">
                Security Settings
              </button>
            </div>
          </div>
        </div>

        {/* Events List */}
        <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-96 overflow-y-auto">
          {filteredEvents.map((event) => (
            <div key={event.id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="text-2xl">{getEventTypeIcon(event.type)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3">
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getSeverityColor(event.severity)}`}>
                        {event.severity.toUpperCase()}
                      </span>
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${event.resolved ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'}`}>
                        {event.resolved ? 'Resolved' : 'Active'}
                      </span>
                    </div>
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mt-1">
                      {event.description}
                    </h4>
                    <div className="flex items-center space-x-4 mt-1">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Source: {event.source}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {event.timestamp.toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="flex space-x-2">
                    {!event.resolved && (
                      <button
                        onClick={() => handleResolve(event)}
                        className="text-gray-400 hover:text-green-600 dark:hover:text-green-400 p-1"
                        title="Resolve Event"
                      >
                        ✅
                      </button>
                    )}
                    <button
                      onClick={() => handleInvestigate(event)}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                      title="Investigate"
                    >
                      🔍
                    </button>
                    <button
                      onClick={() => setSelectedEvent(event)}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                      title="View Details"
                    >
                      📋
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Event Details Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                {getEventTypeIcon(selectedEvent.type)} Security Event Details
              </h3>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Event ID</h4>
                  <p className="text-sm text-gray-900 dark:text-white font-mono">{selectedEvent.id}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Severity</h4>
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getSeverityColor(selectedEvent.severity)}`}>
                    {selectedEvent.severity.toUpperCase()}
                  </span>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Type</h4>
                  <p className="text-sm text-gray-900 dark:text-white">{selectedEvent.type.replace('_', ' ')}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Status</h4>
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${selectedEvent.resolved ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'}`}>
                    {selectedEvent.resolved ? 'Resolved' : 'Active'}
                  </span>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Description</h4>
                <p className="text-sm text-gray-900 dark:text-white">{selectedEvent.description}</p>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Source</h4>
                <p className="text-sm text-gray-900 dark:text-white font-mono">{selectedEvent.source}</p>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Timestamp</h4>
                <p className="text-sm text-gray-900 dark:text-white">{selectedEvent.timestamp.toLocaleString()}</p>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Actions Taken</h4>
                <div className="space-y-2">
                  {selectedEvent.actions.map((action, index) => (
                    <div key={index} className="flex items-center space-x-2 text-sm text-gray-700 dark:text-gray-300">
                      <span className="text-green-500">✓</span>
                      <span>{action}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
