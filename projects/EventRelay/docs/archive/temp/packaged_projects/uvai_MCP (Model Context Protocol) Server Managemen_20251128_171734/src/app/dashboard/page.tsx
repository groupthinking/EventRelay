import React from 'react';
import { 
  Server, 
  Activity, 
  Cpu, 
  Zap, 
  Plus, 
  MoreVertical, 
  Play, 
  Square, 
  Terminal, 
  Settings,
  RefreshCw,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

// --- Mock Data ---

interface MetricCardProps {
  title: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'neutral';
  icon: React.ElementType;
}

interface MCPServer {
  id: string;
  name: string;
  type: string;
  status: 'running' | 'stopped' | 'error' | 'building';
  port: number;
  uptime: string;
  memory: string;
  requests: number;
}

const servers: MCPServer[] = [
  { id: '1', name: 'filesystem-mcp', type: 'Node.js', status: 'running', port: 3001, uptime: '2d 4h', memory: '128MB', requests: 1240 },
  { id: '2', name: 'postgres-connector', type: 'Docker', status: 'running', port: 5432, uptime: '5d 12h', memory: '256MB', requests: 8502 },
  { id: '3', name: 'brave-search-api', type: 'Python', status: 'stopped', port: 8000, uptime: '-', memory: '-', requests: 0 },
  { id: '4', name: 'github-context', type: 'Docker', status: 'building', port: 3005, uptime: '1m', memory: '450MB', requests: 12 },
  { id: '5', name: 'slack-integration', type: 'Node.js', status: 'error', port: 3002, uptime: '1h', memory: '0MB', requests: 5 },
];

const logs = [
  { id: 1, time: '10:42:01', server: 'filesystem-mcp', message: 'Read file request: /src/app/page.tsx', type: 'info' },
  { id: 2, time: '10:42:05', server: 'postgres-connector', message: 'Connection pool established', type: 'success' },
  { id: 3, time: '10:43:12', server: 'slack-integration', message: 'Auth token expired', type: 'error' },
  { id: 4, time: '10:44:00', server: 'github-context', message: 'Container pulling image...', type: 'info' },
];

// --- Components ---

const StatusBadge = ({ status }: { status: MCPServer['status'] }) => {
  const styles = {
    running: 'bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800',
    stopped: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700',
    error: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
    building: 'bg-yellow-100 text-yellow-700 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800',
  };

  const icons = {
    running: <CheckCircle2 className="w-3 h-3 mr-1" />,
    stopped: <Square className="w-3 h-3 mr-1 fill-current" />,
    error: <AlertCircle className="w-3 h-3 mr-1" />,
    building: <RefreshCw className="w-3 h-3 mr-1 animate-spin" />,
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[status]}`}>
      {icons[status]}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-zinc-950 p-6 space-y-8">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">MCP Control Center</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Manage your Model Context Protocol servers and connections.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-zinc-900 dark:text-gray-300 dark:border-zinc-700 dark:hover:bg-zinc-800 transition-colors">
            <RefreshCw className="w-4 h-4" />
            Check Health
          </button>
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 shadow-sm shadow-indigo-200 dark:shadow-none transition-colors">
            <Plus className="w-4 h-4" />
            Deploy Server
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { title: 'Active Servers', value: '3/5', change: '+1 deployed', trend: 'up', icon: Server },
          { title: 'Total Requests', value: '9.8k', change: '+12% this week', trend: 'up', icon: Activity },
          { title: 'System Load', value: '34%', change: 'Normal', trend: 'neutral', icon: Cpu },
          { title: 'Avg Latency', value: '42ms', change: '-5ms faster', trend: 'up', icon: Zap },
        ].map((stat, i) => (
          <div key={i} className="bg-white dark:bg-zinc-900 p-6 rounded-xl border border-gray-200 dark:border-zinc-800 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{stat.title}</p>
                <h3 className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{stat.value}</h3>
              </div>
              <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg">
                <stat.icon className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm">
              <span className={`font-medium ${stat.trend === 'up' ? 'text-green-600 dark:text-green-400' : 'text-gray-600 dark:text-gray-400'}`}>
                {stat.change}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        
        {/* Server List (Takes up 2/3 on large screens) */}
        <div className="xl:col-span-2 bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-gray-200 dark:border-zinc-800 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Active MCP Servers</h2>
            <button className="text-sm text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 font-medium">View All</button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-500 dark:text-gray-400">
              <thead className="bg-gray-50 dark:bg-zinc-950/50 text-xs uppercase font-semibold text-gray-500 dark:text-gray-400">
                <tr>
                  <th className="px-6 py-4">Server Name</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Port</th>
                  <th className="px-6 py-4">Stats</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-zinc-800">
                {servers.map((server) => (
                  <tr key={server.id} className="hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded bg-gray-100 dark:bg-zinc-800 flex items-center justify-center text-gray-500">
                          {server.type === 'Docker' ? <BoxIcon /> : <Terminal className="w-4 h-4" />}
                        </div>
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">{server.name}</p>
                          <p className="text-xs text-gray-500">{server.type}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={server.status} />
                    </td>
                    <td className="px-6 py-4 font-mono text-xs">{server.port}</td>
                    <td className="px-6 py-4 text-xs">
                      <div className="flex flex-col gap-1">
                        <span>Mem: {server.memory}</span>
                        <span>Req: {server.requests}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {server.status === 'running' ? (
                           <button title="Stop" className="p-1.5 hover:bg-red-50 text-gray-500 hover:text-red-600 rounded-md transition-colors">
                             <Square className="w-4 h-4 fill-current" />
                           </button>
                        ) : (
                          <button title="Start" className="p-1.5 hover:bg-green-50 text-gray-500 hover:text-green-600 rounded-md transition-colors">
                             <Play className="w-4 h-4" />
                           </button>
                        )}
                        <button title="Logs" className="p-1.5 hover:bg-gray-100 dark:hover:bg-zinc-800 text-gray-500 rounded-md transition-colors">
                          <Terminal className="w-4 h-4" />
                        </button>
                        <button title="Settings" className="p-1.5 hover:bg-gray-100 dark:hover:bg-zinc-800 text-gray-500 rounded-md transition-colors">
                          <Settings className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Real-time Logs / Activity Panel */}
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 shadow-sm flex flex-col">
          <div className="p-6 border-b border-gray-200 dark:border-zinc-800 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Activity</h2>
            <span className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400 font-medium">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
              </span>
              Live
            </span>
          </div>
          
          <div className="p-4 flex-1 overflow-y-auto max-h-[500px]">
             <div className="space-y-4">
                {logs.map((log) => (
                  <div key={log.id} className="flex gap-3 text-sm">
                    <div className="mt-0.5 min-w-[60px] text-xs font-mono text-gray-400">{log.time}</div>
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 dark:text-gray-200 flex items-center gap-2">
                        {log.server}
                        {log.type === 'error' && <span className="text-[10px] bg-red-100 text-red-600 px-1.5 rounded dark:bg-red-900/30">ERR</span>}
                      </p>
                      <p className={`text-gray-600 dark:text-gray-400 line-clamp-2 ${log.type === 'error' ? 'text-red-500 dark:text-red-400' : ''}`}>
                        {log.message}
                      </p>
                    </div>
                  </div>
                ))}
             </div>
             
             {/* Fake typing cursor for effect */}
             <div className="mt-4 pt-4 border-t border-dashed border-gray-200 dark:border-zinc-800">
               <div className="flex gap-2 items-center text-xs text-gray-400">
                  <span className="w-1.5 h-4 bg-gray-400 animate-pulse"></span>
                  Waiting for incoming logs...
               </div>
             </div>
          </div>
          
          <div className="p-4 border-t border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-950/50 rounded-b-xl">
             <button className="w-full py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 border border-gray-200 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-900 transition-colors shadow-sm">
                View Full Logs
             </button>
          </div>
        </div>

      </div>
    </div>
  );
}

// Simple icon for Docker
function BoxIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className="w-4 h-4"
      {...props}
    >
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
      <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
      <line x1="12" y1="22.08" x2="12" y2="12"></line>
    </svg>
  );
}