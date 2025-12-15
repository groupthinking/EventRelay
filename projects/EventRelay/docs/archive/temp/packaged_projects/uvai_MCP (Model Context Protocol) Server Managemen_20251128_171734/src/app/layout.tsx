import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import React from "react";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "MCP Toolkit - Ultimate MCP Setup For AI Coding Assistants",
  description: "One-click Docker deployment, real-time monitoring, and orchestration for your Model Context Protocol servers to 10x your productivity.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen flex flex-col bg-slate-50 text-slate-900`}>
        {/* Inline Navigation Bar */}
        <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/80 backdrop-blur-md">
          <div className="container mx-auto px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Link href="/" className="flex items-center gap-2 group">
                <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-600/20 group-hover:bg-blue-700 transition-colors">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="h-5 w-5 text-white"
                  >
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                </div>
                <span className="font-bold text-xl tracking-tight text-slate-900">MCP Toolkit</span>
              </Link>
            </div>

            <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
              <Link href="/dashboard" className="hover:text-blue-600 transition-colors">Dashboard</Link>
              <Link href="/servers" className="hover:text-blue-600 transition-colors">My Servers</Link>
              <Link href="/templates" className="hover:text-blue-600 transition-colors">Templates</Link>
              <Link href="/analytics" className="hover:text-blue-600 transition-colors">Analytics</Link>
            </nav>

            <div className="flex items-center gap-4">
              <div className="hidden lg:flex items-center gap-2 px-3 py-1 bg-slate-100 rounded-full border border-slate-200">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="text-xs font-medium text-slate-600">System Healthy</span>
              </div>
              <Link
                href="https://github.com"
                target="_blank"
                className="hidden sm:block text-slate-500 hover:text-slate-800 transition-colors"
                aria-label="GitHub"
              >
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                </svg>
              </Link>
              <button className="bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-md text-sm font-semibold transition-all shadow-sm flex items-center gap-2">
                <span>Deploy Server</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
              </button>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-grow">
          {children}
        </main>

        {/* Inline Footer */}
        <footer className="bg-slate-950 text-slate-400 py-12 border-t border-slate-800">
          <div className="container mx-auto px-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-12">
              <div className="col-span-1 md:col-span-1">
                <div className="flex items-center gap-2 mb-4 text-white">
                  <div className="h-6 w-6 bg-blue-600 rounded flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 text-white">
                      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                    </svg>
                  </div>
                  <span className="font-bold text-lg">MCP Toolkit</span>
                </div>
                <p className="text-sm leading-relaxed mb-6">
                  The ultimate setup for AI coding assistants. Orchestrate Model Context Protocol servers, manage Docker containers, and debug connections in real-time.
                </p>
                <div className="flex gap-4">
                  {/* Social placeholders */}
                  <a href="#" className="hover:text-white transition-colors"><span className="sr-only">Twitter</span><svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24"><path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84" /></svg></a>
                  <a href="#" className="hover:text-white transition-colors"><span className="sr-only">Discord</span><svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24"><path d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028 14.09 14.09 0 001.226-1.994.076.076 0 00-.041-.106 13.107 13.107 0 01-1.872-.892.077.077 0 01-.008-.128 10.2 10.2 0 00.372-.292.074.074 0 01.077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 01.078.01c.12.098.246.198.373.292a.077.077 0 01-.006.127 12.299 12.299 0 01-1.873.892.077.077 0 00-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg></a>
                </div>
              </div>

              <div>
                <h3 className="font-semibold text-white mb-4">Platform</h3>
                <ul className="space-y-2 text-sm">
                  <li><Link href="/features" className="hover:text-blue-400 transition-colors">Features</Link></li>
                  <li><Link href="/templates" className="hover:text-blue-400 transition-colors">Server Templates</Link></li>
                  <li><Link href="/integrations" className="hover:text-blue-400 transition-colors">Integrations</Link></li>
                  <li><Link href="/changelog" className="hover:text-blue-400 transition-colors">Changelog</Link></li>
                </ul>
              </div>

              <div>
                <h3 className="font-semibold text-white mb-4">Resources</h3>
                <ul className="space-y-2 text-sm">
                  <li><Link href="/docs" className="hover:text-blue-400 transition-colors">Documentation</Link></li>
                  <li><Link href="/api" className="hover:text-blue-400 transition-colors">API Reference</Link></li>
                  <li><Link href="/community" className="hover:text-blue-400 transition-colors">Community Hub</Link></li>
                  <li><Link href="/help" className="hover:text-blue-400 transition-colors">Help Center</Link></li>
                </ul>
              </div>

              <div>
                <h3 className="font-semibold text-white mb-4">Legal</h3>
                <ul className="space-y-2 text-sm">
                  <li><Link href="/privacy" className="hover:text-blue-400 transition-colors">Privacy Policy</Link></li>
                  <li><Link href="/terms" className="hover:text-blue-400 transition-colors">Terms of Service</Link></li>
                  <li><Link href="/security" className="hover:text-blue-400 transition-colors">Security</Link></li>
                </ul>
                <div className="mt-8 pt-8 border-t border-slate-900 text-xs text-slate-600">
                  &copy; {new Date().getFullYear()} MCP Toolkit.
                </div>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}