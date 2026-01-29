import React, { useState } from 'react';
import './HomeDashboard.css';

interface StatCardProps {
  label: string;
  value: string;
  trend: string;
  icon: string;
  glowColor: 'violet' | 'cyan';
}

const StatCard: React.FC<StatCardProps> = ({ label, value, trend, icon, glowColor }) => (
  <div className="stat-card">
    <div className="stat-icon-bg">
      <span className="material-symbols-outlined" style={{ fontSize: '48px' }}>{icon}</span>
    </div>
    <div className="stat-info">
      <p className="stat-label">{label}</p>
      <p className="stat-value">{value}</p>
    </div>
    <div className="stat-trend trend-up">
      <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>trending_up</span>
      <span>{trend}</span>
    </div>
    <div className={`stat-glow ${glowColor}`}></div>
  </div>
);

interface ActivityItemProps {
  title: string;
  status: 'processing' | 'completed' | 'failed';
  time: string;
  thumbnail: string;
  summary?: string;
  isProcessing?: boolean;
}

const ActivityItem: React.FC<ActivityItemProps> = ({ title, status, time, thumbnail, summary, isProcessing }) => (
  <div className="feed-item">
    {isProcessing && <div className="accent-bar"></div>}
    <div className="thumbnail-box">
      <div className="thumbnail-img" style={{ backgroundImage: `url(${thumbnail})` }}></div>
      <div className="status-overlay">
        {status === 'processing' ? (
          <span className="material-symbols-outlined spinner" style={{ fontSize: '24px', color: 'var(--color-accent-cyan)' }}>progress_activity</span>
        ) : status === 'completed' ? (
           <div className="absolute bottom-1 right-1 bg-black/60 px-1 py-0.5 rounded text-[10px] text-white font-mono" style={{ bottom: '4px', right: '4px', padding: '2px 4px', fontSize: '10px', background: 'rgba(0,0,0,0.6)', borderRadius: '4px' }}>04:12</div>
        ) : null}
      </div>
    </div>
    <div className="item-content">
      <h3 className="item-title">{title}</h3>
      <div className="item-meta">
        <span className={`status-badge badge-${status}`}>
          {status === 'processing' && <span className="dot dot-pulse"></span>}
          {status}
        </span>
        <span className="timestamp">{time}</span>
      </div>
      {summary && <p className="item-summary">{summary}</p>}
    </div>
    <button className="action-btn" style={{ height: '2rem', width: '2rem' }}>
      <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>
        {status === 'completed' ? 'file_download' : status === 'failed' ? 'refresh' : 'more_vert'}
      </span>
    </button>
  </div>
);

interface HomeDashboardProps {
  analysis: any | null;
  isLoading: boolean;
  loadingPhase: string;
  onNewAnalysis: () => void;
}

