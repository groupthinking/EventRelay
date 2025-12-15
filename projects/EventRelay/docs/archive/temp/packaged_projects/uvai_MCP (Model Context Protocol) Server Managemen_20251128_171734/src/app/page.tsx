import Link from 'next/link';
import { 
  Terminal, 
  Server, 
  Activity, 
  Shield, 
  Zap, 
  Box, 
  Cpu, 
  LayoutDashboard, 
  ChevronRight,
  Code2,
  Container
} from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-slate-300 selection:bg-indigo-500/30 selection:text-indigo-200 font-sans">
      {/* Background Gradients */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-900/20 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-violet-900/10 blur-[120px]" />
      </div>

      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-[#0A0A0B]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white">
              <Cpu size={18} />
            </div>
            <span className="text-white font-bold text-lg tracking-tight">MCP<span className="text-indigo-400">Toolkit</span></span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium">
            <Link href="#features" className="hover:text-white transition-colors">Features</Link>
            <Link href="#templates" className="hover:text-white transition-colors">Templates</Link>
            <Link href="#monitoring" className="hover:text-white transition-colors">Monitoring</Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-medium hover:text-white transition-colors">Log In</Link>
            <Link href="/signup" className="text-sm font-medium bg-white text-black px-4 py-2 rounded-full hover:bg-slate-200 transition-colors">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      <main className="relative z-10">
        {/* Hero Section */}
        <section className="pt-32 pb-20 lg:pt-48 lg:pb-32 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-xs font-semibold mb-8 animate-fade-in-up">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
            </span>
            New: One-Click Docker Deployment
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold text-white tracking-tight mb-6 leading-tight">
            The Ultimate <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-violet-400 to-indigo-400">MCP Setup</span> for<br />
            AI Coding Assistants
          </h1>
          
          <p className="max-w-2xl mx-auto text-lg md:text-xl text-slate-400 mb-10">
            Connect Claude, Cursor, and potential AI agents to your data instantly. Orchestrate, monitor, and deploy Model Context Protocol servers with a single command.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-20">
            <Link href="/dashboard" className="w-full sm:w-auto px-8 py-3.5 rounded-lg bg-indigo-600 text-white font-medium hover:bg-indigo-500 transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-900/20">
              <Zap size={18} />
              Deploy Server
            </Link>
            <Link href="/docs" className="w-full sm:w-auto px-8 py-3.5 rounded-lg border border-white/10 bg-white/5 text-white font-medium hover:bg-white/10 transition-all flex items-center justify-center gap-2">
              <Terminal size={18} />
              View Templates
            </Link>
          </div>

          {/* Terminal / Dashboard Preview */}
          <div className="relative max-w-5xl mx-auto rounded-xl border border-white/10 bg-[#0F1012] shadow-2xl overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5 bg-white/5">
              <div className="w-3 h-3 rounded-full bg-red-500/50" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
              <div className="w-3 h-3 rounded-full bg-green-500/50" />
              <div className="ml-4 text-xs text-slate-500 font-mono">mcp-orchestrator — zsh</div>
            </div>
            <div className="grid md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-white/10 h-full min-h-[400px]">
              {/* Column 1: Server List */}
              <div className="p-4 flex flex-col gap-3">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Active Servers</div>
                <div className="p-3 rounded bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.5)]" />
                    <span className="text-sm text-indigo-100 font-medium">Postgres-Main</span>
                  </div>
                  <span className="text-xs text-indigo-300">Port 5432</span>
                </div>
                <div className="p-3 rounded bg-white/5 border border-white/5 flex items-center justify-between opacity-70">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-green-400" />
                    <span className="text-sm text-slate-300">GitHub-Integration</span>
                  </div>
                  <span className="text-xs text-slate-500">Port 3000</span>
                </div>
                <div className="p-3 rounded bg-white/5 border border-white/5 flex items-center justify-between opacity-70">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-green-400" />
                    <span className="text-sm text-slate-300">Slack-Bot-Context</span>
                  </div>
                  <span className="text-xs text-slate-500">Port 8080</span>
                </div>
              </div>
              
              {/* Column 2: Logs */}
              <div className="col-span-2 bg-[#050505] p-4 font-mono text-xs md:text-sm text-slate-400 overflow-hidden relative">
                 <div className="absolute top-0 right-0 p-2">
                    <span className="px-2 py-1 rounded bg-green-900/30 text-green-400 border border-green-900/50">Live</span>
                 </div>
                 <div className="space-y-2">
                   <p><span className="text-blue-400">info</span>  [Orchestrator] Initializing MCP connection bridge...</p>
                   <p><span className="text-blue-400">info</span>  [Docker] Container <span className="text-yellow-300">postgres-mcp-1</span> started successfully</p>
                   <p><span className="text-purple-400">debug</span> [Auth] Verifying environment secrets for Claude connection</p>
                   <p><span className="text-green-400">success</span> Connection established! MCP Server is ready to accept queries.</p>
                   <p><span className="text-slate-600">... Waiting for incoming context requests</span></p>
                   <div className="mt-4 pl-2 border-l-2 border-indigo-500/50">
                      <p className="text-slate-300">{`> User: "Check the database schema for the users table"`}</p>
                      <p className="text-indigo-400 mt-1">{`> MCP: Retrieving schema from Postgres-Main...`}</p>
                   </div>
                 </div>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Grid */}
        <section id="features" className="py-24 bg-white/5 border-y border-white/5">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">Everything needed to 10x productivity</h2>
              <p className="text-slate-400 max-w-2xl mx-auto">Stop wrestling with JSON configs and manual container restarts. We provide a full GUI for your Model Context Protocol infrastructure.</p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              <FeatureCard 
                icon={<Container className="text-blue-400" />}
                title="One-Click Docker"
                description="Instantly spin up MCP servers in isolated Docker containers. No more dependency conflicts on your local machine."
              />
              <FeatureCard 
                icon={<LayoutDashboard className="text-indigo-400" />}
                title="Orchestration Dashboard"
                description="Manage multiple servers from a single pane of glass. Start, stop, and restart services with visual controls."
              />
              <FeatureCard 
                icon={<Activity className="text-green-400" />}
                title="Health Monitoring"
                description="Real-time heartbeat checks and log aggregation. Know exactly when a server goes down or a connection fails."
              />
              <FeatureCard 
                icon={<Box className="text-orange-400" />}
                title="Template Library"
                description="Pre-configured setups for Postgres, GitHub, Slack, Linear, and Notion. Clone and deploy in seconds."
              />
              <FeatureCard 
                icon={<Shield className="text-red-400" />}
                title="Secrets Management"
                description="Securely store API keys and database credentials. Variables are injected into containers at runtime."
              />
              <FeatureCard 
                icon={<Code2 className="text-purple-400" />}
                title="Connection Debugger"
                description="Test tools built-in to verify that your AI assistant can actually read and execute tools on your server."
              />
            </div>
          </div>
        </section>

        {/* Integration / How it Works */}
        <section className="py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
                Bridge the gap between <br />
                <span className="text-indigo-400">Code</span> and <span className="text-indigo-400">Context</span>
              </h2>
              <p className="text-slate-400 text-lg mb-8">
                Your AI coding assistant is only as good as the context it has. MCP Toolkit provides the piping to feed real-time data from your tools directly into Claude or Cursor.
              </p>
              
              <div className="space-y-6">
                <IntegrationItem 
                  step="01"
                  title="Select a Server Template"
                  desc="Choose from our marketplace of pre-built MCP servers (SQL, Filesystem, API wrappers)."
                />
                <IntegrationItem 
                  step="02"
                  title="Configure Secrets"
                  desc="Enter your connection strings and API keys in our secure vault."
                />
                <IntegrationItem 
                  step="03"
                  title="Connect to Assistant"
                  desc="Copy the generated config snippet directly into your Claude Desktop or Cursor settings."
                />
              </div>
            </div>
            
            <div className="relative">
              <div className="absolute inset-0 bg-indigo-500/20 blur-[100px] rounded-full" />
              <div className="relative rounded-2xl border border-white/10 bg-slate-900/50 backdrop-blur-sm p-8">
                 <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 rounded-lg bg-white/5 border border-white/5">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded bg-indigo-600 flex items-center justify-center">
                                <Server size={24} className="text-white" />
                            </div>
                            <div>
                                <h4 className="text-white font-medium">Postgres MCP</h4>
                                <p className="text-xs text-slate-400">Running • 24ms latency</p>
                            </div>
                        </div>
                        <div className="h-2 w-24 bg-green-500/20 rounded-full overflow-hidden">
                            <div className="h-full w-[80%] bg-green-500 animate-pulse" />
                        </div>
                    </div>

                    <div className="flex justify-center">
                        <div className="h-8 w-px bg-gradient-to-b from-white/20 to-transparent" />
                    </div>

                    <div className="p-6 rounded-lg border border-indigo-500/30 bg-indigo-500/5 text-center">
                        <p className="text-sm text-indigo-300 font-mono mb-2">Generated Config</p>
                        <code className="text-xs text-slate-400 break-all">
                            {`"mcpServers": { "postgres": { "command": "docker", "args": ["run", "-i", "--rm", "mcp/pg"] } }`}
                        </code>
                        <button className="mt-4 w-full py-2 bg-indigo-600 hover:bg-indigo-500 rounded text-sm font-medium text-white transition-colors">
                            Copy for Claude Desktop
                        </button>
                    </div>
                 </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 px-4">
          <div className="max-w-4xl mx-auto relative rounded-3xl overflow-hidden p-12 text-center border border-white/10">
            <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/40 to-black z-0" />
            
            <div className="relative z-10">
              <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">Ready to supercharge your AI workflow?</h2>
              <p className="text-slate-300 text-lg mb-8 max-w-xl mx-auto">
                Join thousands of developers using MCP Toolkit to orchestrate their context servers and code 10x faster.
              </p>
              
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link href="/signup" className="w-full sm:w-auto px-8 py-4 rounded-full bg-white text-black font-bold hover:bg-slate-200 transition-colors text-lg">
                  Get Started for Free
                </Link>
                <Link href="/pricing" className="w-full sm:w-auto px-8 py-4 rounded-full border border-white/20 hover:bg-white/5 transition-colors text-white font-medium">
                  View Pricing
                </Link>
              </div>
              
              <div className="mt-8 flex items-center justify-center gap-6 text-slate-500 text-sm">
                <span className="flex items-center gap-2"><Shield size={14} /> No credit card required</span>
                <span className="flex items-center gap-2"><Container size={14} /> Free Docker tier</span>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/10 bg-black py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-indigo-600 flex items-center justify-center text-white">
                  <Cpu size={14} />
                </div>
                <span className="text-slate-300 font-bold">MCP Toolkit</span>
            </div>
            <div className="flex gap-8 text-sm text-slate-500">
                <Link href="#" className="hover:text-white transition-colors">Documentation</Link>
                <Link href="#" className="hover:text-white transition-colors">Marketplace</Link>
                <Link href="#" className="hover:text-white transition-colors">Twitter</Link>
                <Link href="#" className="hover:text-white transition-colors">GitHub</Link>
            </div>
            <p className="text-slate-600 text-xs">© 2024 MCP Toolkit. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="p-6 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] transition-colors group">
      <div className="mb-4 p-3 rounded-lg bg-white/5 w-fit group-hover:scale-110 transition-transform duration-300">
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
      <p className="text-slate-400 text-sm leading-relaxed">{description}</p>
    </div>
  );
}

function IntegrationItem({ step, title, desc }: { step: string, title: string, desc: string }) {
    return (
        <div className="flex gap-4">
            <div className="flex-shrink-0 w-12 h-12 rounded-full border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold bg-indigo-900/10">
                {step}
            </div>
            <div>
                <h3 className="text-lg font-semibold text-white">{title}</h3>
                <p className="text-slate-400 mt-1">{desc}</p>
            </div>
        </div>
    )
}