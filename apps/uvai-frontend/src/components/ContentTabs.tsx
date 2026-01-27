import { useState } from 'react';
import './ContentTabs.css';
import type { VideoAnalysis } from '@/lib/api';

interface ContentTabsProps {
  analysis: VideoAnalysis;
}

type TabId = 'summary' | 'actions' | 'transcript' | 'data';

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'summary', label: 'Summary', icon: '📋' },
  { id: 'actions', label: 'Actions', icon: '⚡' },
  { id: 'transcript', label: 'Transcript', icon: '📝' },
  { id: 'data', label: 'Data', icon: '{ }' },
];

export default function ContentTabs({ analysis }: ContentTabsProps) {
  const [activeTab, setActiveTab] = useState<TabId>('summary');

  const renderTabContent = () => {
    switch (activeTab) {
      case 'summary':
        return (
          <div className="tab-content animate-fade-in">
            <h2 className="content-title">Video Summary</h2>
            {analysis.summary ? (
              <p className="summary-text">{analysis.summary}</p>
            ) : (
              <p className="summary-text">
                {analysis.transcript?.slice(0, 500)}...
              </p>
            )}

            {analysis.key_insights && analysis.key_insights.length > 0 && (
              <div className="insights-section">
                <h3>Key Insights</h3>
                <ul className="insights-list">
                  {analysis.key_insights.map((insight, index) => (
                    <li key={index} className="insight-item">
                      <span className="insight-icon">💡</span>
                      {insight}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.timestamps && analysis.timestamps.length > 0 && (
              <div className="timestamps-section">
                <h3>Key Moments</h3>
                <div className="timestamps-list">
                  {analysis.timestamps.map((ts, index) => (
                    <div key={index} className="timestamp-item">
                      <span className="timestamp-time">
                        {Math.floor(ts.time / 60)}:{String(ts.time % 60).padStart(2, '0')}
                      </span>
                      <span className="timestamp-label">{ts.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      case 'actions':
        return (
          <div className="tab-content animate-fade-in">
            <h2 className="content-title">Action Items</h2>
            {analysis.action_items && analysis.action_items.length > 0 ? (
              <div className="actions-list">
                {analysis.action_items.map((action) => (
                  <div key={action.id} className={`action-card priority-${action.priority}`}>
                    <div className="action-header">
                      <span className={`priority-badge ${action.priority}`}>
                        {action.priority}
                      </span>
                      <span className={`status-badge ${action.status}`}>
                        {action.status.replace('_', ' ')}
                      </span>
                    </div>
                    <h4 className="action-title">{action.title}</h4>
                    <p className="action-description">{action.description}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <p>No action items detected for this video.</p>
              </div>
            )}
          </div>
        );

      case 'transcript':
        return (
          <div className="tab-content animate-fade-in">
            <h2 className="content-title">Full Transcript</h2>
            <div className="transcript-container">
              <pre className="transcript-text">{analysis.transcript || 'No transcript available.'}</pre>
            </div>
          </div>
        );

      case 'data':
        return (
          <div className="tab-content animate-fade-in">
            <h2 className="content-title">Raw Data</h2>
            <div className="data-container">
              <pre className="data-json">
                {JSON.stringify(analysis, null, 2)}
              </pre>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="content-tabs">
      <div className="tabs-header">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span className="tab-label">{tab.label}</span>
          </button>
        ))}
      </div>
      <div className="tabs-body">
        {renderTabContent()}
      </div>
    </div>
  );
}
