import React, { useState } from 'react';

interface GeneratorConsoleProps {
    // Empty interfaces for now
}

export function GeneratorConsole() {
    const [url, setUrl] = useState('');
    const [status, setStatus] = useState<'idle' | 'analyzing' | 'building' | 'complete'>('idle');

    const handleGenerate = async () => {
        try {
            setStatus('analyzing');
            const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
            console.log('Using API URL:', apiUrl);
            
            const response = await fetch(`${apiUrl}/api/v1/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, auto_deploy: true })
            });

            if (!response.ok) throw new Error('Generation failed');

            const data = await response.json();
            console.log('Job started:', data.job_id);

            // Poll for status (mock for now, will implement real polling next)
            setStatus('building');

            // Simulate polling duration for effect until real WS/polling is in
            setTimeout(() => setStatus('complete'), 5000); // Temporary visual

        } catch (error) {
            console.error('Error:', error);
            setStatus('idle'); // Reset on error
            alert('Failed to start generation. Check backend connection.');
        }
    };

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Header Section */}
            <div className="text-center mb-12">
                <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white sm:text-5xl md:text-6xl">
                    <span className="block">EventRelay</span>
                    <span className="block text-indigo-600 dark:text-indigo-400">Infrastructure Generator</span>
                </h1>
                <p className="mt-3 max-w-md mx-auto text-base text-gray-500 dark:text-gray-400 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
                    Transform YouTube tutorials into production-ready AI infrastructure.
                    Input a URL, get a deployed monorepo.
                </p>
            </div>

            {/* Input Section */}
            <div className="max-w-3xl mx-auto mb-12">
                <div className="flex gap-4">
                    <input
                        type="text"
                        className="flex-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md dark:bg-gray-800 dark:border-gray-700 dark:text-white p-4 text-lg"
                        placeholder="Paste YouTube Tutorial URL (e.g. 'Build a SaaS with Next.js')..."
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                    />
                    <button
                        onClick={handleGenerate}
                        disabled={!url || status !== 'idle'}
                        className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {status === 'idle' ? 'Generate Platform' : 'Processing...'}
                    </button>
                </div>
            </div>

            {/* Visualization / Console Output */}
            {status !== 'idle' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Left: Architecture Visualization Mock */}
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 border border-gray-200 dark:border-gray-700 h-96">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Architecture Plan (Tri-Model Consensus)</h3>
                        <div className="h-full flex items-center justify-center border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg">
                            <div className="text-center">
                                <p className="text-gray-500 animate-pulse">Analyzing Video Content...</p>
                                <p className="text-xs text-gray-400 mt-2">Gemini • Claude • Grok</p>
                            </div>
                        </div>
                    </div>

                    {/* Right: Build Log Console */}
                    <div className="bg-black rounded-lg p-4 font-mono text-sm h-96 overflow-y-auto">
                        <div className="flex items-center justify-between mb-2 border-b border-gray-700 pb-2">
                            <span className="text-green-500 font-bold">Build Terminal</span>
                            <span className="text-gray-500">v1.2.0</span>
                        </div>
                        <div className="space-y-1">
                            <p className="text-gray-400">[10:00:01] <span className="text-blue-400">INFO</span> Initializing Tri-Model Consensus Engine...</p>
                            <p className="text-gray-400">[10:00:02] <span className="text-blue-400">INFO</span> Fetching transcript from: {url}</p>
                            {status === 'building' && (
                                <>
                                    <p className="text-gray-400">[10:00:04] <span className="text-yellow-400">WARN</span> Complex schema detected at 04:32. Verifying with Claude 3.5 Sonnet.</p>
                                    <p className="text-gray-400">[10:00:05] <span className="text-green-400">SUCCESS</span> Architecture Graph locked.</p>
                                    <p className="text-gray-400">[10:00:06] <span className="text-blue-400">INFO</span> Generating Turborepo structure...</p>
                                </>
                            )}
                            {status === 'complete' && (
                                <p className="text-green-500 mt-4">✔ Infrastructure Provisioned. Ready for Deployment.</p>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
