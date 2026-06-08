'use client';

import { useState } from 'react';
import Link from 'next/link';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';

interface APIResponse {
  status: 'success' | 'error' | 'loading' | null;
  data: unknown;
  latency?: number;
}

interface PlaygroundEndpoint {
  method: 'GET' | 'POST';
  endpoint: string;
  description: string;
  realBody: string | null;
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
        className="w-full h-64 p-4 bg-surface-900 rounded-xl border border-white/10 font-mono text-sm text-white/80 resize-none focus:outline-none focus:border-primary-500/50"
        spellCheck={false}
      />
    </div>
  );
}

// Response viewer
function ResponseViewer({ response }: { response: APIResponse }) {
  if (response.status === 'loading') {
    return (
      <div className="flex items-center justify-center h-64 bg-surface-900 rounded-xl border border-white/10">
        <div className="text-center">
          <div className="w-12 h-12 rounded-full border-4 border-primary-500 border-t-transparent animate-spin mx-auto mb-4" />
          <p className="text-white/60">Processing request...</p>
        </div>
      </div>
    );
  }

  if (!response.status) {
    return (
      <div className="flex items-center justify-center h-64 bg-surface-900 rounded-xl border border-white/10">
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
          ? 'bg-teal-500/10 border-teal-500/50'
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
  "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"
}`);
  const [response, setResponse] = useState<APIResponse>({ status: null, data: null });

  const endpoints: PlaygroundEndpoint[] = [
    {
      method: 'POST',
      endpoint: '/api/video',
      description: 'Analyze a YouTube video — extract transcript, generate insights and actions',
      realBody: '{"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"}',
    },
    {
      method: 'POST',
      endpoint: '/api/pipeline',
      description: 'Create a Vercel-oriented app or workflow handoff from a video',
      realBody: '{"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw", "project_type": "web", "deployment_target": "vercel"}',
    },
    {
      method: 'POST',
      endpoint: '/api/extract-events',
      description: 'Turn transcript text into events, decisions and action items',
      realBody: '{"transcript": "The video explains how to turn a tutorial into a working product workflow.", "videoTitle": "Sample workflow", "videoUrl": "https://www.youtube.com/watch?v=jNQXAC9IVRw"}',
    },
    {
      method: 'POST',
      endpoint: '/api/chat',
      description: 'Ask a question with optional video context',
      realBody: '{"message": "What should this video become?", "context": "A YouTube tutorial should become a deployable workflow."}',
    },
    {
      method: 'GET',
      endpoint: '/api/pipeline',
      description: 'Check whether backend and model services are configured',
      realBody: null,
    },
    {
      method: 'GET',
      endpoint: '/api',
      description: 'List the public app API surface',
      realBody: null,
    },
  ];

  const handleSendRequest = async () => {
    setResponse({ status: 'loading', data: null });

    const start = Date.now();
    const currentEndpoint = endpoints[selectedEndpoint];
    const url = currentEndpoint.endpoint;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);

    try {
      const fetchOptions: RequestInit = {
        method: currentEndpoint.method,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
        },
      };

      // Add body for POST requests
      if (currentEndpoint.method === 'POST') {
        // Use the request body from the editor if it's valid JSON
        try {
          const parsedBody = JSON.parse(requestBody);
          fetchOptions.body = JSON.stringify(parsedBody);
        } catch {
          // Fall back to the realBody template
          fetchOptions.body = currentEndpoint.realBody || '{}';
        }
      }

      const res = await fetch(url, fetchOptions);
      const text = await res.text();
      const contentType = res.headers.get('content-type') || '';
      let data: unknown;
      if (text.length === 0) {
        data = { status: res.status, message: 'Empty response body' };
      } else {
        try {
          data = JSON.parse(text);
        } catch {
          data = {
            status: res.status,
            contentType,
            error: 'Non-JSON response',
            body: text.slice(0, 1200),
          };
        }
      }
      const latency = Date.now() - start;

      setResponse({
        status: res.ok ? 'success' : 'error',
        data,
        latency
      });
    } catch (error) {
      const timedOut = error instanceof DOMException && error.name === 'AbortError';
      setResponse({
        status: 'error',
        data: {
          error: timedOut ? 'Request timed out' : 'Request failed',
          message: timedOut
            ? 'The backend did not respond within 15 seconds. Check provider billing and BACKEND_URL before retrying.'
            : String(error),
          url,
        },
        latency: Date.now() - start
      });
    } finally {
      window.clearTimeout(timeout);
    }
  };

  const currentEndpoint = endpoints[selectedEndpoint];

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Gradient background */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-900/10 via-slate-950 to-slate-950" />

      {/* Navigation */}
      <Nav
        subtitle="API Playground"
        rightSlot={
          <Link
            href="/api/docs"
            className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm hover:bg-white/10 transition"
          >
            Full API Docs →
          </Link>
        }
      />

      <div className="relative z-10 max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2 font-heading">API Playground</h1>
          <p className="text-white/60">
            Test UVAI routes directly in this Vercel app. Responses stay JSON-first, even when a backend key or service is missing.
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
                onClick={() => {
                  setSelectedEndpoint(i);
                  setRequestBody(ep.realBody || '');
                  setResponse({ status: null, data: null });
                }}
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
                {currentEndpoint.endpoint}
              </code>
              <button
                onClick={handleSendRequest}
                className="px-6 py-2 rounded-lg bg-gradient-to-r from-teal-600 to-teal-700 font-medium hover:opacity-90 transition"
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
  'https://uvai.io/api/video',
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
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
    'https://uvai.io/api/video',
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
      <Footer variant="compact" />
    </div>
  );
}
