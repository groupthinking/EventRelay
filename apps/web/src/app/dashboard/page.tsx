'use client';

import { useEffect, useState } from 'react';

interface DashboardMetrics {
  status: string;
  timestamp: string;
  metrics: {
    activeWorkflows: number;
    totalProcessed: number;
    errorRate: number;
  };
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchMetrics() {
      try {
        const res = await fetch('/api/dashboard');
        const data = await res.json();
        setMetrics(data);
      } catch (error) {
        console.error('Failed to fetch metrics:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchMetrics();
  }, []);

  if (loading) {
    return <div className="p-8">Loading dashboard...</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">EventRelay Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-500 text-sm">Active Workflows</h3>
          <p className="text-3xl font-bold">{metrics?.metrics.activeWorkflows ?? 0}</p>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-500 text-sm">Total Processed</h3>
          <p className="text-3xl font-bold">{metrics?.metrics.totalProcessed ?? 0}</p>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-500 text-sm">Error Rate</h3>
          <p className="text-3xl font-bold">{metrics?.metrics.errorRate ?? 0}%</p>
        </div>
      </div>

      <div className="mt-8 text-sm text-gray-500">
        Status: {metrics?.status} | Last updated: {metrics?.timestamp}
      </div>
    </div>
  );
}