'use client';

import { useState } from 'react';
import Link from 'next/link';

interface APIResponse {
  status: 'success' | 'error' | 'loading' | null;
  data: any;
  latency?: number;
}

// Code editor component
function CodeEditor({ value, onChange, language = 'json' }: { value: string; onChange: (v: string) => void; language?: string }) {
  return (
    <div className="relative">
      <div className="absolute top-2 right-2 px-2 py-1 rounded bg-white/10 text-xs text-white/40">
        {language.toUpperCase()}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-64 p-4 bg-slate-900 rounded-xl border border-white/10 font-mono text-sm text-white/80 resize-none focus:outline-none focus:border-violet-500/50"
        spellCheck={false}
      />
    </div>
  );
}

// Response viewer
function ResponseViewer({ response }: { response: APIResponse }) {
  if (response.status === 'loading') {
    return (
      <div className="flex items-center justify-center h-64 bg-slate-900 rounded-xl border border-white/10">
        <div className="text-center">
          <div className="w-12 h-12 rounded-full border-4 border-violet-500 border-t-transparent animate-spin mx-auto mb-4" />
          <p className="text-white/60">Processing request...</p>
        </div>
      </div>
    );
  }

  if (!response.status) {
    return (
      <div className="flex items-center justify-center h-64 bg-slate-900 rounded-xl border border-white/10">
        <p className="text-white/40">Response will appear here</p>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className={`absolute top-2 right-2 px-2 py-1 rounded text-xs ${
        response.status === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
      }`}>
        {response.status.toUpperCase()} {response.latency && `• ${response.latency}ms`}
      </div>
      <pre className="w-full h-64 p-4 bg-slate-900 rounded-xl border border-white/10 font-mono text-sm text-white/80 overflow-auto">
        {JSON.stringify(response.data, null, 2)}
      </pre>
    </div>
  );
}

// Endpoint selector
function EndpointCard({
  method,
  endpoint,
  description,
  isSelected,
  onClick
}: {
  method: string;
  endpoint: string;
  description: string;
  isSelected: boolean;
  onClick: () => void;
}) {
  const methodColors: Record<string, string> = {
    GET: 'bg-green-500/20 text-green-400',
    POST: 'bg-blue-500/20 text-blue-400',
    PUT: 'bg-yellow-500/20 text-yellow-400',
    DELETE: 'bg-red-500/20 text-red-400',
  };

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border transition-all ${
        isSelected
          ? 'bg-violet-500/10 border-violet-500/50'
          : 'bg-white/5 border-white/10 hover:bg-white/10'
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className={`px-2 py-0.5 rounded text-xs font-bold ${methodColors[method]}`}>
          {method}
        </span>
        <code className="text-white/80 text-sm">{endpoint}</code>
      </div>
      <p className="text-white/40 text-sm">{description}</p>
    </button>
  );
}

export default function APIPlaygroundPage() {
  const [selectedEndpoint, setSelectedEndpoint] = useState(0);
  const [requestBody, setRequestBody] = useState(`{
  "url": "https://youtube.com/watch?v=example",
  "options": {
    "extract": ["summary", "actions", "code"],
    "deploy": false,
    "format": "json"
  }
}`);
  const [response, setResponse] = useState<APIResponse>({ status: null, data: null });

  const endpoints = [
    {
      method: 'POST',
      endpoint: '/api/v1/video/analyze',
      description: 'Analyze a video and extract intelligence',
      baseUrl: 'https://api.uvai.io',
    },
    {
      method: 'GET',
      endpoint: '/api/v1/video/{id}',
      description: 'Get analysis results for a processed video',
      baseUrl: 'https://api.uvai.io',
    },
    {
      method: 'POST',
      endpoint: '/api/v1/evolve',
      description: 'Execute a task with the Prescient Twin AI',
      baseUrl: 'https://api.uvai.io',
    },
    {
      method: 'GET',
      endpoint: '/api/v1/stats',
      description: 'Get current system statistics and active agents',
      baseUrl: 'https://api.uvai.io',
    },
    {
      method: 'POST',
      endpoint: '/api/v1/execute',
      description: 'Execute code in a sandboxed environment',
      baseUrl: 'https://api.uvai.io',
    },
  ];

  const handleSendRequest = async () => {
    setResponse({ status: 'loading', data: null });

    const start = Date.now();

    try {
      // Simulate API call (in production, this would make a real request)
      await new Promise(resolve => setTimeout(resolve, 1200));

      const latency = Date.now() - start;

      // Mock response based on endpoint
      const mockResponses: Record<string, any> = {
        '/api/v1/video/analyze': {
          id: 'vid_' + Math.random().toString(36).substring(7),
          status: 'complete',
          processing_time_ms: 2341,
          result: {
            summary: 'This video demonstrates advanced React patterns including hooks, context, and performance optimization techniques.',
            actions: [
              'Implement useState for local component state',
              'Use useCallback for memoized event handlers',
              'Create custom hooks for reusable logic'
            ],
            topics: ['React', 'JavaScript', 'Frontend Development'],
            sentiment: 'educational',
            code_snippets: [
              {
                language: 'typescript',
                description: 'Custom useAPI hook',
                code: 'const useAPI = (url) => { ... }'
              }
            ]
          }
        },
        '/api/v1/stats': {
          status: 'ok',
          agents_active: ['gemini-2.5-flash', 'claude-3-opus', 'grok-2'],
          videos_processed_today: 156,
          avg_processing_time_ms: 2300,
          uptime_percent: 99.97
        },
        '/api/v1/evolve': {
          task_id: 'task_' + Math.random().toString(36).substring(7),
          status: 'queued',
          estimated_completion_ms: 5000,
          assigned_agent: 'gemini-2.5-flash'
        }
      };

      const endpoint = endpoints[selectedEndpoint].endpoint;
      const mockData = mockResponses[endpoint] || { message: 'Request processed successfully' };

      setResponse({
        status: 'success',
        data: mockData,
        latency
      });
    } catch (error) {
      setResponse({
        status: 'error',
        data: { error: 'Request failed', message: String(error) },
        latency: Date.now() - start
      });
    }
  };

  const currentEndpoint = endpoints[selectedEndpoint];

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Gradient background */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-900/10 via-slate-950 to-slate-950" />

      {/* Navigation */}
      <nav className="relative z-50 flex items-center justify-between px-6 py-4 border-b border-white/5">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center font-black text-lg">
              U
            </div>
            <span className="font-bold text-xl">UVAI.io</span>
          </Link>
          <div className="h-6 w-px bg-white/10" />
          <span className="text-white/60">API Playground</span>
        </div>
        <div className="flex items-center gap-4">
          <Link
            href="https://api.uvai.io/docs"
            target="_blank"
            className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm hover:bg-white/10 transition"
          >
            Full API Docs →
          </Link>
        </div>
      </nav>

      <div className="relative z-10 max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">API Playground</h1>
          <p className="text-white/60">
            Test UVAI APIs directly in your browser. No authentication required for sandbox mode.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Endpoints List */}
          <div className="space-y-3">
            <h2 className="text-sm font-medium text-white/60 mb-4">Endpoints</h2>
            {endpoints.map((ep, i) => (
              <EndpointCard
                key={i}
                method={ep.method}
                endpoint={ep.endpoint}
                description={ep.description}
                isSelected={selectedEndpoint === i}
                onClick={() => setSelectedEndpoint(i)}
              />
            ))}
          </div>

          {/* Request/Response */}
          <div className="lg:col-span-3 space-y-6">
            {/* URL Bar */}
            <div className="flex items-center gap-3 p-4 bg-white/5 rounded-xl border border-white/10">
              <span className={`px-3 py-1 rounded-lg text-sm font-bold ${
                currentEndpoint.method === 'GET' ? 'bg-green-500/20 text-green-400' :
                currentEndpoint.method === 'POST' ? 'bg-blue-500/20 text-blue-400' :
                'bg-yellow-500/20 text-yellow-400'
              }`}>
                {currentEndpoint.method}
              </span>
              <code className="flex-1 text-white/80 font-mono">
                {currentEndpoint.baseUrl}{currentEndpoint.endpoint}
              </code>
              <button
                onClick={handleSendRequest}
                className="px-6 py-2 rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 font-medium hover:opacity-90 transition"
              >
                Send Request
              </button>
            </div>

            {/* Request Editor */}
            <div>
              <h3 className="text-sm font-medium text-white/60 mb-3">Request Body</h3>
              <CodeEditor
                value={requestBody}
                onChange={setRequestBody}
              />
            </div>

            {/* Response Viewer */}
            <div>
              <h3 className="text-sm font-medium text-white/60 mb-3">Response</h3>
              <ResponseViewer response={response} />
            </div>

            {/* Code Examples */}
            <div className="bg-white/5 rounded-xl border border-white/10 p-6">
              <h3 className="text-sm font-medium text-white/60 mb-4">Quick Start</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-white/40 mb-2">JavaScript / Node.js</p>
                  <pre className="p-4 bg-slate-900 rounded-lg text-xs text-white/70 overflow-x-auto">
{`const response = await fetch(
  'https://api.uvai.io/video/analyze',
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer YOUR_API_KEY'
    },
    body: JSON.stringify({
      url: 'https://youtube.com/...'
    })
  }
);`}
                  </pre>
                </div>
                <div>
                  <p className="text-xs text-white/40 mb-2">Python</p>
                  <pre className="p-4 bg-slate-900 rounded-lg text-xs text-white/70 overflow-x-auto">
{`import requests

response = requests.post(
    'https://api.uvai.io/video/analyze',
    headers={
        'Authorization': 'Bearer YOUR_API_KEY'
    },
    json={
        'url': 'https://youtube.com/...'
    }
)`}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