export default function HomeDashboard({ analysis, isLoading, loadingPhase, onNewAnalysis }: HomeDashboardProps) {
  const [activeTab, setActiveTab] = useState('Overview');

  return (
    <div className="home-dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <div className="profile-section">
            <div className="avatar-container">
              <div
                className="avatar"
                style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuC6-5RmOSYjpv-NngywZNr-UTESL_vYQmKb0k3T3r94mPu8oXEov0-NvoFgndA9-Bkgdwl-7BoBXriPncOkPpIDtXHF6c9bctKQDUlxfxlahyc0R_vnkyf7po111W82bPYbzNHZSRPJBxyr4pBKAsT5vzzR_qfAvPkQriVEH55Axl1pPbdh0QJ4vQtSPuGEFOc3FaMtoBCnWacFbUae1suo4g1-Q3ZMtPRYEQaSpnZF-HJZIdGVx81YdcdqyNQkdnGrkMvtBdBSaSg')" }}
              ></div>
              <div className="status-dot"></div>
            </div>
            <div className="brand-info">
              <h1>EventRelay</h1>
              <p>Dev Workspace</p>
            </div>
          </div>
          <div className="header-actions">
            <button className="action-btn">
              <span className="material-symbols-outlined">search</span>
            </button>
            <button className="action-btn" style={{ position: 'relative' }}>
              <span className="material-symbols-outlined">notifications</span>
              <span className="notification-badge"></span>
            </button>
          </div>
        </div>

        <div className="filter-chips">
          {['Overview', 'Last 24 Hours', 'All Sources', 'Errors Only'].map((tab) => (
            <button
              key={tab}
              className={`chip ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
              {(tab === 'Last 24 Hours' || tab === 'All Sources') && (
                <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>expand_more</span>
              )}
            </button>
          ))}
        </div>
      </header>

      <main className="dashboard-main">
        {isLoading ? (
          <div className="loading-overlay">
            <span className="material-symbols-outlined spinner" style={{ fontSize: '48px' }}>progress_activity</span>
            <p>{loadingPhase}...</p>
          </div>
        ) : (
          <>
            <section>
              <div className="section-header">
                <h2>Pipeline Stats</h2>
                <button className="view-all">View Report</button>
              </div>
              <div className="stats-grid">
                <StatCard
                  label="Videos Processed"
                  value={analysis?.stats?.processed || "1,248"}
                  trend="+12%"
                  icon="videocam"
                  glowColor="violet"
                />
                <StatCard
                  label="Events Detected"
                  value={analysis?.stats?.events || "85.2k"}
                  trend="+8%"
                  icon="center_focus_strong"
                  glowColor="cyan"
                />
              </div>
            </section>

            <section className="quota-card">
              <div className="quota-header">
                <div className="quota-label">
                  <span className="material-symbols-outlined" style={{ color: 'var(--color-accent-cyan)', fontSize: '20px' }}>api</span>
                  <p style={{ margin: 0, fontWeight: 500 }}>API Quota Usage</p>
                </div>
                <span className="percentage-badge">85%</span>
              </div>
              <div className="progress-container">
                <div className="progress-bar" style={{ width: '85%' }}></div>
              </div>
              <div className="quota-footer">
                <span>850 / 1000 calls</span>
                <span style={{ color: 'var(--color-accent-cyan)' }}>Resets in 4h</span>
              </div>
            </section>

            <section>
              <div className="section-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <h2>Recent Activity</h2>
                  <span style={{ backgroundColor: 'rgba(255,255,255,0.1)', padding: '2px 8px', borderRadius: '10px', fontSize: '12px', fontWeight: 'bold' }}>
                    {analysis ? '1' : '3'}
                  </span>
                </div>
                <button className="view-all" style={{ color: '#6b7280' }}>
                  <span className="material-symbols-outlined">tune</span>
                </button>
              </div>
              <div className="activity-feed">
                {analysis ? (
                  <ActivityItem
                    title={analysis.video_title || "Processed Video"}
                    status="completed"
                    time="Just now"
                    thumbnail={analysis.thumbnail || ""}
                    summary={analysis.summary || "Analysis complete"}
                  />
                ) : (
                  <>
                    <ActivityItem
                      title="Cam_04_Parking_Lot.mp4"
                      status="processing"
                      time="2m ago"
                      thumbnail="https://lh3.googleusercontent.com/aida-public/AB6AXuAZAFhATwmybILzjwpiip2g94HK3jiQ6xy0SFfx35Mm6XVxwEme7JkCdSThBlIvG1spg1NVkAILCe3vV4PjtFQaGcTu8ApODvOzIG11q9Bo23qCNMLRvwaFIHfuxeLU8zt-rQdLVgFNN0NNZmStO-B-pfABPRmaUrMdQoCwbKSp08rMiQTGApltO0Xd7RGU-lXd7gNYH1AurSnXBk3xdG1vuNRq8Wf5ggp65vv6b0rbsLFLyJxq1ZQkwqMLWhBquNLXYoOGJJ5rdfs"
                      isProcessing
                    />
                    <ActivityItem
                      title="Drone_Survey_B7.mov"
                      status="completed"
                      time="15m ago"
                      thumbnail="https://lh3.googleusercontent.com/aida-public/AB6AXuD6xBQqIkFB64vObboCz712LkoETyC6lGturoUYu1mmpVq8btesweK_k3cQ7zTjMF4sTmE_z1V2HeARM5q0-xwK64uKvftVS0YB6Ewv4Xqz7pZR6pqbC5A2-HjfVSlBLZ5UK8nZItkkoMnEP3sQiFgLAkcoDsaIWr7y4e01ifezqFUuoDQjjicZsBSZ1nNFTVQaeEqLAn0XHX5FimpUc58Ik20E-Pr5pDzbWgXJo2ZBoPRDyvv0NvoRTxBpzDWzCRCD-niYqpxPjso"
                      summary="Detected: 14 Objects (Vehicles)"
                    />
                  </>
                )}
              </div>
            </section>
          </>
        )}
      </main>

      <button className="fab" onClick={onNewAnalysis}>
        <span className="material-symbols-outlined">add</span>
      </button>

      <nav className="bottom-nav">
        <button className="nav-item active">
          <span className="material-symbols-outlined fill-current">home</span>
          <span>Home</span>
        </button>
        <button className="nav-item">
          <span className="material-symbols-outlined">analytics</span>
          <span>Analytics</span>
        </button>
        <button className="nav-item">
          <span className="material-symbols-outlined">key</span>
          <span>API Keys</span>
        </button>
        <button className="nav-item">
          <span className="material-symbols-outlined">settings</span>
          <span>Settings</span>
        </button>
      </nav>
    </div>
  );
}
