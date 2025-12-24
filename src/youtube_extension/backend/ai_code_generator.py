#!/usr/bin/env python3
"""
AI-Powered Full-Stack Code Generator
=====================================

Uses Gemini 3 Pro Preview to generate complete full-stack applications
based on video analysis. Produces monetizable products, not templates.
"""

import os
import sys
import json
import logging
import tempfile
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Add project root for knowledge_base import
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import knowledge base for accumulated learning
try:
    from knowledge_base import get_knowledge_base
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_BASE_AVAILABLE = False
    logger.warning("Knowledge base not available - video technologies won't be persisted")

# Import Gemini SDK
try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-genai SDK not available - AI code generation disabled")


class AICodeGenerator:
    """
    AI-powered code generator using Gemini for intelligent full-stack generation.
    Produces complete, deployable applications from video analysis.
    """

    def __init__(self, output_dir: Optional[str] = None):
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set - AI code generation disabled")

        # Configure output directory (cross-platform)
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Default: EventRelay/generated_projects/
            project_root = Path(__file__).parent.parent.parent.parent
            self.output_dir = project_root / "generated_projects"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Output directory: {self.output_dir}")

        self.client = None
        if GENAI_AVAILABLE and self.gemini_api_key:
            self.client = genai.Client(api_key=self.gemini_api_key)
            logger.info("✅ AI Code Generator initialized with Gemini")

    async def generate_fullstack_project(
        self,
        video_analysis: Dict[str, Any],
        project_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a complete full-stack project using AI.

        Args:
            video_analysis: Results from video processing
            project_config: User configuration (type, features, monetization)

        Returns:
            Project generation results with path and metadata
        """
        if not self.client:
            logger.error("Gemini client not available")
            raise RuntimeError("AI code generation requires Gemini API key")

        logger.info("🤖 Starting AI-powered full-stack generation")

        # Extract information from video analysis
        extracted = video_analysis.get("extracted_info", {})
        ai_analysis = video_analysis.get("ai_analysis", {})

        title = extracted.get("title", "AI Generated Project")
        technologies = extracted.get("technologies", [])
        features = extracted.get("features", [])

        # Capture technologies to knowledge base for continuous learning
        if KNOWLEDGE_BASE_AVAILABLE and technologies:
            try:
                kb = get_knowledge_base()
                video_data = video_analysis.get("video_data", {})
                video_id = video_data.get("video_id", "unknown")
                video_url = video_data.get("video_url", "")
                result = kb.capture_from_video(video_id, title, technologies, video_url)
                logger.info(f"📚 Knowledge captured: {result['captured']} techs, {result['total_unique']} unique total")
            except Exception as e:
                logger.warning(f"Knowledge capture failed: {e}")

        # Determine project architecture
        architecture = await self._determine_architecture(
            video_analysis,
            project_config
        )

        # Create project directory in configured output location
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = f"uvai_{project_config.get('type', 'project')}_{timestamp}"
        project_path = self.output_dir / project_name
        project_path.mkdir(parents=True, exist_ok=True)

        # Generate project files using AI
        files_created = await self._generate_project_files(
            project_path,
            architecture,
            video_analysis
        )

        logger.info(f"✅ Generated {len(files_created)} files at {project_path}")

        return {
            "project_path": str(project_path),
            "project_type": architecture["type"],
            "framework": architecture["framework"],
            "files_created": files_created,
            "entry_point": architecture.get("entry_point", "package.json"),
            "build_command": architecture.get("build_command", "npm install && npm run build"),
            "start_command": architecture.get("start_command", "npm run dev"),
            "architecture": architecture,
            "monetization": architecture.get("monetization", {}),
            "ai_generated": True
        }

    async def _determine_architecture(
        self,
        video_analysis: Dict[str, Any],
        project_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to determine optimal project architecture"""

        extracted = video_analysis.get("extracted_info", {})
        ai_analysis = video_analysis.get("ai_analysis", {})

        # Get accumulated knowledge context
        knowledge_context = ""
        if KNOWLEDGE_BASE_AVAILABLE:
            try:
                kb = get_knowledge_base()
                knowledge_context = kb.get_technology_context()
            except Exception as e:
                logger.warning(f"Failed to get knowledge context: {e}")

        prompt = f"""Analyze this video content and determine the optimal full-stack architecture.

{knowledge_context}

VIDEO ANALYSIS:
Title: {extracted.get('title', 'Unknown')}
Technologies: {json.dumps(extracted.get('technologies', []))}
Features: {json.dumps(extracted.get('features', []))}
Complexity: {extracted.get('complexity', 'intermediate')}
AI Analysis: {json.dumps(ai_analysis) if ai_analysis else 'Not available'}

USER CONFIG:
{json.dumps(project_config)}

Return ONLY valid JSON with this structure:
{{
    "type": "fullstack_app" | "agent" | "saas" | "game" | "workflow" | "api",
    "framework": "nextjs" | "react_node" | "python_fastapi" | "typescript",
    "frontend": {{
        "framework": "nextjs" | "react" | "vue",
        "styling": "tailwind" | "chakra" | "material_ui",
        "state": "zustand" | "redux" | "context"
    }},
    "backend": {{
        "type": "api_routes" | "express" | "fastapi",
        "database": "supabase" | "postgres" | "mongodb" | "sqlite",
        "auth": "nextauth" | "clerk" | "supabase_auth" | "custom"
    }},
    "features": ["list", "of", "features", "to", "implement"],
    "monetization": {{
        "model": "freemium" | "subscription" | "one_time" | "usage_based",
        "payment_processor": "stripe" | "lemonsqueezy" | "paddle",
        "pricing_tiers": ["free", "pro", "enterprise"]
    }},
    "deployment": {{
        "platform": "vercel" | "railway" | "render" | "fly",
        "database_hosting": "supabase" | "planetscale" | "railway"
    }},
    "entry_point": "package.json",
    "build_command": "npm install && npm run build",
    "start_command": "npm run dev",
    "estimated_dev_time": "2-4 hours"
}}

Choose the architecture that best implements what the video teaches as WORKING INFRASTRUCTURE.

CRITICAL: Prioritize functional MVP over polished product. Generated code must:
1. Have real API endpoints (not mocks)
2. Include state management (Redis/Upstash for production apps)
3. Use actual SDKs (Docker SDK for container apps, etc)
4. Implement real business logic
5. Include error handling and observability

Choose "fullstack_app" for most cases, "agent" for MCP/workflow systems, "infrastructure_platform" for Turborepo monorepo with multiple apps."""

        try:
            response = self.client.models.generate_content(
                model='gemini-3-pro-preview',
                contents=prompt
            )

            # Parse response
            text = response.text
            # Extract JSON from potential markdown fences
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]

            architecture = json.loads(text.strip())
            logger.info(f"📐 Architecture determined: {architecture['type']} with {architecture['framework']}")
            return architecture

        except Exception as e:
            logger.warning(f"Architecture determination failed: {e}, using defaults")
            return self._default_architecture()

    def _default_architecture(self) -> Dict[str, Any]:
        """Return default infrastructure platform architecture with all packages"""
        return {
            "type": "infrastructure_platform",
            "framework": "nextjs",
            "frontend": {
                "framework": "nextjs",
                "styling": "tailwind",
                "state": "zustand"
            },
            "backend": {
                "type": "api_routes",
                "database": "supabase",
                "auth": "nextauth"
            },
            "features": [
                "auth",
                "database",
                "api",
                "dashboard",
                "ai-gateway",
                "workflows",
                "observability",
                "mcp-connectors",
                "error-handling"
            ],
            "monetization": {
                "model": "freemium",
                "payment_processor": "stripe",
                "pricing_tiers": ["free", "pro"]
            },
            "deployment": {
                "platform": "vercel",
                "database_hosting": "supabase"
            },
            # Explicit flags to trigger all package generation
            "monorepo": True,
            "has_mcp": True,
            "has_workflows": True,
            "has_observability": True,
            "has_ai_gateway": True,
            "has_logging": True,
            "has_error_handling": True,
            "has_database": True,
            "has_config": True,
            "entry_point": "package.json",
            "build_command": "npm install && npm run build",
            "start_command": "npm run dev",
            "estimated_dev_time": "2-4 hours"
        }

    async def _generate_project_files(
        self,
        project_path: Path,
        architecture: Dict[str, Any],
        video_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate all project files using AI"""

        files_created = []

        # Check if this should be a Turborepo monorepo (infrastructure platform)
        if architecture.get("type") == "infrastructure_platform" or architecture.get("monorepo"):
            files_created = await self._generate_turborepo_monorepo(
                project_path, architecture, video_analysis
            )
        elif architecture["framework"] == "nextjs":
            files_created = await self._generate_nextjs_project(
                project_path, architecture, video_analysis
            )
        elif architecture["framework"] == "python_fastapi":
            files_created = await self._generate_fastapi_project(
                project_path, architecture, video_analysis
            )
        else:
            # Default to Next.js
            files_created = await self._generate_nextjs_project(
                project_path, architecture, video_analysis
            )

        return files_created

    async def _generate_nextjs_project(
        self,
        project_path: Path,
        architecture: Dict[str, Any],
        video_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate a complete Next.js full-stack project"""

        files_created = []
        extracted = video_analysis.get("extracted_info", {})
        title = extracted.get("title", "AI Generated App")

        # Create directory structure
        dirs = [
            "src/app",
            "src/app/api",
            "src/app/api/auth",
            "src/app/dashboard",
            "src/components",
            "src/lib",
            "src/hooks",
            "public",
            ".github/workflows"  # GitHub Actions for auto-deployment
        ]
        for d in dirs:
            (project_path / d).mkdir(parents=True, exist_ok=True)

        # Generate package.json
        package_json = await self._generate_package_json(title, architecture)
        self._write_file(project_path / "package.json", json.dumps(package_json, indent=2))
        files_created.append("package.json")

        # Generate main page with AI
        main_page = await self._ai_generate_file(
            "main Next.js page",
            architecture,
            video_analysis,
            """Generate a WORKING Next.js 14+ app/page.tsx that implements core functionality:

PRIORITY: Working features over visual polish.

Requirements:
1. 'use client' directive at top (uses React hooks)
2. Import useState, useEffect from 'react'
3. State management for core data (useState for demo, but add TODO comments for Redis/Upstash)
4. Fetch data from /api route on mount using useEffect
5. Action buttons with REAL onClick handlers that call API endpoints
6. Display API response data (not hardcoded mock data)
7. Error handling and loading states
8. TypeScript with proper interfaces
9. Basic Tailwind styling (clean, not fancy)

VALIDATION: Every button must DO something functional (API call, state update, etc).
Return ONLY the code, no explanations."""
        )
        self._write_file(project_path / "src/app/page.tsx", main_page)
        files_created.append("src/app/page.tsx")

        # Generate layout
        layout = await self._ai_generate_file(
            "Next.js root layout",
            architecture,
            video_analysis,
            """Generate a Next.js 14+ app/layout.tsx with:
- Metadata for SEO
- Font imports (Inter from Google Fonts)
- Tailwind CSS imports (import './globals.css')
- INLINE navigation bar (do NOT import from @/components/navbar)
- INLINE footer section (do NOT import from @/components/footer)
- All components must be defined in this file or use standard React/Next.js imports only
- TypeScript
Return ONLY the code. Do NOT import any @/components/* files."""
        )
        self._write_file(project_path / "src/app/layout.tsx", layout)
        files_created.append("src/app/layout.tsx")

        # Generate FUNCTIONAL API route with real business logic
        api_route = await self._ai_generate_file(
            "main API route",
            architecture,
            video_analysis,
            """Generate a FUNCTIONAL Next.js API route at app/api/route.ts:

PRIORITY: Real business logic over placeholder responses.

Requirements:
1. Import NextRequest, NextResponse from 'next/server'
2. TypeScript interfaces for request/response
3. GET endpoint: Return meaningful system data (not just {status: 'online'})
4. POST endpoint: Implement actual business logic based on video content
5. Proper error handling with try/catch
6. Validate request payloads
7. Return structured responses with data/error fields

CONTEXT-SPECIFIC LOGIC:
- For MCP Dashboard: Implement Docker container operations (list, start, stop)
  * Use docker ps commands via child_process.exec
  * Parse and return real container data
- For SaaS apps: Implement core business operations
- For agent systems: Implement workflow triggers

VALIDATION: API must return real data, not mock/placeholder responses.
Return ONLY the code."""
        )
        self._write_file(project_path / "src/app/api/route.ts", api_route)
        files_created.append("src/app/api/route.ts")

        # Generate dashboard API route
        dashboard_api = await self._ai_generate_file(
            "dashboard API route",
            architecture,
            video_analysis,
            """Generate API route at app/api/dashboard/route.ts:

Requirements:
1. GET endpoint returning dashboard metrics/data
2. POST endpoint for dashboard actions
3. Real data sources (file system, Docker, processes, etc)
4. TypeScript interfaces
5. Error handling

For MCP Dashboard: Return Docker container list with status.
Return ONLY the code."""
        )
        self._write_file(project_path / "src/app/api/dashboard/route.ts", dashboard_api)
        files_created.append("src/app/api/dashboard/route.ts")

        # Generate dashboard page
        dashboard = await self._ai_generate_file(
            "dashboard page",
            architecture,
            video_analysis,
            """Generate a FUNCTIONAL Next.js dashboard at app/dashboard/page.tsx:

PRIORITY: Working data flow over visual design.

Requirements:
1. 'use client' directive (uses hooks)
2. Fetch real data from /api/dashboard on mount
3. Stats/metrics cards showing API response data (not mocks)
4. Refresh button that re-fetches data
5. Action buttons that POST to API and update UI
6. Loading spinner during data fetch
7. Error message display if API fails
8. TypeScript interfaces for API responses
9. Responsive grid with Tailwind

IMPLEMENTATION NOTES:
- For MCP Dashboard: Include Docker container operations (start/stop/list)
- API endpoints should return real system data (Docker SDK, process info, etc)
- State updates after each action

VALIDATION: Clicking refresh must fetch new data from server.
Return ONLY the code."""
        )
        self._write_file(project_path / "src/app/dashboard/page.tsx", dashboard)
        files_created.append("src/app/dashboard/page.tsx")

        # Generate component
        button_component = await self._ai_generate_file(
            "reusable button component",
            architecture,
            video_analysis,
            """Generate a FUNCTIONAL Button component at components/Button.tsx:

Requirements:
1. TypeScript props: onClick, children, variant, size, loading, disabled
2. Variants: primary, secondary, outline, danger
3. Sizes: sm, md, lg
4. Loading state (show spinner, disable button)
5. Disabled state styling
6. onClick handler pass-through
7. Accessible (aria-label, role)
8. Tailwind styling with class-variance-authority

CRITICAL: Button must support async operations (loading state during API calls).
Return ONLY the code."""
        )
        self._write_file(project_path / "src/components/Button.tsx", button_component)
        files_created.append("src/components/Button.tsx")

        # Generate config files
        self._write_file(project_path / "tailwind.config.js", self._tailwind_config())
        files_created.append("tailwind.config.js")

        self._write_file(project_path / "tsconfig.json", self._tsconfig())
        files_created.append("tsconfig.json")

        self._write_file(project_path / "next.config.js", self._next_config())
        files_created.append("next.config.js")

        # Generate globals.css
        self._write_file(project_path / "src/app/globals.css", self._globals_css())
        files_created.append("src/app/globals.css")

        # Generate README
        readme = self._generate_readme(title, architecture, video_analysis)
        self._write_file(project_path / "README.md", readme)
        files_created.append("README.md")

        # Generate .env.example
        env_example = self._generate_env_example(architecture)
        self._write_file(project_path / ".env.example", env_example)
        files_created.append(".env.example")

        # Generate .env.local with actual production keys
        env_local = self._generate_env_local(architecture)
        self._write_file(project_path / ".env.local", env_local)
        files_created.append(".env.local")
        logger.info("💰 Injected production Stripe keys into .env.local")

        # Generate .gitignore
        self._write_file(project_path / ".gitignore", self._gitignore())
        files_created.append(".gitignore")

        # Generate GitHub Actions workflow for auto-deployment to Vercel
        self._write_file(project_path / ".github/workflows/deploy.yml", self._github_actions_deploy())
        files_created.append(".github/workflows/deploy.yml")

        return files_created

    async def _ai_generate_file(
        self,
        description: str,
        architecture: Dict[str, Any],
        video_analysis: Dict[str, Any],
        specific_prompt: str
    ) -> str:
        """Use AI to generate a specific file"""

        extracted = video_analysis.get("extracted_info", {})

        prompt = f"""You are generating code for a {architecture['type']} application.

PROJECT CONTEXT:
- Title: {extracted.get('title', 'AI App')}
- Type: {architecture['type']}
- Framework: {architecture['framework']}
- Styling: {architecture.get('frontend', {}).get('styling', 'tailwind')}
- Features: {json.dumps(architecture.get('features', []))}

TASK: Generate {description}

{specific_prompt}"""

        try:
            response = self.client.models.generate_content(
                model='gemini-3-pro-preview',
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=1.0,  # Gemini 3 requires temp=1.0
                    max_output_tokens=8192
                    # Gemini 3 Pro uses HIGH thinking by default - cannot be disabled
                )
            )

            # Handle Gemini 3 responses with thought_signature
            code = response.text
            if code is None:
                # Try extracting from parts
                if response.candidates and response.candidates[0].content.parts:
                    text_parts = [p.text for p in response.candidates[0].content.parts if hasattr(p, 'text') and p.text]
                    code = "\n".join(text_parts) if text_parts else None

            if not code:
                return f"// Error: Gemini returned no code for {description}\n// Please implement manually"
            # Clean up code fences
            if '```typescript' in code:
                code = code.split('```typescript')[1].split('```')[0]
            elif '```tsx' in code:
                code = code.split('```tsx')[1].split('```')[0]
            elif '```javascript' in code:
                code = code.split('```javascript')[1].split('```')[0]
            elif '```' in code:
                code = code.split('```')[1].split('```')[0]

            return code.strip()

        except Exception as e:
            logger.error(f"AI file generation failed for {description}: {e}")
            return f"// Error generating {description}: {e}\n// Please implement manually"

    async def _generate_package_json(
        self,
        title: str,
        architecture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate package.json with appropriate dependencies"""

        name = title.lower().replace(' ', '-').replace("'", '')[:50]

        package = {
            "name": name,
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint"
            },
            "dependencies": {
                "next": "14.2.0",
                "react": "^18",
                "react-dom": "^18"
            },
            "devDependencies": {
                "typescript": "^5",
                "@types/node": "^20",
                "@types/react": "^18",
                "@types/react-dom": "^18",
                "postcss": "^8",
                "tailwindcss": "^3.4.1",
                "autoprefixer": "^10.0.1",
                "eslint": "^8",
                "eslint-config-next": "14.2.0"
            }
        }

        # Add based on architecture
        frontend = architecture.get("frontend", {})
        backend = architecture.get("backend", {})

        if frontend.get("state") == "zustand":
            package["dependencies"]["zustand"] = "^4.5.0"

        if backend.get("auth") == "nextauth":
            package["dependencies"]["next-auth"] = "^4.24.0"

        if backend.get("database") == "supabase":
            package["dependencies"]["@supabase/supabase-js"] = "^2.39.0"

        monetization = architecture.get("monetization", {})
        if monetization.get("payment_processor") == "stripe":
            package["dependencies"]["stripe"] = "^14.0.0"
            package["dependencies"]["@stripe/stripe-js"] = "^2.0.0"

        # Add common useful packages
        package["dependencies"]["lucide-react"] = "^0.300.0"  # Icons
        package["dependencies"]["clsx"] = "^2.1.0"  # Utility
        package["dependencies"]["tailwind-merge"] = "^2.2.0"  # Tailwind utility
        package["dependencies"]["class-variance-authority"] = "^0.7.0"  # Button variants

        # Add infrastructure packages for production-ready apps
        # State management
        package["dependencies"]["@upstash/redis"] = "^1.28.0"  # Serverless Redis

        # AI Gateway integration
        package["dependencies"]["ai"] = "^3.0.0"  # Vercel AI SDK
        package["dependencies"]["@ai-sdk/openai"] = "^0.0.15"  # OpenAI provider
        package["dependencies"]["@ai-sdk/anthropic"] = "^0.0.15"  # Anthropic provider

        # For agent/MCP apps: Add dockerode for container management
        if architecture.get("type") == "agent" or "docker" in str(architecture.get("features", [])).lower():
            package["dependencies"]["dockerode"] = "^4.0.2"  # Docker SDK
            package["devDependencies"]["@types/dockerode"] = "^3.3.0"

        return package

    def _write_file(self, path: Path, content: str):
        """Write content to file"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)

    def _tailwind_config(self) -> str:
        return '''/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
      },
    },
  },
  plugins: [],
}'''

    def _tsconfig(self) -> str:
        return '''{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}'''

    def _next_config(self) -> str:
        return '''/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: [],
  },
}

module.exports = nextConfig'''

    def _globals_css(self) -> str:
        return '''@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 0, 0, 0;
  --background-start-rgb: 214, 219, 220;
  --background-end-rgb: 255, 255, 255;
}

@media (prefers-color-scheme: dark) {
  :root {
    --foreground-rgb: 255, 255, 255;
    --background-start-rgb: 0, 0, 0;
    --background-end-rgb: 0, 0, 0;
  }
}

body {
  color: rgb(var(--foreground-rgb));
  background: linear-gradient(
      to bottom,
      transparent,
      rgb(var(--background-end-rgb))
    )
    rgb(var(--background-start-rgb));
}'''

    def _generate_readme(
        self,
        title: str,
        architecture: Dict[str, Any],
        video_analysis: Dict[str, Any]
    ) -> str:
        """Generate comprehensive README"""

        video_url = video_analysis.get("video_data", {}).get("video_url", "Unknown")

        return f'''# {title}

A full-stack {architecture['type']} built with {architecture['framework']}.

## Generated by UVAI
This project was AI-generated from video analysis using UVAI (Universal Video-to-Action Intelligence).

- **Source Video**: {video_url}
- **Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Framework**: {architecture['framework']}
- **Database**: {architecture.get('backend', {}).get('database', 'N/A')}
- **Auth**: {architecture.get('backend', {}).get('auth', 'N/A')}

## Features
{chr(10).join([f"- {f}" for f in architecture.get('features', [])])}

## Tech Stack
- **Frontend**: {architecture.get('frontend', {}).get('framework', 'Next.js')} with {architecture.get('frontend', {}).get('styling', 'Tailwind')}
- **Backend**: {architecture.get('backend', {}).get('type', 'API Routes')}
- **Database**: {architecture.get('backend', {}).get('database', 'Supabase')}
- **Auth**: {architecture.get('backend', {}).get('auth', 'NextAuth')}
- **Deployment**: {architecture.get('deployment', {}).get('platform', 'Vercel')}

## Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation
```bash
npm install
```

### Environment Setup
Copy `.env.example` to `.env.local` and fill in your values:
```bash
cp .env.example .env.local
```

### Development
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build
```bash
npm run build
```

### Deploy

This project includes automatic deployment to Vercel via GitHub Actions.

#### Setup GitHub Actions Deployment

1. **Install Vercel CLI** (if not already installed):
   ```bash
   npm install -g vercel
   ```

2. **Link your project to Vercel**:
   ```bash
   vercel link
   ```
   This creates `.vercel/project.json` with your project ID.

3. **Get your Vercel tokens**:
   - Go to https://vercel.com/account/tokens
   - Create a new token
   - Copy the token value

4. **Add GitHub Secrets**:
   Go to your GitHub repo → Settings → Secrets and variables → Actions

   Add these secrets:
   - `VERCEL_TOKEN`: Your Vercel API token
   - `VERCEL_ORG_ID`: Found in `.vercel/project.json`
   - `VERCEL_PROJECT_ID`: Found in `.vercel/project.json`

5. **Push to GitHub**:
   ```bash
   git push origin main
   ```

   The GitHub Action will automatically deploy to Vercel!

#### Manual Deployment

Alternatively, deploy manually:
```bash
vercel --prod
```

## Monetization
- **Model**: {architecture.get('monetization', {}).get('model', 'Freemium')}
- **Payment**: {architecture.get('monetization', {}).get('payment_processor', 'Stripe')}
- **Tiers**: {', '.join(architecture.get('monetization', {}).get('pricing_tiers', ['free', 'pro']))}

## License
MIT

---
*Generated with UVAI - Transform videos into products*
'''

    def _generate_env_example(self, architecture: Dict[str, Any]) -> str:
        """Generate .env.example file"""

        env_vars = [
            "# App",
            "NEXT_PUBLIC_APP_URL=http://localhost:3000",
            "",
            "# Infrastructure - State Management",
            "UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io",
            "UPSTASH_REDIS_REST_TOKEN=your-token-here",
            "",
            "# AI Gateway (Vercel AI SDK)",
            "OPENAI_API_KEY=sk-...",
            "ANTHROPIC_API_KEY=sk-ant-...",
            "",
        ]

        backend = architecture.get("backend", {})

        if backend.get("database") == "supabase":
            env_vars.extend([
                "# Supabase",
                "NEXT_PUBLIC_SUPABASE_URL=your-supabase-url",
                "NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key",
                "SUPABASE_SERVICE_ROLE_KEY=your-service-role-key",
                ""
            ])

        if backend.get("auth") == "nextauth":
            env_vars.extend([
                "# NextAuth",
                "NEXTAUTH_URL=http://localhost:3000",
                "NEXTAUTH_SECRET=your-secret-here",
                ""
            ])

        monetization = architecture.get("monetization", {})
        if monetization.get("payment_processor") == "stripe":
            # Inject real Stripe keys from environment if available
            stripe_secret = os.environ.get("STRIPE_SECRET_KEY", "sk_test_...")
            stripe_publishable = os.environ.get("STRIPE_PUBLISHABLE_KEY", "pk_test_...")

            env_vars.extend([
                "# Stripe (LIVE keys injected from environment)",
                f"STRIPE_SECRET_KEY={stripe_secret}",
                f"NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY={stripe_publishable}",
                "STRIPE_WEBHOOK_SECRET=whsec_...",
                ""
            ])

        return "\n".join(env_vars)

    def _generate_env_local(self, architecture: Dict[str, Any]) -> str:
        """Generate .env.local file with actual production keys for immediate deployment"""

        env_vars = [
            "# Production Environment Variables",
            "# Generated by UVAI - DO NOT COMMIT TO VERSION CONTROL",
            "",
            "# App",
            "NEXT_PUBLIC_APP_URL=http://localhost:3000",
            "",
        ]

        # Infrastructure - State Management
        upstash_url = os.environ.get("UPSTASH_REDIS_REST_URL", "")
        upstash_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
        if upstash_url and upstash_token:
            env_vars.extend([
                "# Infrastructure - State Management",
                f"UPSTASH_REDIS_REST_URL={upstash_url}",
                f"UPSTASH_REDIS_REST_TOKEN={upstash_token}",
                ""
            ])

        # AI Gateway
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if openai_key or anthropic_key:
            env_vars.extend([
                "# AI Gateway (Vercel AI SDK)",
                f"OPENAI_API_KEY={openai_key}",
                f"ANTHROPIC_API_KEY={anthropic_key}",
                ""
            ])

        backend = architecture.get("backend", {})

        if backend.get("database") == "supabase":
            supabase_url = os.environ.get("SUPABASE_URL", "")
            supabase_anon = os.environ.get("SUPABASE_ANON_KEY", "")
            supabase_service = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

            env_vars.extend([
                "# Supabase",
                f"NEXT_PUBLIC_SUPABASE_URL={supabase_url}",
                f"NEXT_PUBLIC_SUPABASE_ANON_KEY={supabase_anon}",
                f"SUPABASE_SERVICE_ROLE_KEY={supabase_service}",
                ""
            ])

        if backend.get("auth") == "nextauth":
            # Generate a secure random secret for NextAuth
            import secrets
            nextauth_secret = secrets.token_urlsafe(32)

            env_vars.extend([
                "# NextAuth",
                "NEXTAUTH_URL=http://localhost:3000",
                f"NEXTAUTH_SECRET={nextauth_secret}",
                ""
            ])

        monetization = architecture.get("monetization", {})
        if monetization.get("payment_processor") == "stripe":
            # Use real LIVE Stripe keys from environment
            stripe_secret = os.environ.get("STRIPE_SECRET_KEY", "")
            stripe_publishable = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")

            if stripe_secret and stripe_publishable:
                env_vars.extend([
                    "# Stripe LIVE Keys",
                    f"STRIPE_SECRET_KEY={stripe_secret}",
                    f"NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY={stripe_publishable}",
                    "STRIPE_WEBHOOK_SECRET=whsec_configure_in_stripe_dashboard",
                    ""
                ])
            else:
                env_vars.extend([
                    "# Stripe (keys not found in environment)",
                    "STRIPE_SECRET_KEY=",
                    "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=",
                    "STRIPE_WEBHOOK_SECRET=",
                    ""
                ])

        return "\n".join(env_vars)

    def _gitignore(self) -> str:
        return '''# Dependencies
/node_modules
/.pnp
.pnp.js
.yarn/install-state.gz

# Testing
/coverage

# Next.js
/.next/
/out/

# Production
/build

# Misc
.DS_Store
*.pem

# Debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Local env files
.env*.local
.env

# Vercel
.vercel

# TypeScript
*.tsbuildinfo
next-env.d.ts
'''

    def _github_actions_deploy(self) -> str:
        """Generate GitHub Actions workflow for auto-deployment to Vercel"""
        return '''name: Deploy to Vercel

on:
  push:
    branches:
      - main
      - master
  pull_request:
    branches:
      - main
      - master

env:
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install Vercel CLI
        run: npm install --global vercel@latest

      - name: Pull Vercel Environment Information
        run: vercel pull --yes --environment=production --token=${{ secrets.VERCEL_TOKEN }}

      - name: Build Project Artifacts
        run: vercel build --prod --token=${{ secrets.VERCEL_TOKEN }}

      - name: Deploy Project Artifacts to Vercel
        run: vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }}

      - name: Comment PR with deployment URL
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✅ Deployed to Vercel! Check your deployment at https://vercel.com'
            })
'''

    async def fix_build_errors(
        self,
        project_path: Path,
        errors: List[str],
        suggested_fixes: List[str]
    ) -> Dict[str, Any]:
        """
        Use AI to fix build errors in generated code.

        Args:
            project_path: Path to the project
            errors: List of build error messages
            suggested_fixes: List of suggested resolutions from skill database

        Returns:
            Dict with fixed files and status
        """
        if not self.client:
            return {"success": False, "reason": "Gemini client not available"}

        logger.info(f"🔧 AI auto-fix: Attempting to fix {len(errors)} build errors")

        # Identify files with errors
        error_files = set()
        for error in errors:
            # Extract file paths from error messages
            for part in error.split():
                if ".tsx" in part or ".ts" in part or ".js" in part:
                    # Clean up the path
                    file_path = part.split(":")[0].strip("()'\"")
                    if file_path:
                        error_files.add(file_path)

        if not error_files:
            # Try common problem files
            error_files = {"src/app/page.tsx", "src/components/Button.tsx"}

        fixed_files = []
        for rel_path in error_files:
            file_path = project_path / rel_path
            if not file_path.exists():
                continue

            # Read current file content
            current_content = file_path.read_text()

            # Build fix prompt
            fix_prompt = f"""You are a TypeScript/Next.js expert. Fix the following code that has build errors.

ERRORS:
{chr(10).join(errors[:10])}

SUGGESTED FIXES:
{chr(10).join(suggested_fixes[:5]) if suggested_fixes else "Apply standard TypeScript/Next.js best practices"}

CURRENT CODE ({rel_path}):
```typescript
{current_content[:3000]}
```

Return ONLY the fixed code, no explanations. Ensure:
1. All imports are correct
2. Types are properly defined
3. No implicit any types
4. Client components have 'use client' directive if using hooks
5. Code compiles without errors"""

            try:
                response = self.client.models.generate_content(
                    model="gemini-3-pro-preview",
                    contents=fix_prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=1.0,  # Gemini 3 requires temp=1.0
                        max_output_tokens=4096
                        # Gemini 3 Pro uses HIGH thinking by default - cannot be disabled
                    )
                )

                # Handle Gemini 3's thought_signature responses - extract text from parts if needed
                response_text = response.text
                if response_text is None:
                    # Try extracting from parts directly
                    if response.candidates and response.candidates[0].content.parts:
                        text_parts = [p.text for p in response.candidates[0].content.parts if hasattr(p, 'text') and p.text]
                        response_text = "\n".join(text_parts) if text_parts else None

                if not response_text:
                    logger.warning(f"⚠️ Gemini returned no text for {rel_path}, skipping")
                    continue

                fixed_code = response_text.strip()

                # Extract code from markdown if present
                if "```" in fixed_code:
                    code_blocks = fixed_code.split("```")
                    for i, block in enumerate(code_blocks):
                        if i % 2 == 1:  # Odd indices are code blocks
                            # Remove language identifier
                            lines = block.split("\n")
                            if lines[0].strip() in ["typescript", "tsx", "javascript", "js"]:
                                fixed_code = "\n".join(lines[1:])
                            else:
                                fixed_code = block
                            break

                # Write fixed content
                file_path.write_text(fixed_code)
                fixed_files.append(rel_path)
                logger.info(f"✅ Fixed: {rel_path}")

            except Exception as e:
                logger.warning(f"⚠️ Failed to fix {rel_path}: {e}")

        return {
            "success": len(fixed_files) > 0,
            "fixed_files": fixed_files,
            "total_errors": len(errors)
        }

    async def _generate_turborepo_monorepo(
        self,
        project_path: Path,
        architecture: Dict[str, Any],
        video_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate Turborepo monorepo infrastructure platform"""
        logger.info("🏗️  Generating Turborepo monorepo structure...")

        files_created = []
        extracted = video_analysis.get("extracted_info", {})
        title = extracted.get("title", "AI Infrastructure Platform")

        # 1. Create turbo.json
        turbo_config = {
            "$schema": "https://turbo.build/schema.json",
            "globalDependencies": ["**/.env.*local"],
            "pipeline": {
                "build": {
                    "dependsOn": ["^build"],
                    "outputs": [".next/**", "!.next/cache/**"]
                },
                "lint": {},
                "dev": {
                    "cache": False,
                    "persistent": True
                }
            }
        }
        self._write_file(project_path / "turbo.json", json.dumps(turbo_config, indent=2))
        files_created.append("turbo.json")

        # 2. Create root package.json with workspaces
        root_package = {
            "name": "infrastructure-platform",
            "version": "0.0.0",
            "private": True,
            "workspaces": ["apps/*", "packages/*"],
            "scripts": {
                "build": "turbo run build",
                "dev": "turbo run dev",
                "lint": "turbo run lint",
                "format": "prettier --write \"**/*.{ts,tsx,md}\""
            },
            "devDependencies": {
                "prettier": "^3.0.0",
                "turbo": "latest"
            }
        }
        self._write_file(project_path / "package.json", json.dumps(root_package, indent=2))
        files_created.append("package.json")

        # 3. Create .gitignore
        self._write_file(project_path / ".gitignore", self._gitignore())
        files_created.append(".gitignore")

        # 4. Generate apps/web (main Next.js app with Docker integration)
        web_path = project_path / "apps" / "web"
        web_files = await self._generate_nextjs_project(web_path, architecture, video_analysis)
        files_created.extend([f"apps/web/{f}" for f in web_files])

        # 5. Generate packages/ui (shared UI components)
        ui_files = await self._generate_ui_package(project_path / "packages" / "ui", architecture)
        files_created.extend([f"packages/ui/{f}" for f in ui_files])

        # 6. Generate packages/eslint-config (shared configs)
        config_files = self._generate_eslint_config_package(project_path / "packages" / "eslint-config")
        files_created.extend([f"packages/eslint-config/{f}" for f in config_files])

        # 7. Generate packages/tsconfig (shared TypeScript configs)
        tsconfig_files = self._generate_tsconfig_package(project_path / "packages" / "tsconfig")
        files_created.extend([f"packages/tsconfig/{f}" for f in tsconfig_files])

        # 8. Generate packages/mcp-connectors (if agent or infrastructure type)
        if architecture.get("type") in ["agent", "infrastructure_platform"] or architecture.get("has_mcp", False):
            mcp_files = await self._generate_mcp_connectors_package(project_path / "packages" / "mcp-connectors", architecture)
            files_created.extend([f"packages/mcp-connectors/{f}" for f in mcp_files])

        # 9. Generate packages/workflows (Workflow.dev integration for durable execution)
        if architecture.get("type") in ["agent", "infrastructure_platform"] or architecture.get("has_workflows", False):
            workflow_files = await self._generate_workflows_package(project_path / "packages" / "workflows", architecture)
            files_created.extend([f"packages/workflows/{f}" for f in workflow_files])

        # 10. Generate packages/observability (OpenTelemetry integration)
        if architecture.get("type") in ["agent", "infrastructure_platform"] or architecture.get("has_observability", False):
            observability_files = await self._generate_observability_package(project_path / "packages" / "observability", architecture)
            files_created.extend([f"packages/observability/{f}" for f in observability_files])

        # 11. Generate packages/ai-gateway (Vercel AI SDK multi-model integration)
        if architecture.get("type") in ["agent", "infrastructure_platform"] or architecture.get("has_ai_gateway", False):
            ai_gateway_files = await self._generate_ai_gateway_package(project_path / "packages" / "ai-gateway", architecture)
            files_created.extend([f"packages/ai-gateway/{f}" for f in ai_gateway_files])

        # 12. Generate packages/logger (Comprehensive structured logging)
        if architecture.get("type") in ["agent", "infrastructure_platform"] or architecture.get("has_logging", False):
            logger_files = await self._generate_logger_package(project_path / "packages" / "logger", architecture)
            files_created.extend([f"packages/logger/{f}" for f in logger_files])

        # 13. Generate packages/error-handling (Phase 3.1: Error boundaries + retry logic)
        if architecture.get("type") in ["agent", "infrastructure_platform"] or architecture.get("has_error_handling", False):
            error_handling_files = await self._generate_error_handling_package(project_path / "packages" / "error-handling", architecture)
            files_created.extend([f"packages/error-handling/{f}" for f in error_handling_files])

        # 14. Generate packages/database (Phase 3.2: Prisma + migrations)
        if architecture.get("type") in ["agent", "infrastructure_platform"] or architecture.get("has_database", False):
            database_files = await self._generate_database_package(project_path / "packages" / "database", architecture)
            files_created.extend([f"packages/database/{f}" for f in database_files])

        # 15. Generate packages/config (Phase 3.3: Environment variable management)
        if architecture.get("type") in ["agent", "infrastructure_platform"] or architecture.get("has_config", False):
            config_files = await self._generate_config_package(project_path / "packages" / "config", architecture)
            files_created.extend([f"packages/config/{f}" for f in config_files])

        # 16. Generate README
        readme = self._generate_monorepo_readme(title, architecture, video_analysis)
        self._write_file(project_path / "README.md", readme)
        files_created.append("README.md")

        logger.info(f"✅ Generated Turborepo monorepo with {len(files_created)} files")
        return files_created

    async def _generate_ui_package(self, package_path: Path, architecture: Dict[str, Any]) -> List[str]:
        """Generate shared UI components package"""
        files_created = []

        # package.json
        package_json = {
            "name": "@repo/ui",
            "version": "0.0.0",
            "private": True,
            "exports": {
                "./button": "./src/button.tsx",
                "./card": "./src/card.tsx"
            },
            "scripts": {
                "lint": "eslint . --max-warnings 0",
                "generate:component": "turbo gen react-component"
            },
            "peerDependencies": {
                "react": "^18"
            },
            "devDependencies": {
                "@types/react": "^18",
                "typescript": "^5",
                "eslint": "^8"
            }
        }
        self._write_file(package_path / "package.json", json.dumps(package_json, indent=2))
        files_created.append("package.json")

        # Button component
        button_tsx = '''import * as React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline";
}

export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  className,
  children,
  ...props
}) => {
  const baseStyles = "px-4 py-2 rounded-md font-medium transition-colors";
  const variantStyles = {
    primary: "bg-blue-600 text-white hover:bg-blue-700",
    secondary: "bg-gray-200 text-gray-900 hover:bg-gray-300",
    outline: "border border-gray-300 text-gray-700 hover:bg-gray-50"
  };

  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${className || ""}`}
      {...props}
    >
      {children}
    </button>
  );
};
'''
        self._write_file(package_path / "src/button.tsx", button_tsx)
        files_created.append("src/button.tsx")

        # Card component
        card_tsx = '''import * as React from "react";

export interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ children, className }) => {
  return (
    <div className={`rounded-lg border bg-white p-6 shadow-sm ${className || ""}`}>
      {children}
    </div>
  );
};
'''
        self._write_file(package_path / "src/card.tsx", card_tsx)
        files_created.append("src/card.tsx")

        # tsconfig.json
        tsconfig = {
            "extends": "@repo/typescript-config/react-library.json",
            "compilerOptions": {
                "outDir": "dist"
            },
            "include": ["src"],
            "exclude": ["node_modules", "dist"]
        }
        self._write_file(package_path / "tsconfig.json", json.dumps(tsconfig, indent=2))
        files_created.append("tsconfig.json")

        return files_created

    def _generate_eslint_config_package(self, package_path: Path) -> List[str]:
        """Generate shared ESLint config package"""
        files_created = []

        # package.json
        package_json = {
            "name": "@repo/eslint-config",
            "version": "0.0.0",
            "private": True,
            "main": "index.js",
            "devDependencies": {
                "eslint": "^8",
                "eslint-config-next": "14.2.0",
                "eslint-config-prettier": "^9.0.0"
            }
        }
        self._write_file(package_path / "package.json", json.dumps(package_json, indent=2))
        files_created.append("package.json")

        # index.js
        eslint_config = '''module.exports = {
  extends: ["next", "prettier"],
  rules: {
    "@next/next/no-html-link-for-pages": "off"
  }
};
'''
        self._write_file(package_path / "index.js", eslint_config)
        files_created.append("index.js")

        return files_created

    def _generate_tsconfig_package(self, package_path: Path) -> List[str]:
        """Generate shared TypeScript config package"""
        files_created = []

        # package.json
        package_json = {
            "name": "@repo/typescript-config",
            "version": "0.0.0",
            "private": True,
            "files": ["base.json", "nextjs.json", "react-library.json"]
        }
        self._write_file(package_path / "package.json", json.dumps(package_json, indent=2))
        files_created.append("package.json")

        # base.json
        base_config = {
            "$schema": "https://json.schemastore.org/tsconfig",
            "compilerOptions": {
                "esModuleInterop": True,
                "skipLibCheck": True,
                "target": "es2022",
                "allowJs": True,
                "resolveJsonModule": True,
                "moduleDetection": "force",
                "isolatedModules": True,
                "strict": True,
                "noUncheckedIndexedAccess": True
            }
        }
        self._write_file(package_path / "base.json", json.dumps(base_config, indent=2))
        files_created.append("base.json")

        # nextjs.json
        nextjs_config = {
            "$schema": "https://json.schemastore.org/tsconfig",
            "extends": "./base.json",
            "compilerOptions": {
                "lib": ["dom", "dom.iterable", "esnext"],
                "module": "esnext",
                "moduleResolution": "bundler",
                "noEmit": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [{"name": "next"}],
                "paths": {"@/*": ["./src/*"]}
            }
        }
        self._write_file(package_path / "nextjs.json", json.dumps(nextjs_config, indent=2))
        files_created.append("nextjs.json")

        # react-library.json
        react_lib_config = {
            "$schema": "https://json.schemastore.org/tsconfig",
            "extends": "./base.json",
            "compilerOptions": {
                "lib": ["ES2023"],
                "module": "ESNext",
                "moduleResolution": "bundler",
                "jsx": "react-jsx",
                "declaration": True,
                "declarationMap": True,
                "outDir": "dist"
            }
        }
        self._write_file(package_path / "react-library.json", json.dumps(react_lib_config, indent=2))
        files_created.append("react-library.json")

        return files_created

    def _generate_monorepo_readme(self, title: str, architecture: Dict[str, Any], video_analysis: Dict[str, Any]) -> str:
        """Generate Turborepo monorepo README"""
        video_url = video_analysis.get("video_data", {}).get("video_url", "Unknown")

        return f'''# {title} - Infrastructure Platform

AI-generated Turborepo monorepo from video analysis.

## Generated by EventRelay
- **Source Video**: {video_url}
- **Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Architecture**: Turborepo monorepo

## What's Inside?

This Turborepo includes the following packages/apps:

### Apps
- `web`: Main Next.js application with functional Docker integration
- Future: `docs`, `workflows`, `ai-gateway`

### Packages
- `@repo/ui`: Shared React UI component library
- `@repo/eslint-config`: Shared ESLint configurations
- `@repo/typescript-config`: Shared TypeScript configurations

## Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation
```bash
npm install
```

### Development
```bash
npm run dev
```

### Build
```bash
npm run build
```

### Deploy
Each app can be deployed independently to Vercel:
```bash
cd apps/web
vercel --prod
```

## Turborepo Features

- **Incremental builds**: Only rebuild what changed
- **Content-aware hashing**: Avoid rebuilding when unchanged
- **Parallel execution**: Run tasks across packages simultaneously
- **Remote caching**: Share build cache across team/CI

## Learn More

- [Turborepo Documentation](https://turbo.build/repo/docs)
- [Next.js Documentation](https://nextjs.org/docs)

---
*Generated with EventRelay AI Infrastructure Generator*
'''

    async def _generate_mcp_connectors_package(self, package_path: Path, architecture: Dict[str, Any]) -> List[str]:
        """Generate MCP connectors package with Postgres, GitHub, and Slack connectors"""
        logger.info("🔌 Generating MCP connectors package...")
        files_created = []

        # package.json
        package_json = {
            "name": "@repo/mcp-connectors",
            "version": "0.0.0",
            "private": True,
            "main": "dist/index.js",
            "types": "dist/index.d.ts",
            "exports": {
                "./postgres": "./dist/postgres.js",
                "./github": "./dist/github.js",
                "./slack": "./dist/slack.js"
            },
            "scripts": {
                "build": "tsc",
                "dev": "tsc --watch",
                "lint": "eslint . --max-warnings 0"
            },
            "dependencies": {
                "pg": "^8.11.0",
                "@octokit/rest": "^20.0.0",
                "@slack/web-api": "^6.9.0"
            },
            "devDependencies": {
                "@types/pg": "^8.10.0",
                "@types/node": "^20",
                "typescript": "^5",
                "eslint": "^8"
            }
        }
        self._write_file(package_path / "package.json", json.dumps(package_json, indent=2))
        files_created.append("package.json")

        # tsconfig.json
        tsconfig = {
            "extends": "@repo/typescript-config/base.json",
            "compilerOptions": {
                "outDir": "dist",
                "rootDir": "src",
                "declaration": True,
                "declarationMap": True
            },
            "include": ["src"],
            "exclude": ["node_modules", "dist"]
        }
        self._write_file(package_path / "tsconfig.json", json.dumps(tsconfig, indent=2))
        files_created.append("tsconfig.json")

        # Generate Postgres connector
        postgres_code = self._generate_postgres_connector()
        self._write_file(package_path / "src/postgres.ts", postgres_code)
        files_created.append("src/postgres.ts")

        # Generate GitHub connector
        github_code = self._generate_github_connector()
        self._write_file(package_path / "src/github.ts", github_code)
        files_created.append("src/github.ts")

        # Generate Slack connector
        slack_code = self._generate_slack_connector()
        self._write_file(package_path / "src/slack.ts", slack_code)
        files_created.append("src/slack.ts")

        # Generate index barrel export
        index_ts = '''/**
 * MCP Connectors - Production-ready connectors for Postgres, GitHub, and Slack
 * @packageDocumentation
 */

export { PostgresConnector, type PostgresConfig, type PostgresToolName } from './postgres';
export { GitHubConnector, type GitHubConfig, type GitHubToolName } from './github';
export { SlackConnector, type SlackConfig, type SlackToolName } from './slack';
'''
        self._write_file(package_path / "src/index.ts", index_ts)
        files_created.append("src/index.ts")

        # README
        readme = '''# MCP Connectors

Production-ready Model Context Protocol (MCP) connectors for external services.

## Available Connectors

### Postgres Connector
Database operations with connection pooling and error handling.

```typescript
import { PostgresConnector } from '@repo/mcp-connectors/postgres';

const postgres = new PostgresConnector({
  connectionString: process.env.DATABASE_URL,
  maxConnections: 20
});

const result = await postgres.executeTool('query', {
  query: 'SELECT * FROM users WHERE id = $1',
  params: [userId]
});
```

### GitHub Connector
GitHub API integration with rate limit handling.

```typescript
import { GitHubConnector } from '@repo/mcp-connectors/github';

const github = new GitHubConnector({
  token: process.env.GITHUB_TOKEN,
  owner: 'your-org',
  repo: 'your-repo'
});

const issues = await github.executeTool('list_issues', {
  state: 'open',
  labels: ['bug']
});
```

### Slack Connector
Slack messaging and channel management.

```typescript
import { SlackConnector } from '@repo/mcp-connectors/slack';

const slack = new SlackConnector({
  token: process.env.SLACK_BOT_TOKEN
});

await slack.executeTool('send_message', {
  channel: '#general',
  text: 'Hello from MCP!'
});
```

## Features

- **Type Safety**: Full TypeScript support with type definitions
- **Error Handling**: Production-ready error handling and logging
- **Connection Management**: Automatic connection pooling and cleanup
- **MCP Protocol**: Follows Model Context Protocol standards

## Environment Variables

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/db
GITHUB_TOKEN=ghp_...
SLACK_BOT_TOKEN=xoxb-...
```
'''
        self._write_file(package_path / "README.md", readme)
        files_created.append("README.md")

        logger.info(f"✅ Generated MCP connectors with {len(files_created)} files")
        return files_created

    def _generate_postgres_connector(self) -> str:
        """Generate Postgres MCP connector with type safety and connection pooling"""
        return '''import { Pool, PoolClient, QueryResult } from 'pg';

/**
 * Postgres connector configuration
 */
export interface PostgresConfig {
  connectionString: string;
  maxConnections?: number;
  ssl?: boolean;
}

/**
 * Available Postgres tool names
 */
export type PostgresToolName =
  | 'query'
  | 'execute'
  | 'transaction'
  | 'get_schema'
  | 'get_table_info';

/**
 * Tool arguments for each Postgres tool
 */
export interface PostgresToolArguments {
  query: { query: string; params?: any[] };
  execute: { query: string; params?: any[] };
  transaction: { queries: Array<{ query: string; params?: any[] }> };
  get_schema: { schema?: string };
  get_table_info: { table: string; schema?: string };
}

/**
 * MCP Connector for PostgreSQL databases
 * Provides database operations with connection pooling and error handling
 */
export class PostgresConnector {
  private pool: Pool;
  private config: PostgresConfig;

  constructor(config: PostgresConfig) {
    this.config = config;
    this.pool = new Pool({
      connectionString: config.connectionString,
      max: config.maxConnections || 20,
      ssl: config.ssl ? { rejectUnauthorized: false } : undefined,
    });
  }

  /**
   * List available tools with their schemas
   */
  async listTools() {
    return {
      tools: [
        {
          name: 'query',
          description: 'Execute a SELECT query and return results',
          inputSchema: {
            type: 'object',
            properties: {
              query: { type: 'string', description: 'SQL SELECT query' },
              params: { type: 'array', description: 'Query parameters (optional)' }
            },
            required: ['query']
          }
        },
        {
          name: 'execute',
          description: 'Execute INSERT, UPDATE, or DELETE statement',
          inputSchema: {
            type: 'object',
            properties: {
              query: { type: 'string', description: 'SQL statement' },
              params: { type: 'array', description: 'Query parameters (optional)' }
            },
            required: ['query']
          }
        },
        {
          name: 'transaction',
          description: 'Execute multiple queries in a transaction',
          inputSchema: {
            type: 'object',
            properties: {
              queries: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    query: { type: 'string' },
                    params: { type: 'array' }
                  }
                }
              }
            },
            required: ['queries']
          }
        },
        {
          name: 'get_schema',
          description: 'Get database schema information',
          inputSchema: {
            type: 'object',
            properties: {
              schema: { type: 'string', description: 'Schema name (defaults to public)' }
            }
          }
        },
        {
          name: 'get_table_info',
          description: 'Get detailed information about a table',
          inputSchema: {
            type: 'object',
            properties: {
              table: { type: 'string', description: 'Table name' },
              schema: { type: 'string', description: 'Schema name (optional)' }
            },
            required: ['table']
          }
        }
      ]
    };
  }

  /**
   * Execute a tool by name
   */
  async executeTool<T extends PostgresToolName>(
    name: T,
    args: PostgresToolArguments[T]
  ): Promise<any> {
    try {
      switch (name) {
        case 'query':
          return await this.executeQuery(args as PostgresToolArguments['query']);
        case 'execute':
          return await this.executeStatement(args as PostgresToolArguments['execute']);
        case 'transaction':
          return await this.executeTransaction(args as PostgresToolArguments['transaction']);
        case 'get_schema':
          return await this.getSchema(args as PostgresToolArguments['get_schema']);
        case 'get_table_info':
          return await this.getTableInfo(args as PostgresToolArguments['get_table_info']);
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error: any) {
      console.error(`Error executing tool ${name}:`, error);
      throw new Error(`Database operation failed: ${error.message}`);
    }
  }

  private async executeQuery(args: { query: string; params?: any[] }): Promise<QueryResult> {
    const client = await this.pool.connect();
    try {
      return await client.query(args.query, args.params || []);
    } finally {
      client.release();
    }
  }

  private async executeStatement(args: { query: string; params?: any[] }): Promise<{ rowCount: number }> {
    const result = await this.executeQuery(args);
    return { rowCount: result.rowCount || 0 };
  }

  private async executeTransaction(args: { queries: Array<{ query: string; params?: any[] }> }): Promise<{ success: boolean; results: any[] }> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const results = [];
      for (const q of args.queries) {
        const result = await client.query(q.query, q.params || []);
        results.push(result);
      }
      await client.query('COMMIT');
      return { success: true, results };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async getSchema(args: { schema?: string }): Promise<any> {
    const schema = args.schema || 'public';
    const query = `
      SELECT table_name, column_name, data_type
      FROM information_schema.columns
      WHERE table_schema = $1
      ORDER BY table_name, ordinal_position
    `;
    return await this.executeQuery({ query, params: [schema] });
  }

  private async getTableInfo(args: { table: string; schema?: string }): Promise<any> {
    const schema = args.schema || 'public';
    const query = `
      SELECT column_name, data_type, is_nullable, column_default
      FROM information_schema.columns
      WHERE table_schema = $1 AND table_name = $2
      ORDER BY ordinal_position
    `;
    return await this.executeQuery({ query, params: [schema, args.table] });
  }

  /**
   * Close all connections
   */
  async close(): Promise<void> {
    await this.pool.end();
  }
}
'''

    def _generate_github_connector(self) -> str:
        """Generate GitHub MCP connector with Octokit integration"""
        return '''import { Octokit } from '@octokit/rest';

/**
 * GitHub connector configuration
 */
export interface GitHubConfig {
  token: string;
  owner: string;
  repo: string;
}

/**
 * Available GitHub tool names
 */
export type GitHubToolName =
  | 'list_issues'
  | 'create_issue'
  | 'update_issue'
  | 'list_prs'
  | 'create_pr'
  | 'get_repo_info'
  | 'list_branches';

/**
 * Tool arguments for each GitHub tool
 */
export interface GitHubToolArguments {
  list_issues: { state?: 'open' | 'closed' | 'all'; labels?: string[]; page?: number };
  create_issue: { title: string; body: string; labels?: string[] };
  update_issue: { issue_number: number; title?: string; body?: string; state?: 'open' | 'closed' };
  list_prs: { state?: 'open' | 'closed' | 'all'; page?: number };
  create_pr: { title: string; body: string; head: string; base: string };
  get_repo_info: {};
  list_branches: {};
}

/**
 * MCP Connector for GitHub API
 * Provides issue tracking, PR management, and repository operations
 */
export class GitHubConnector {
  private octokit: Octokit;
  private owner: string;
  private repo: string;

  constructor(config: GitHubConfig) {
    this.octokit = new Octokit({ auth: config.token });
    this.owner = config.owner;
    this.repo = config.repo;
  }

  /**
   * List available tools with their schemas
   */
  async listTools() {
    return {
      tools: [
        {
          name: 'list_issues',
          description: 'List repository issues',
          inputSchema: {
            type: 'object',
            properties: {
              state: { type: 'string', enum: ['open', 'closed', 'all'], default: 'open' },
              labels: { type: 'array', items: { type: 'string' } },
              page: { type: 'number', default: 1 }
            }
          }
        },
        {
          name: 'create_issue',
          description: 'Create a new issue',
          inputSchema: {
            type: 'object',
            properties: {
              title: { type: 'string' },
              body: { type: 'string' },
              labels: { type: 'array', items: { type: 'string' } }
            },
            required: ['title', 'body']
          }
        },
        {
          name: 'update_issue',
          description: 'Update an existing issue',
          inputSchema: {
            type: 'object',
            properties: {
              issue_number: { type: 'number' },
              title: { type: 'string' },
              body: { type: 'string' },
              state: { type: 'string', enum: ['open', 'closed'] }
            },
            required: ['issue_number']
          }
        },
        {
          name: 'list_prs',
          description: 'List pull requests',
          inputSchema: {
            type: 'object',
            properties: {
              state: { type: 'string', enum: ['open', 'closed', 'all'], default: 'open' },
              page: { type: 'number', default: 1 }
            }
          }
        },
        {
          name: 'create_pr',
          description: 'Create a new pull request',
          inputSchema: {
            type: 'object',
            properties: {
              title: { type: 'string' },
              body: { type: 'string' },
              head: { type: 'string', description: 'Branch with changes' },
              base: { type: 'string', description: 'Branch to merge into' }
            },
            required: ['title', 'body', 'head', 'base']
          }
        },
        {
          name: 'get_repo_info',
          description: 'Get repository information',
          inputSchema: { type: 'object' }
        },
        {
          name: 'list_branches',
          description: 'List repository branches',
          inputSchema: { type: 'object' }
        }
      ]
    };
  }

  /**
   * Execute a tool by name
   */
  async executeTool<T extends GitHubToolName>(
    name: T,
    args: GitHubToolArguments[T]
  ): Promise<any> {
    try {
      switch (name) {
        case 'list_issues':
          return await this.listIssues(args as GitHubToolArguments['list_issues']);
        case 'create_issue':
          return await this.createIssue(args as GitHubToolArguments['create_issue']);
        case 'update_issue':
          return await this.updateIssue(args as GitHubToolArguments['update_issue']);
        case 'list_prs':
          return await this.listPRs(args as GitHubToolArguments['list_prs']);
        case 'create_pr':
          return await this.createPR(args as GitHubToolArguments['create_pr']);
        case 'get_repo_info':
          return await this.getRepoInfo();
        case 'list_branches':
          return await this.listBranches();
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error: any) {
      console.error(`Error executing tool ${name}:`, error);
      throw new Error(`GitHub API operation failed: ${error.message}`);
    }
  }

  private async listIssues(args: { state?: 'open' | 'closed' | 'all'; labels?: string[]; page?: number }) {
    const response = await this.octokit.issues.listForRepo({
      owner: this.owner,
      repo: this.repo,
      state: args.state || 'open',
      labels: args.labels?.join(','),
      page: args.page || 1,
      per_page: 30
    });
    return response.data;
  }

  private async createIssue(args: { title: string; body: string; labels?: string[] }) {
    const response = await this.octokit.issues.create({
      owner: this.owner,
      repo: this.repo,
      title: args.title,
      body: args.body,
      labels: args.labels
    });
    return response.data;
  }

  private async updateIssue(args: { issue_number: number; title?: string; body?: string; state?: 'open' | 'closed' }) {
    const response = await this.octokit.issues.update({
      owner: this.owner,
      repo: this.repo,
      issue_number: args.issue_number,
      title: args.title,
      body: args.body,
      state: args.state
    });
    return response.data;
  }

  private async listPRs(args: { state?: 'open' | 'closed' | 'all'; page?: number }) {
    const response = await this.octokit.pulls.list({
      owner: this.owner,
      repo: this.repo,
      state: args.state || 'open',
      page: args.page || 1,
      per_page: 30
    });
    return response.data;
  }

  private async createPR(args: { title: string; body: string; head: string; base: string }) {
    const response = await this.octokit.pulls.create({
      owner: this.owner,
      repo: this.repo,
      title: args.title,
      body: args.body,
      head: args.head,
      base: args.base
    });
    return response.data;
  }

  private async getRepoInfo() {
    const response = await this.octokit.repos.get({
      owner: this.owner,
      repo: this.repo
    });
    return response.data;
  }

  private async listBranches() {
    const response = await this.octokit.repos.listBranches({
      owner: this.owner,
      repo: this.repo
    });
    return response.data;
  }
}
'''

    def _generate_slack_connector(self) -> str:
        """Generate Slack MCP connector with Web API integration"""
        return '''import { WebClient } from '@slack/web-api';

/**
 * Slack connector configuration
 */
export interface SlackConfig {
  token: string;
}

/**
 * Available Slack tool names
 */
export type SlackToolName =
  | 'send_message'
  | 'list_channels'
  | 'create_channel'
  | 'get_user_info'
  | 'upload_file'
  | 'get_channel_history';

/**
 * Tool arguments for each Slack tool
 */
export interface SlackToolArguments {
  send_message: { channel: string; text: string; blocks?: any[] };
  list_channels: { types?: string };
  create_channel: { name: string; is_private?: boolean };
  get_user_info: { user_id: string };
  upload_file: { channels: string; file: Buffer; filename: string; title?: string };
  get_channel_history: { channel: string; limit?: number };
}

/**
 * MCP Connector for Slack Web API
 * Provides messaging, channel management, and user operations
 */
export class SlackConnector {
  private client: WebClient;

  constructor(config: SlackConfig) {
    this.client = new WebClient(config.token);
  }

  /**
   * List available tools with their schemas
   */
  async listTools() {
    return {
      tools: [
        {
          name: 'send_message',
          description: 'Send a message to a channel',
          inputSchema: {
            type: 'object',
            properties: {
              channel: { type: 'string', description: 'Channel ID or name' },
              text: { type: 'string', description: 'Message text' },
              blocks: { type: 'array', description: 'Block Kit blocks (optional)' }
            },
            required: ['channel', 'text']
          }
        },
        {
          name: 'list_channels',
          description: 'List workspace channels',
          inputSchema: {
            type: 'object',
            properties: {
              types: { type: 'string', description: 'Channel types (public_channel, private_channel, etc.)', default: 'public_channel' }
            }
          }
        },
        {
          name: 'create_channel',
          description: 'Create a new channel',
          inputSchema: {
            type: 'object',
            properties: {
              name: { type: 'string', description: 'Channel name' },
              is_private: { type: 'boolean', default: false }
            },
            required: ['name']
          }
        },
        {
          name: 'get_user_info',
          description: 'Get information about a user',
          inputSchema: {
            type: 'object',
            properties: {
              user_id: { type: 'string', description: 'User ID' }
            },
            required: ['user_id']
          }
        },
        {
          name: 'upload_file',
          description: 'Upload a file to a channel',
          inputSchema: {
            type: 'object',
            properties: {
              channels: { type: 'string', description: 'Comma-separated channel IDs' },
              file: { type: 'string', description: 'File buffer' },
              filename: { type: 'string', description: 'File name' },
              title: { type: 'string', description: 'File title (optional)' }
            },
            required: ['channels', 'file', 'filename']
          }
        },
        {
          name: 'get_channel_history',
          description: 'Get message history from a channel',
          inputSchema: {
            type: 'object',
            properties: {
              channel: { type: 'string', description: 'Channel ID' },
              limit: { type: 'number', default: 100 }
            },
            required: ['channel']
          }
        }
      ]
    };
  }

  /**
   * Execute a tool by name
   */
  async executeTool<T extends SlackToolName>(
    name: T,
    args: SlackToolArguments[T]
  ): Promise<any> {
    try {
      switch (name) {
        case 'send_message':
          return await this.sendMessage(args as SlackToolArguments['send_message']);
        case 'list_channels':
          return await this.listChannels(args as SlackToolArguments['list_channels']);
        case 'create_channel':
          return await this.createChannel(args as SlackToolArguments['create_channel']);
        case 'get_user_info':
          return await this.getUserInfo(args as SlackToolArguments['get_user_info']);
        case 'upload_file':
          return await this.uploadFile(args as SlackToolArguments['upload_file']);
        case 'get_channel_history':
          return await this.getChannelHistory(args as SlackToolArguments['get_channel_history']);
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error: any) {
      console.error(`Error executing tool ${name}:`, error);
      throw new Error(`Slack API operation failed: ${error.message}`);
    }
  }

  private async sendMessage(args: { channel: string; text: string; blocks?: any[] }) {
    const result = await this.client.chat.postMessage({
      channel: args.channel,
      text: args.text,
      blocks: args.blocks
    });
    return result;
  }

  private async listChannels(args: { types?: string }) {
    const result = await this.client.conversations.list({
      types: args.types || 'public_channel'
    });
    return result.channels;
  }

  private async createChannel(args: { name: string; is_private?: boolean }) {
    const result = await this.client.conversations.create({
      name: args.name,
      is_private: args.is_private || false
    });
    return result.channel;
  }

  private async getUserInfo(args: { user_id: string }) {
    const result = await this.client.users.info({
      user: args.user_id
    });
    return result.user;
  }

  private async uploadFile(args: { channels: string; file: Buffer; filename: string; title?: string }) {
    const result = await this.client.files.uploadV2({
      channels: args.channels,
      file: args.file,
      filename: args.filename,
      title: args.title
    });
    return result;
  }

  private async getChannelHistory(args: { channel: string; limit?: number }) {
    const result = await this.client.conversations.history({
      channel: args.channel,
      limit: args.limit || 100
    });
    return result.messages;
  }
}
'''

    async def _generate_workflows_package(self, package_path: Path, architecture: Dict[str, Any]) -> List[str]:
        """Generate Workflow.dev durable workflows package"""
        logger.info("⚡ Generating Workflow.dev durable workflows package...")
        files_created = []

        # package.json
        package_json = {
            "name": "@repo/workflows",
            "version": "0.0.0",
            "private": True,
            "main": "dist/index.js",
            "types": "dist/index.d.ts",
            "exports": {
                "./data-processing": "./dist/data-processing.js",
                "./mcp-orchestration": "./dist/mcp-orchestration.js"
            },
            "scripts": {
                "build": "tsc",
                "dev": "tsc --watch",
                "lint": "eslint . --max-warnings 0"
            },
            "dependencies": {
                "@vercel/workflow": "^0.3.0"
            },
            "devDependencies": {
                "@types/node": "^20",
                "typescript": "^5",
                "eslint": "^8"
            }
        }
        self._write_file(package_path / "package.json", json.dumps(package_json, indent=2))
        files_created.append("package.json")

        # tsconfig.json
        tsconfig = {
            "extends": "@repo/typescript-config/base.json",
            "compilerOptions": {
                "outDir": "dist",
                "rootDir": "src",
                "declaration": True,
                "declarationMap": True
            },
            "include": ["src"],
            "exclude": ["node_modules", "dist"]
        }
        self._write_file(package_path / "tsconfig.json", json.dumps(tsconfig, indent=2))
        files_created.append("tsconfig.json")

        # Data processing workflow example
        data_processing_ts = '''import { Workflow } from '@vercel/workflow';

/**
 * Durable data processing workflow
 * Survives deployments, crashes, and long-running operations
 */
export const dataProcessingWorkflow = new Workflow('data-processing')
  .step('fetch-data', async (context) => {
    'use step';

    // Fetch data from external source
    const response = await fetch(context.input.dataUrl);
    const rawData = await response.json();

    return { rawData, timestamp: Date.now() };
  })
  .step('transform-data', async (context, prevResult) => {
    'use step';

    // Transform and validate data
    const transformed = prevResult.rawData.map((item: any) => ({
      id: item.id,
      value: item.value * 2,
      processed: true
    }));

    return { transformed, count: transformed.length };
  })
  .step('store-results', async (context, prevResult) => {
    'use step';

    // Store results durably
    // This step will retry on failure
    await fetch(context.input.storageUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prevResult.transformed)
    });

    return {
      success: true,
      itemsProcessed: prevResult.count,
      completedAt: new Date().toISOString()
    };
  });

/**
 * Execute the workflow
 */
export async function runDataProcessing(dataUrl: string, storageUrl: string) {
  return await dataProcessingWorkflow.run({
    dataUrl,
    storageUrl
  });
}
'''
        self._write_file(package_path / "src/data-processing.ts", data_processing_ts)
        files_created.append("src/data-processing.ts")

        # MCP orchestration workflow (integrates with MCP connectors)
        mcp_orchestration_ts = '''import { Workflow } from '@vercel/workflow';
import type { PostgresConnector } from '@repo/mcp-connectors/postgres';
import type { GitHubConnector } from '@repo/mcp-connectors/github';
import type { SlackConnector } from '@repo/mcp-connectors/slack';

/**
 * Orchestrate MCP connectors with durable workflows
 * Example: Sync GitHub issues to database and notify Slack
 */
export const mcpOrchestrationWorkflow = new Workflow('mcp-orchestration')
  .step('fetch-github-issues', async (context) => {
    'use step';

    const github: GitHubConnector = context.input.githubConnector;
    const issues = await github.executeTool('list_issues', {
      state: 'open',
      labels: context.input.labels || []
    });

    return { issues, fetchedAt: Date.now() };
  })
  .step('sync-to-database', async (context, prevResult) => {
    'use step';

    const postgres: PostgresConnector = context.input.postgresConnector;
    const { issues } = prevResult;

    // Use transaction for atomic insert
    const queries = issues.map((issue: any) => ({
      query: `
        INSERT INTO github_issues (issue_number, title, state, created_at)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (issue_number) DO UPDATE SET
          title = EXCLUDED.title,
          state = EXCLUDED.state
      `,
      params: [issue.number, issue.title, issue.state, issue.created_at]
    }));

    await postgres.executeTool('transaction', { queries });

    return { syncedCount: issues.length };
  })
  .step('notify-slack', async (context, prevResult) => {
    'use step';

    const slack: SlackConnector = context.input.slackConnector;

    await slack.executeTool('send_message', {
      channel: context.input.slackChannel || '#engineering',
      text: `✅ Synced ${prevResult.syncedCount} GitHub issues to database`
    });

    return {
      success: true,
      issuesSynced: prevResult.syncedCount,
      completedAt: new Date().toISOString()
    };
  });

/**
 * Long-running agent workflow example
 * Demonstrates periodic execution and error recovery
 */
export const agentMonitoringWorkflow = new Workflow('agent-monitoring')
  .step('check-system-health', async (context) => {
    'use step';

    const postgres: PostgresConnector = context.input.postgresConnector;

    // Check database health
    const result = await postgres.executeTool('query', {
      query: 'SELECT COUNT(*) as active_connections FROM pg_stat_activity'
    });

    return {
      dbConnections: result.rows[0].active_connections,
      healthy: result.rows[0].active_connections < 100
    };
  })
  .step('alert-if-unhealthy', async (context, prevResult) => {
    'use step';

    if (!prevResult.healthy) {
      const slack: SlackConnector = context.input.slackConnector;

      await slack.executeTool('send_message', {
        channel: '#alerts',
        text: `🚨 System health alert: ${prevResult.dbConnections} active database connections`
      });

      return { alerted: true, reason: 'high_db_connections' };
    }

    return { alerted: false, status: 'healthy' };
  });

/**
 * Execute MCP orchestration workflow
 */
export async function runMCPOrchestration(config: {
  githubConnector: GitHubConnector;
  postgresConnector: PostgresConnector;
  slackConnector: SlackConnector;
  labels?: string[];
  slackChannel?: string;
}) {
  return await mcpOrchestrationWorkflow.run(config);
}

/**
 * Execute agent monitoring workflow
 */
export async function runAgentMonitoring(config: {
  postgresConnector: PostgresConnector;
  slackConnector: SlackConnector;
}) {
  return await agentMonitoringWorkflow.run(config);
}
'''
        self._write_file(package_path / "src/mcp-orchestration.ts", mcp_orchestration_ts)
        files_created.append("src/mcp-orchestration.ts")

        # Index barrel export
        index_ts = '''/**
 * Workflow.dev Durable Workflows
 * @packageDocumentation
 */

export { dataProcessingWorkflow, runDataProcessing } from './data-processing';
export {
  mcpOrchestrationWorkflow,
  agentMonitoringWorkflow,
  runMCPOrchestration,
  runAgentMonitoring
} from './mcp-orchestration';
'''
        self._write_file(package_path / "src/index.ts", index_ts)
        files_created.append("src/index.ts")

        # README
        readme = '''# Durable Workflows with Workflow.dev

Production-ready durable workflows using [Vercel Workflow DevKit](https://useworkflow.dev/).

## What is Workflow.dev?

Workflow DevKit makes TypeScript functions durable, reliable, and observable:
- Functions pause for minutes/months and resume exactly where they stopped
- Survives deployments and crashes
- Automatic retry logic and persistence
- Zero infrastructure setup

## Available Workflows

### Data Processing Workflow
Multi-step data pipeline with automatic retry and persistence.

```typescript
import { runDataProcessing } from '@repo/workflows/data-processing';

const result = await runDataProcessing(
  'https://api.example.com/data',
  'https://api.example.com/storage'
);
```

### MCP Orchestration Workflow
Orchestrate MCP connectors (GitHub, Postgres, Slack) durably.

```typescript
import { runMCPOrchestration } from '@repo/workflows/mcp-orchestration';
import { GitHubConnector } from '@repo/mcp-connectors/github';
import { PostgresConnector } from '@repo/mcp-connectors/postgres';
import { SlackConnector } from '@repo/mcp-connectors/slack';

const result = await runMCPOrchestration({
  githubConnector: new GitHubConnector({ token, owner, repo }),
  postgresConnector: new PostgresConnector({ connectionString }),
  slackConnector: new SlackConnector({ token }),
  labels: ['bug', 'priority-high']
});
```

### Agent Monitoring Workflow
Periodic system health checks with alerting.

```typescript
import { runAgentMonitoring } from '@repo/workflows/mcp-orchestration';

const result = await runAgentMonitoring({
  postgresConnector,
  slackConnector
});
```

## Key Concepts

### Workflow Directive
Mark a function as durable:
```typescript
const myWorkflow = new Workflow('my-workflow')
```

### Step Directive
Mark units of work that auto-retry:
```typescript
.step('step-name', async (context) => {
  'use step';
  // This work is persisted and retries on failure
  return { result: 'data' };
})
```

## Features

- **Durability**: Workflows survive crashes and deployments
- **Retry Logic**: Steps automatically retry on failure
- **Observability**: Built-in monitoring and logging
- **MCP Integration**: Works seamlessly with @repo/mcp-connectors
- **Zero Config**: No queues, schedulers, or YAML needed

## Resources

- [Workflow.dev Documentation](https://useworkflow.dev/)
- [GitHub Repository](https://github.com/vercel/workflow)
- [Vercel Announcement](https://vercel.com/blog/introducing-workflow)
'''
        self._write_file(package_path / "README.md", readme)
        files_created.append("README.md")

        logger.info(f"✅ Generated Workflow.dev package with {len(files_created)} files")
        return files_created

    async def _generate_observability_package(self, package_path: Path, architecture: Dict[str, Any]) -> List[str]:
        """Generate OpenTelemetry observability package (based on existing EventRelay implementation)"""
        logger.info("📊 Generating OpenTelemetry observability package...")
        files_created = []

        # package.json
        package_json = {
            "name": "@repo/observability",
            "version": "0.0.0",
            "private": True,
            "main": "dist/index.js",
            "types": "dist/index.d.ts",
            "scripts": {
                "build": "tsc",
                "dev": "tsc --watch",
                "lint": "eslint . --max-warnings 0"
            },
            "dependencies": {
                "@opentelemetry/api": "^1.7.0",
                "@opentelemetry/sdk-node": "^0.45.0",
                "@opentelemetry/exporter-trace-otlp-grpc": "^0.45.0",
                "@opentelemetry/exporter-metrics-otlp-grpc": "^0.45.0",
                "@opentelemetry/instrumentation": "^0.45.0",
                "@opentelemetry/resources": "^1.18.0",
                "@opentelemetry/semantic-conventions": "^1.18.0"
            },
            "devDependencies": {
                "@types/node": "^20",
                "typescript": "^5",
                "eslint": "^8"
            }
        }
        self._write_file(package_path / "package.json", json.dumps(package_json, indent=2))
        files_created.append("package.json")

        # tsconfig.json
        tsconfig = {
            "extends": "@repo/typescript-config/base.json",
            "compilerOptions": {
                "outDir": "dist",
                "rootDir": "src",
                "declaration": True,
                "declarationMap": True
            },
            "include": ["src"],
            "exclude": ["node_modules", "dist"]
        }
        self._write_file(package_path / "tsconfig.json", json.dumps(tsconfig, indent=2))
        files_created.append("tsconfig.json")

        # Main observability class
        observability_ts = '''import { Tracer, Meter, trace, metrics, context, SpanStatusCode } from '@opentelemetry/api';
import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-grpc';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-grpc';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

/**
 * Observability configuration
 */
export interface ObservabilityConfig {
  serviceName: string;
  otlpEndpoint?: string;
  enabled?: boolean;
}

/**
 * OpenTelemetry observability system
 * Based on EventRelay's Python implementation
 */
export class Observability {
  private sdk: NodeSDK | null = null;
  private tracer: Tracer | null = null;
  private meter: Meter | null = null;
  private enabled: boolean = false;
  private serviceName: string;

  constructor(config: ObservabilityConfig) {
    this.serviceName = config.serviceName;
    const otlpEndpoint = config.otlpEndpoint || process.env.OTEL_EXPORTER_OTLP_ENDPOINT;

    if (config.enabled !== false && otlpEndpoint) {
      this.setupObservability(otlpEndpoint);
      this.enabled = true;
    } else {
      console.log('[Observability] Disabled (no OTLP endpoint configured)');
    }
  }

  private setupObservability(endpoint: string): void {
    // Configure resource with service name
    const resource = new Resource({
      [SemanticResourceAttributes.SERVICE_NAME]: this.serviceName,
    });

    // Initialize SDK with OTLP exporters
    this.sdk = new NodeSDK({
      resource,
      traceExporter: new OTLPTraceExporter({ url: endpoint }),
      metricReader: new OTLPMetricExporter({ url: endpoint }),
    });

    // Start SDK
    this.sdk.start();

    // Get tracer and meter
    this.tracer = trace.getTracer(this.serviceName);
    this.meter = metrics.getMeter(this.serviceName);

    console.log(`[Observability] Initialized for ${this.serviceName} (endpoint: ${endpoint})`);
  }

  /**
   * Create a traced operation
   * @param operationName Name of the operation
   * @param attributes Optional attributes to add to the span
   * @param fn Function to trace
   */
  async trace<T>(
    operationName: string,
    attributes: Record<string, string | number | boolean> = {},
    fn: () => Promise<T>
  ): Promise<T> {
    if (!this.enabled || !this.tracer) {
      // Fallback: execute without tracing
      return await fn();
    }

    return await this.tracer.startActiveSpan(operationName, async (span) => {
      try {
        // Set attributes
        Object.entries(attributes).forEach(([key, value]) => {
          span.setAttribute(key, value);
        });

        // Execute function
        const result = await fn();

        // Mark as successful
        span.setStatus({ code: SpanStatusCode.OK });
        return result;
      } catch (error: any) {
        // Record error
        span.setStatus({
          code: SpanStatusCode.ERROR,
          message: error.message || 'Unknown error'
        });
        span.recordException(error);
        throw error;
      } finally {
        span.end();
      }
    });
  }

  /**
   * Record metrics for an operation
   */
  recordMetrics(name: string, value: number, attributes: Record<string, string | number> = {}): void {
    if (!this.enabled || !this.meter) {
      return;
    }

    const counter = this.meter.createCounter(name, {
      description: `Metric for ${name}`
    });

    counter.add(value, attributes);
  }

  /**
   * Record operation duration
   */
  recordDuration(operation: string, durationMs: number, attributes: Record<string, string | number> = {}): void {
    if (!this.enabled || !this.meter) {
      return;
    }

    const histogram = this.meter.createHistogram(`${operation}_duration_ms`, {
      description: `Duration of ${operation} in milliseconds`
    });

    histogram.record(durationMs, attributes);
  }

  /**
   * Shutdown observability
   */
  async shutdown(): Promise<void> {
    if (this.sdk) {
      await this.sdk.shutdown();
      console.log('[Observability] Shutdown complete');
    }
  }
}

/**
 * Singleton instance
 */
let observabilityInstance: Observability | null = null;

/**
 * Initialize observability (call once at app startup)
 */
export function initObservability(config: ObservabilityConfig): Observability {
  if (!observabilityInstance) {
    observabilityInstance = new Observability(config);
  }
  return observabilityInstance;
}

/**
 * Get observability instance
 */
export function getObservability(): Observability {
  if (!observabilityInstance) {
    throw new Error('Observability not initialized. Call initObservability() first.');
  }
  return observabilityInstance;
}
'''
        self._write_file(package_path / "src/observability.ts", observability_ts)
        files_created.append("src/observability.ts")

        # Workflow instrumentation helper
        workflow_instrumentation_ts = '''import { getObservability } from './observability';

/**
 * Helper for instrumenting Workflow.dev workflows with OpenTelemetry
 */
export class WorkflowInstrumentation {
  private obs = getObservability();

  /**
   * Trace a workflow execution
   */
  async traceWorkflow<T>(
    workflowName: string,
    workflowId: string,
    fn: () => Promise<T>
  ): Promise<T> {
    const startTime = Date.now();

    try {
      const result = await this.obs.trace(
        `workflow.${workflowName}`,
        {
          'workflow.name': workflowName,
          'workflow.id': workflowId,
          'workflow.status': 'running'
        },
        fn
      );

      // Record success metrics
      const duration = Date.now() - startTime;
      this.obs.recordDuration(`workflow.${workflowName}`, duration, {
        status: 'success',
        workflow_id: workflowId
      });

      this.obs.recordMetrics('workflow_executions_total', 1, {
        workflow: workflowName,
        status: 'success'
      });

      return result;
    } catch (error) {
      // Record failure metrics
      const duration = Date.now() - startTime;
      this.obs.recordDuration(`workflow.${workflowName}`, duration, {
        status: 'failure',
        workflow_id: workflowId
      });

      this.obs.recordMetrics('workflow_executions_total', 1, {
        workflow: workflowName,
        status: 'failure'
      });

      throw error;
    }
  }

  /**
   * Trace a workflow step
   */
  async traceStep<T>(
    workflowName: string,
    stepName: string,
    stepData: Record<string, any>,
    fn: () => Promise<T>
  ): Promise<T> {
    return await this.obs.trace(
      `workflow.${workflowName}.step.${stepName}`,
      {
        'workflow.name': workflowName,
        'step.name': stepName,
        ...stepData
      },
      fn
    );
  }
}

/**
 * Singleton instance
 */
let instrumentationInstance: WorkflowInstrumentation | null = null;

export function getWorkflowInstrumentation(): WorkflowInstrumentation {
  if (!instrumentationInstance) {
    instrumentationInstance = new WorkflowInstrumentation();
  }
  return instrumentationInstance;
}
'''
        self._write_file(package_path / "src/workflow-instrumentation.ts", workflow_instrumentation_ts)
        files_created.append("src/workflow-instrumentation.ts")

        # Index barrel export
        index_ts = '''/**
 * OpenTelemetry Observability Package
 * @packageDocumentation
 */

export {
  Observability,
  ObservabilityConfig,
  initObservability,
  getObservability
} from './observability';

export {
  WorkflowInstrumentation,
  getWorkflowInstrumentation
} from './workflow-instrumentation';
'''
        self._write_file(package_path / "src/index.ts", index_ts)
        files_created.append("src/index.ts")

        # README
        readme = '''# OpenTelemetry Observability

Production-ready observability with OpenTelemetry tracing and metrics.

**Based on EventRelay's proven Python implementation**

## Features

- **Distributed Tracing**: Track operations across services with OTLP
- **Metrics**: Counters and histograms for performance monitoring
- **Workflow Integration**: Built-in instrumentation for Workflow.dev
- **Zero Config**: Works with standard OTEL environment variables
- **Fallback Mode**: Gracefully degrades when OTEL unavailable

## Quick Start

### 1. Initialize Observability

```typescript
import { initObservability } from '@repo/observability';

// Initialize at app startup
const obs = initObservability({
  serviceName: 'my-service',
  otlpEndpoint: process.env.OTEL_EXPORTER_OTLP_ENDPOINT,
  enabled: true
});
```

### 2. Trace Operations

```typescript
import { getObservability } from '@repo/observability';

const obs = getObservability();

await obs.trace('data-processing', { user_id: '123' }, async () => {
  // Your operation here
  const data = await fetchData();
  return processData(data);
});
```

### 3. Record Metrics

```typescript
// Record a counter
obs.recordMetrics('api_requests_total', 1, {
  endpoint: '/api/users',
  method: 'GET'
});

// Record operation duration
obs.recordDuration('database_query', 125, {
  query: 'SELECT',
  table: 'users'
});
```

### 4. Instrument Workflows

```typescript
import { getWorkflowInstrumentation } from '@repo/observability';

const instrumentation = getWorkflowInstrumentation();

await instrumentation.traceWorkflow(
  'data-sync',
  'run-123',
  async () => {
    // Workflow execution
    return await runDataSyncWorkflow();
  }
);
```

## Environment Variables

```env
# OTLP endpoint (required)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Optional: Service name (can also be set in code)
OTEL_SERVICE_NAME=my-service
```

## Integration Examples

### With Workflow.dev

```typescript
import { Workflow } from '@vercel/workflow';
import { getWorkflowInstrumentation } from '@repo/observability';

const instrumentation = getWorkflowInstrumentation();

export const tracedWorkflow = new Workflow('my-workflow')
  .step('step-1', async (context) => {
    return await instrumentation.traceStep(
      'my-workflow',
      'step-1',
      { input: context.input },
      async () => {
        // Step implementation
        return { result: 'data' };
      }
    );
  });
```

### With MCP Connectors

```typescript
import { PostgresConnector } from '@repo/mcp-connectors/postgres';
import { getObservability } from '@repo/observability';

const obs = getObservability();
const postgres = new PostgresConnector({ connectionString: '...' });

await obs.trace('postgres-query', { table: 'users' }, async () => {
  return await postgres.executeTool('query', {
    query: 'SELECT * FROM users'
  });
});
```

## Architecture

Based on EventRelay's `agents/observability_setup.py`:
- **Tracing**: OTLP trace exporter with gRPC
- **Metrics**: OTLP metric exporter with periodic export
- **Graceful Degradation**: Continues working without OTEL backend
- **Node.js SDK**: Official OpenTelemetry Node.js SDK

## Resources

- [OpenTelemetry Docs](https://opentelemetry.io/docs/)
- [Node.js SDK Guide](https://opentelemetry.io/docs/instrumentation/js/getting-started/nodejs/)
- [EventRelay Implementation](../../../agents/observability_setup.py)
'''
        self._write_file(package_path / "README.md", readme)
        files_created.append("README.md")

        logger.info(f"✅ Generated OpenTelemetry observability package with {len(files_created)} files")
        return files_created

    async def _generate_ai_gateway_package(self, package_path: Path, architecture: Dict[str, Any]) -> List[str]:
        """Generate Vercel AI SDK multi-model gateway package (Phase 1.4)"""
        logger.info("🤖 Generating Vercel AI Gateway package with multi-model failover...")

        package_path.mkdir(parents=True, exist_ok=True)
        files_created = []

        # package.json with Vercel AI SDK
        package_json = {
            "name": "@repo/ai-gateway",
            "version": "0.0.0",
            "private": True,
            "type": "module",
            "exports": {
                ".": "./src/index.ts",
                "./models": "./src/models.ts",
                "./types": "./src/types.ts"
            },
            "scripts": {
                "lint": "eslint . --max-warnings 0",
                "test": "jest"
            },
            "dependencies": {
                "ai": "^3.0.0",
                "@ai-sdk/openai": "^0.0.24",
                "@ai-sdk/anthropic": "^0.0.24",
                "@ai-sdk/google": "^0.0.24",
                "zod": "^3.22.4"
            },
            "devDependencies": {
                "@types/node": "^20",
                "typescript": "^5",
                "eslint": "^8",
                "jest": "^29"
            }
        }
        self._write_file(package_path / "package.json", json.dumps(package_json, indent=2))
        files_created.append("package.json")

        # src/types.ts - Type definitions
        types_ts = '''export type AIProvider = 'grok' | 'claude' | 'gemini' | 'openai';

export interface AIGatewayConfig {
  providers: AIProvider[];
  fallbackOrder?: AIProvider[];
  maxRetries?: number;
  timeout?: number;
}

export interface ModelConfig {
  provider: AIProvider;
  model: string;
  apiKey: string;
  maxTokens?: number;
  temperature?: number;
}

export interface GenerateOptions {
  prompt: string;
  system?: string;
  maxTokens?: number;
  temperature?: number;
  stream?: boolean;
}

export interface GenerateResult {
  text: string;
  provider: AIProvider;
  model: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export interface StreamResult {
  textStream: AsyncIterable<string>;
  provider: AIProvider;
  model: string;
}
'''
        (package_path / "src").mkdir(exist_ok=True)
        self._write_file(package_path / "src" / "types.ts", types_ts)
        files_created.append("src/types.ts")

        # src/models.ts - Model configurations
        models_ts = '''import { openai } from '@ai-sdk/openai';
import { anthropic } from '@ai-sdk/anthropic';
import { google } from '@ai-sdk/google';
import type { LanguageModel } from 'ai';
import type { AIProvider, ModelConfig } from './types';

export class ModelRegistry {
  private models = new Map<AIProvider, LanguageModel>();

  constructor(configs: ModelConfig[]) {
    for (const config of configs) {
      this.registerModel(config);
    }
  }

  private registerModel(config: ModelConfig): void {
    let model: LanguageModel;

    switch (config.provider) {
      case 'grok':
        // Grok uses OpenAI-compatible API
        model = openai(config.model || 'grok-beta', {
          baseURL: 'https://api.x.ai/v1',
          apiKey: config.apiKey,
        });
        break;

      case 'claude':
        model = anthropic(config.model || 'claude-3-5-sonnet-20241022', {
          apiKey: config.apiKey,
        });
        break;

      case 'gemini':
        model = google(config.model || 'gemini-2.0-flash-exp', {
          apiKey: config.apiKey,
        });
        break;

      case 'openai':
        model = openai(config.model || 'gpt-4o', {
          apiKey: config.apiKey,
        });
        break;

      default:
        throw new Error(`Unsupported provider: ${config.provider}`);
    }

    this.models.set(config.provider, model);
  }

  getModel(provider: AIProvider): LanguageModel | undefined {
    return this.models.get(provider);
  }

  hasModel(provider: AIProvider): boolean {
    return this.models.has(provider);
  }

  getAvailableProviders(): AIProvider[] {
    return Array.from(this.models.keys());
  }
}

// Default model configurations
export const DEFAULT_MODELS: Record<AIProvider, string> = {
  grok: 'grok-beta',
  claude: 'claude-3-5-sonnet-20241022',
  gemini: 'gemini-2.0-flash-exp',
  openai: 'gpt-4o',
};

// Default fallback order (Grok -> Claude -> Gemini)
export const DEFAULT_FALLBACK_ORDER: AIProvider[] = ['grok', 'claude', 'gemini'];
'''
        self._write_file(package_path / "src" / "models.ts", models_ts)
        files_created.append("src/models.ts")

        # src/index.ts - Main AI Gateway implementation
        index_ts = '''import { generateText, streamText } from 'ai';
import { ModelRegistry, DEFAULT_FALLBACK_ORDER } from './models';
import type {
  AIProvider,
  AIGatewayConfig,
  ModelConfig,
  GenerateOptions,
  GenerateResult,
  StreamResult,
} from './types';

export class AIGateway {
  private registry: ModelRegistry;
  private fallbackOrder: AIProvider[];
  private maxRetries: number;
  private timeout: number;

  constructor(configs: ModelConfig[], options?: Partial<AIGatewayConfig>) {
    this.registry = new ModelRegistry(configs);
    this.fallbackOrder = options?.fallbackOrder || DEFAULT_FALLBACK_ORDER;
    this.maxRetries = options?.maxRetries || 3;
    this.timeout = options?.timeout || 30000;
  }

  /**
   * Generate text with automatic failover between providers
   */
  async generate(options: GenerateOptions): Promise<GenerateResult> {
    const errors: Array<{ provider: AIProvider; error: Error }> = [];

    for (const provider of this.fallbackOrder) {
      if (!this.registry.hasModel(provider)) {
        continue;
      }

      try {
        const model = this.registry.getModel(provider);
        if (!model) continue;

        const result = await this.generateWithTimeout(model, provider, options);
        return result;
      } catch (error) {
        errors.push({
          provider,
          error: error instanceof Error ? error : new Error(String(error)),
        });
        console.warn(`[AIGateway] ${provider} failed, trying next provider...`, error);
      }
    }

    // All providers failed
    throw new Error(
      `All providers failed: ${errors.map((e) => `${e.provider}: ${e.error.message}`).join(', ')}`
    );
  }

  /**
   * Stream text with automatic failover
   */
  async stream(options: GenerateOptions): Promise<StreamResult> {
    const errors: Array<{ provider: AIProvider; error: Error }> = [];

    for (const provider of this.fallbackOrder) {
      if (!this.registry.hasModel(provider)) {
        continue;
      }

      try {
        const model = this.registry.getModel(provider);
        if (!model) continue;

        const { textStream } = await streamText({
          model,
          prompt: options.prompt,
          system: options.system,
          maxTokens: options.maxTokens,
          temperature: options.temperature,
        });

        return {
          textStream,
          provider,
          model: model.modelId || 'unknown',
        };
      } catch (error) {
        errors.push({
          provider,
          error: error instanceof Error ? error : new Error(String(error)),
        });
        console.warn(`[AIGateway] ${provider} stream failed, trying next provider...`, error);
      }
    }

    throw new Error(
      `All providers failed for streaming: ${errors.map((e) => `${e.provider}: ${e.error.message}`).join(', ')}`
    );
  }

  /**
   * Generate with timeout enforcement
   */
  private async generateWithTimeout(
    model: any,
    provider: AIProvider,
    options: GenerateOptions
  ): Promise<GenerateResult> {
    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('Request timeout')), this.timeout)
    );

    const generatePromise = generateText({
      model,
      prompt: options.prompt,
      system: options.system,
      maxTokens: options.maxTokens,
      temperature: options.temperature,
    });

    const result = await Promise.race([generatePromise, timeoutPromise]);

    return {
      text: result.text,
      provider,
      model: model.modelId || 'unknown',
      usage: result.usage
        ? {
            promptTokens: result.usage.promptTokens,
            completionTokens: result.usage.completionTokens,
            totalTokens: result.usage.totalTokens,
          }
        : undefined,
    };
  }

  /**
   * Get available providers
   */
  getAvailableProviders(): AIProvider[] {
    return this.registry.getAvailableProviders();
  }

  /**
   * Check if provider is available
   */
  hasProvider(provider: AIProvider): boolean {
    return this.registry.hasModel(provider);
  }
}

// Export types
export type {
  AIProvider,
  AIGatewayConfig,
  ModelConfig,
  GenerateOptions,
  GenerateResult,
  StreamResult,
} from './types';

// Export model utilities
export { ModelRegistry, DEFAULT_MODELS, DEFAULT_FALLBACK_ORDER } from './models';
'''
        self._write_file(package_path / "src" / "index.ts", index_ts)
        files_created.append("src/index.ts")

        # tsconfig.json
        tsconfig = {
            "extends": "@repo/typescript-config/base.json",
            "compilerOptions": {
                "outDir": "dist",
                "rootDir": "src"
            },
            "include": ["src"],
            "exclude": ["node_modules", "dist"]
        }
        self._write_file(package_path / "tsconfig.json", json.dumps(tsconfig, indent=2))
        files_created.append("tsconfig.json")

        # README.md with comprehensive documentation
        readme = '''# @repo/ai-gateway

Multi-model AI gateway with automatic failover using Vercel AI SDK.

## Features

- ✅ **Multi-Model Support**: Grok, Claude, Gemini, OpenAI
- ✅ **Automatic Failover**: Seamless switching between providers
- ✅ **Type Safety**: Full TypeScript support
- ✅ **Streaming**: Support for streaming responses
- ✅ **Timeout Handling**: Configurable request timeouts
- ✅ **Error Recovery**: Graceful error handling with detailed logging

## Installation

```bash
npm install @repo/ai-gateway
```

## Usage

### Basic Text Generation

```typescript
import { AIGateway } from '@repo/ai-gateway';

const gateway = new AIGateway([
  {
    provider: 'grok',
    model: 'grok-beta',
    apiKey: process.env.XAI_API_KEY!,
  },
  {
    provider: 'claude',
    model: 'claude-3-5-sonnet-20241022',
    apiKey: process.env.ANTHROPIC_API_KEY!,
  },
  {
    provider: 'gemini',
    model: 'gemini-2.0-flash-exp',
    apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY!,
  },
]);

const result = await gateway.generate({
  prompt: 'Explain quantum computing in simple terms',
  maxTokens: 500,
  temperature: 0.7,
});

console.log(result.text);
console.log(`Generated by: ${result.provider} (${result.model})`);
```

### Streaming Responses

```typescript
const stream = await gateway.stream({
  prompt: 'Write a creative story about AI',
  maxTokens: 1000,
});

for await (const chunk of stream.textStream) {
  process.stdout.write(chunk);
}
```

### Custom Failover Order

```typescript
const gateway = new AIGateway(
  [
    { provider: 'claude', model: 'claude-3-5-sonnet-20241022', apiKey: '...' },
    { provider: 'gemini', model: 'gemini-2.0-flash-exp', apiKey: '...' },
    { provider: 'grok', model: 'grok-beta', apiKey: '...' },
  ],
  {
    fallbackOrder: ['claude', 'gemini', 'grok'], // Claude first
    maxRetries: 5,
    timeout: 60000, // 60 seconds
  }
);
```

### With System Prompts

```typescript
const result = await gateway.generate({
  system: 'You are a helpful AI assistant specialized in technical documentation.',
  prompt: 'Explain the difference between REST and GraphQL APIs',
  maxTokens: 800,
  temperature: 0.5,
});
```

### Integration with Next.js API Routes

```typescript
// app/api/generate/route.ts
import { AIGateway } from '@repo/ai-gateway';
import { NextRequest, NextResponse } from 'next/server';

const gateway = new AIGateway([
  { provider: 'grok', model: 'grok-beta', apiKey: process.env.XAI_API_KEY! },
  { provider: 'claude', model: 'claude-3-5-sonnet-20241022', apiKey: process.env.ANTHROPIC_API_KEY! },
]);

export async function POST(request: NextRequest) {
  const { prompt } = await request.json();

  try {
    const result = await gateway.generate({ prompt });
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: 'All AI providers failed' },
      { status: 500 }
    );
  }
}
```

### Streaming in Next.js

```typescript
// app/api/stream/route.ts
import { AIGateway } from '@repo/ai-gateway';
import { NextRequest } from 'next/server';

const gateway = new AIGateway([...]);

export async function POST(request: NextRequest) {
  const { prompt } = await request.json();

  const stream = await gateway.stream({ prompt });

  const encoder = new TextEncoder();
  const readableStream = new ReadableStream({
    async start(controller) {
      for await (const chunk of stream.textStream) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });

  return new Response(readableStream, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
```

## API Reference

### `AIGateway`

Main gateway class for managing multiple AI providers.

#### Constructor

```typescript
new AIGateway(configs: ModelConfig[], options?: AIGatewayConfig)
```

#### Methods

- `generate(options: GenerateOptions): Promise<GenerateResult>` - Generate text with failover
- `stream(options: GenerateOptions): Promise<StreamResult>` - Stream text with failover
- `getAvailableProviders(): AIProvider[]` - Get list of configured providers
- `hasProvider(provider: AIProvider): boolean` - Check if provider is available

### Types

```typescript
type AIProvider = 'grok' | 'claude' | 'gemini' | 'openai';

interface ModelConfig {
  provider: AIProvider;
  model: string;
  apiKey: string;
  maxTokens?: number;
  temperature?: number;
}

interface GenerateOptions {
  prompt: string;
  system?: string;
  maxTokens?: number;
  temperature?: number;
}

interface GenerateResult {
  text: string;
  provider: AIProvider;
  model: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}
```

## Environment Variables

```bash
# Required for each provider you want to use
XAI_API_KEY=your_grok_api_key
ANTHROPIC_API_KEY=your_claude_api_key
GOOGLE_GENERATIVE_AI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
```

## Architecture

- **Vercel AI SDK**: Unified interface for multiple AI providers
- **Automatic Failover**: Tries providers in order until success
- **Timeout Protection**: Prevents hanging requests
- **Type Safety**: Full TypeScript with generics
- **Error Handling**: Detailed error messages with provider context

## Model Defaults

- **Grok**: `grok-beta`
- **Claude**: `claude-3-5-sonnet-20241022`
- **Gemini**: `gemini-2.0-flash-exp`
- **OpenAI**: `gpt-4o`

## Related Packages

- `@repo/observability` - OpenTelemetry instrumentation
- `@repo/workflows` - Workflow.dev durable execution
- `@repo/mcp-connectors` - MCP protocol integrations

## Resources

- [Vercel AI SDK Docs](https://sdk.vercel.ai/docs)
- [Grok API Docs](https://docs.x.ai/api)
- [Anthropic API Docs](https://docs.anthropic.com/)
- [Google Generative AI Docs](https://ai.google.dev/)
'''
        self._write_file(package_path / "README.md", readme)
        files_created.append("README.md")

        logger.info(f"✅ Generated AI Gateway package with {len(files_created)} files")
        return files_created

    async def _generate_logger_package(self, package_path: Path, architecture: Dict[str, Any]) -> List[str]:
        """Generate comprehensive structured logging package (Phase 1.5)"""
        logger.info("📝 Generating structured logging package with OpenTelemetry integration...")

        package_path.mkdir(parents=True, exist_ok=True)
        files_created = []

        # package.json with pino for high-performance logging
        package_json = {
            "name": "@repo/logger",
            "version": "0.0.0",
            "private": True,
            "type": "module",
            "exports": {
                ".": "./src/index.ts",
                "./types": "./src/types.ts"
            },
            "scripts": {
                "lint": "eslint . --max-warnings 0",
                "test": "jest"
            },
            "dependencies": {
                "pino": "^8.17.0",
                "pino-pretty": "^10.3.0",
                "@opentelemetry/api": "^1.7.0"
            },
            "devDependencies": {
                "@types/node": "^20",
                "typescript": "^5",
                "eslint": "^8",
                "jest": "^29"
            }
        }
        self._write_file(package_path / "package.json", json.dumps(package_json, indent=2))
        files_created.append("package.json")

        # src/types.ts - Type definitions
        types_ts = '''export type LogLevel = 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'fatal';

export interface LoggerConfig {
  level?: LogLevel;
  name?: string;
  pretty?: boolean;
  redact?: string[];
  destination?: string;
}

export interface LogContext {
  requestId?: string;
  traceId?: string;
  spanId?: string;
  userId?: string;
  [key: string]: any;
}

export interface StructuredLogger {
  trace(message: string, context?: LogContext): void;
  debug(message: string, context?: LogContext): void;
  info(message: string, context?: LogContext): void;
  warn(message: string, context?: LogContext): void;
  error(message: string | Error, context?: LogContext): void;
  fatal(message: string | Error, context?: LogContext): void;
  child(context: LogContext): StructuredLogger;
}
'''
        (package_path / "src").mkdir(exist_ok=True)
        self._write_file(package_path / "src" / "types.ts", types_ts)
        files_created.append("src/types.ts")

        # src/index.ts - Main logger implementation
        index_ts = '''import pino from 'pino';
import { trace, context as otelContext } from '@opentelemetry/api';
import type { LoggerConfig, LogContext, StructuredLogger, LogLevel } from './types';

class Logger implements StructuredLogger {
  private logger: pino.Logger;

  constructor(config?: LoggerConfig) {
    const isDevelopment = process.env.NODE_ENV !== 'production';

    this.logger = pino({
      name: config?.name || 'app',
      level: config?.level || (isDevelopment ? 'debug' : 'info'),

      // Redact sensitive fields
      redact: {
        paths: config?.redact || [
          'password',
          'apiKey',
          'api_key',
          'token',
          'secret',
          'authorization',
          'cookie',
        ],
        censor: '[REDACTED]',
      },

      // Pretty printing in development
      transport: config?.pretty || isDevelopment
        ? {
            target: 'pino-pretty',
            options: {
              colorize: true,
              translateTime: 'HH:MM:ss.l',
              ignore: 'pid,hostname',
              singleLine: false,
            },
          }
        : undefined,

      // Base fields
      base: {
        env: process.env.NODE_ENV,
      },

      // Custom serializers
      serializers: {
        err: pino.stdSerializers.err,
        error: pino.stdSerializers.err,
      },

      // Timestamp
      timestamp: pino.stdTimeFunctions.isoTime,
    });
  }

  /**
   * Enrich log context with OpenTelemetry trace context
   */
  private enrichContext(context?: LogContext): LogContext {
    const enriched = { ...context };

    // Add OpenTelemetry trace context if available
    const span = trace.getSpan(otelContext.active());
    if (span) {
      const spanContext = span.spanContext();
      if (spanContext.traceId) {
        enriched.traceId = spanContext.traceId;
      }
      if (spanContext.spanId) {
        enriched.spanId = spanContext.spanId;
      }
    }

    return enriched;
  }

  trace(message: string, context?: LogContext): void {
    this.logger.trace(this.enrichContext(context), message);
  }

  debug(message: string, context?: LogContext): void {
    this.logger.debug(this.enrichContext(context), message);
  }

  info(message: string, context?: LogContext): void {
    this.logger.info(this.enrichContext(context), message);
  }

  warn(message: string, context?: LogContext): void {
    this.logger.warn(this.enrichContext(context), message);
  }

  error(message: string | Error, context?: LogContext): void {
    const enriched = this.enrichContext(context);

    if (message instanceof Error) {
      this.logger.error({ ...enriched, err: message }, message.message);
    } else {
      this.logger.error(enriched, message);
    }
  }

  fatal(message: string | Error, context?: LogContext): void {
    const enriched = this.enrichContext(context);

    if (message instanceof Error) {
      this.logger.fatal({ ...enriched, err: message }, message.message);
    } else {
      this.logger.fatal(enriched, message);
    }
  }

  /**
   * Create a child logger with additional context
   */
  child(context: LogContext): StructuredLogger {
    const childPino = this.logger.child(context);

    // Create new Logger instance wrapping the child pino logger
    const childLogger = new Logger();
    childLogger.logger = childPino;

    return childLogger;
  }
}

// Singleton logger instance
let defaultLogger: StructuredLogger | null = null;

/**
 * Get or create the default logger instance
 */
export function getLogger(config?: LoggerConfig): StructuredLogger {
  if (!defaultLogger) {
    defaultLogger = new Logger(config);
  }
  return defaultLogger;
}

/**
 * Create a new logger instance with custom configuration
 */
export function createLogger(config?: LoggerConfig): StructuredLogger {
  return new Logger(config);
}

// Export types
export type { LoggerConfig, LogContext, StructuredLogger, LogLevel } from './types';
'''
        self._write_file(package_path / "src" / "index.ts", index_ts)
        files_created.append("src/index.ts")

        # tsconfig.json
        tsconfig = {
            "extends": "@repo/typescript-config/base.json",
            "compilerOptions": {
                "outDir": "dist",
                "rootDir": "src"
            },
            "include": ["src"],
            "exclude": ["node_modules", "dist"]
        }
        self._write_file(package_path / "tsconfig.json", json.dumps(tsconfig, indent=2))
        files_created.append("tsconfig.json")

        # README.md with comprehensive documentation
        readme = '''# @repo/logger

High-performance structured logging with OpenTelemetry integration.

## Features

- ✅ **Structured JSON Logging**: Machine-readable logs for production
- ✅ **OpenTelemetry Integration**: Automatic trace/span correlation
- ✅ **High Performance**: Built on pino (one of the fastest Node.js loggers)
- ✅ **Pretty Development Mode**: Human-readable colored output
- ✅ **Sensitive Data Redaction**: Automatic removal of secrets
- ✅ **Child Loggers**: Contextual logging with inheritance
- ✅ **TypeScript Support**: Full type safety

## Installation

```bash
npm install @repo/logger
```

## Usage

### Basic Logging

```typescript
import { getLogger } from '@repo/logger';

const logger = getLogger();

logger.info('Application started');
logger.debug('Debug information', { userId: '123' });
logger.warn('Warning message', { metric: 'high_latency' });
logger.error('Error occurred', { error: new Error('Failed') });
```

### With Context

```typescript
const logger = getLogger();

logger.info('User logged in', {
  userId: '123',
  email: 'user@example.com',
  timestamp: new Date().toISOString(),
});
```

### Child Loggers

```typescript
const logger = getLogger();

// Create child logger with request context
const requestLogger = logger.child({
  requestId: 'req-123',
  path: '/api/users',
  method: 'GET',
});

requestLogger.info('Processing request');
requestLogger.debug('Query parameters', { limit: 10 });
requestLogger.info('Request completed', { duration: 45 });
```

### Error Logging

```typescript
const logger = getLogger();

try {
  throw new Error('Database connection failed');
} catch (error) {
  logger.error(error, {
    operation: 'db_connect',
    database: 'postgres',
  });
}
```

### Custom Configuration

```typescript
import { createLogger } from '@repo/logger';

const logger = createLogger({
  name: 'my-service',
  level: 'debug',
  pretty: true,
  redact: ['password', 'token', 'apiKey'],
});

logger.info('Custom logger initialized');
```

### Next.js API Route Integration

```typescript
// app/api/users/route.ts
import { getLogger } from '@repo/logger';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const logger = getLogger().child({
    requestId: crypto.randomUUID(),
    path: request.nextUrl.pathname,
  });

  logger.info('Fetching users');

  try {
    const users = await fetchUsers();
    logger.info('Users fetched successfully', { count: users.length });
    return NextResponse.json({ users });
  } catch (error) {
    logger.error(error, { operation: 'fetch_users' });
    return NextResponse.json(
      { error: 'Failed to fetch users' },
      { status: 500 }
    );
  }
}
```

### With OpenTelemetry

```typescript
import { getLogger } from '@repo/logger';
import { getObservability } from '@repo/observability';

const logger = getLogger();
const obs = getObservability();

await obs.trace('process-data', { dataId: '123' }, async () => {
  // Logs will automatically include traceId and spanId
  logger.info('Processing data');

  const result = await processData();

  logger.info('Data processed', { resultId: result.id });
  return result;
});
```

### With AI Gateway

```typescript
import { getLogger } from '@repo/logger';
import { AIGateway } from '@repo/ai-gateway';

const logger = getLogger();
const gateway = new AIGateway([...]);

logger.info('Generating AI response');

try {
  const result = await gateway.generate({
    prompt: 'Explain quantum computing',
  });

  logger.info('AI response generated', {
    provider: result.provider,
    tokens: result.usage?.totalTokens,
  });
} catch (error) {
  logger.error(error, { operation: 'ai_generate' });
}
```

### Middleware Pattern

```typescript
// middleware.ts
import { getLogger } from '@repo/logger';
import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const requestId = crypto.randomUUID();
  const logger = getLogger().child({
    requestId,
    path: request.nextUrl.pathname,
    method: request.method,
  });

  logger.info('Request received');

  const response = NextResponse.next();
  response.headers.set('X-Request-ID', requestId);

  return response;
}
```

## API Reference

### `getLogger(config?: LoggerConfig): StructuredLogger`

Get or create the singleton logger instance.

### `createLogger(config?: LoggerConfig): StructuredLogger`

Create a new logger instance with custom configuration.

### `LoggerConfig`

```typescript
interface LoggerConfig {
  level?: 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'fatal';
  name?: string;
  pretty?: boolean;
  redact?: string[];
  destination?: string;
}
```

### `StructuredLogger`

```typescript
interface StructuredLogger {
  trace(message: string, context?: LogContext): void;
  debug(message: string, context?: LogContext): void;
  info(message: string, context?: LogContext): void;
  warn(message: string, context?: LogContext): void;
  error(message: string | Error, context?: LogContext): void;
  fatal(message: string | Error, context?: LogContext): void;
  child(context: LogContext): StructuredLogger;
}
```

## Log Levels

- **trace**: Very detailed debugging (e.g., function entry/exit)
- **debug**: Detailed debugging information
- **info**: General informational messages
- **warn**: Warning messages (non-critical issues)
- **error**: Error messages (failures that need attention)
- **fatal**: Critical errors (application cannot continue)

## Automatic Redaction

The following fields are automatically redacted:
- `password`
- `apiKey` / `api_key`
- `token`
- `secret`
- `authorization`
- `cookie`

## OpenTelemetry Correlation

When used with `@repo/observability`, logs automatically include:
- `traceId`: Distributed trace identifier
- `spanId`: Current span identifier

This enables correlation between logs and traces in observability platforms.

## Environment Variables

```bash
NODE_ENV=production  # Controls default log level and pretty printing
LOG_LEVEL=debug      # Override default log level
```

## Production Best Practices

1. **Use appropriate log levels**
   - Don't log sensitive data at info level
   - Use debug for detailed troubleshooting
   - Reserve error for actual failures

2. **Add context to logs**
   - Include requestId, userId, traceId
   - Add operation-specific metadata
   - Use child loggers for scoped context

3. **Log structured data**
   - Use context objects instead of string interpolation
   - Enables querying and filtering in log aggregation tools

4. **Avoid logging in tight loops**
   - Log at appropriate granularity
   - Consider sampling for high-frequency events

## Related Packages

- `@repo/observability` - OpenTelemetry tracing and metrics
- `@repo/ai-gateway` - Multi-model AI with logging
- `@repo/workflows` - Durable workflows with logging

## Resources

- [Pino Docs](https://getpino.io/)
- [OpenTelemetry Logs](https://opentelemetry.io/docs/specs/otel/logs/)
- [Structured Logging Best Practices](https://www.thoughtworks.com/insights/blog/structured-logging)
'''
        self._write_file(package_path / "README.md", readme)
        files_created.append("README.md")

        logger.info(f"✅ Generated structured logging package with {len(files_created)} files")
        return files_created

    async def _generate_error_handling_package(self, package_path: Path, architecture: Dict[str, Any]) -> List[str]:
        """Generate error handling package with boundaries + retry logic (Phase 3.1)"""
        logger.info("🛡️ Generating error handling package with retry logic and circuit breakers...")

        package_path.mkdir(parents=True, exist_ok=True)
        files_created = []

        # package.json
        package_json = {
            "name": "@repo/error-handling",
            "version": "0.0.0",
            "private": True,
            "type": "module",
            "exports": {
                ".": "./src/index.ts",
                "./boundary": "./src/ErrorBoundary.tsx",
                "./retry": "./src/retry.ts",
                "./circuit-breaker": "./src/circuit-breaker.ts"
            },
            "scripts": {
                "lint": "eslint . --max-warnings 0",
                "test": "jest"
            },
            "dependencies": {
                "react": "^18",
                "@repo/logger": "workspace:*"
            },
            "devDependencies": {
                "@types/react": "^18",
                "typescript": "^5",
                "eslint": "^8"
            }
        }
        self._write_file(package_path / "package.json", json.dumps(package_json, indent=2))
        files_created.append("package.json")

        # src/types.ts
        types_ts = '''export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  retryCondition?: (error: Error) => boolean;
}

export interface CircuitBreakerConfig {
  threshold: number;
  timeout: number;
}

export interface ErrorContext {
  errorId: string;
  timestamp: string;
  url?: string;
  userId?: string;
  [key: string]: any;
}
'''
        (package_path / "src").mkdir(exist_ok=True)
        self._write_file(package_path / "src" / "types.ts", types_ts)
        files_created.append("src/types.ts")

        # src/circuit-breaker.ts (from EventRelay api.ts)
        circuit_breaker_ts = '''import type { CircuitBreakerConfig } from './types';

export class CircuitBreaker {
  private failures = new Map<string, number>();
  private lastFailure = new Map<string, number>();
  private readonly threshold: number;
  private readonly timeout: number;

  constructor(config: CircuitBreakerConfig = { threshold: 5, timeout: 60000 }) {
    this.threshold = config.threshold;
    this.timeout = config.timeout;
  }

  isOpen(endpoint: string): boolean {
    const failures = this.failures.get(endpoint) || 0;
    const lastFailure = this.lastFailure.get(endpoint) || 0;

    if (failures >= this.threshold) {
      if (Date.now() - lastFailure > this.timeout) {
        // Reset circuit breaker
        this.failures.set(endpoint, 0);
        return false;
      }
      return true;
    }
    return false;
  }

  recordFailure(endpoint: string): void {
    this.failures.set(endpoint, (this.failures.get(endpoint) || 0) + 1);
    this.lastFailure.set(endpoint, Date.now());
  }

  recordSuccess(endpoint: string): void {
    this.failures.set(endpoint, 0);
  }

  reset(endpoint: string): void {
    this.failures.delete(endpoint);
    this.lastFailure.delete(endpoint);
  }
}

// Global circuit breaker instance
export const globalCircuitBreaker = new CircuitBreaker();
'''
        self._write_file(package_path / "src" / "circuit-breaker.ts", circuit_breaker_ts)
        files_created.append("src/circuit-breaker.ts")

        # src/retry.ts (exponential backoff from EventRelay)
        retry_ts = '''import type { RetryConfig } from './types';
import { getLogger } from '@repo/logger';

const logger = getLogger({ name: 'retry' });

const defaultRetryConfig: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  retryCondition: (error: Error) => {
    // Retry on network errors, timeouts, 5xx errors
    return /network|timeout|50[0-9]/.test(error.message.toLowerCase());
  },
};

export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  config: Partial<RetryConfig> = {}
): Promise<T> {
  const finalConfig: RetryConfig = { ...defaultRetryConfig, ...config };
  let lastError: Error;

  for (let attempt = 0; attempt <= finalConfig.maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      const shouldRetry = finalConfig.retryCondition
        ? finalConfig.retryCondition(lastError)
        : true;

      if (!shouldRetry || attempt >= finalConfig.maxRetries) {
        logger.error('Retry exhausted', {
          attempt,
          maxRetries: finalConfig.maxRetries,
          error: lastError.message,
        });
        throw lastError;
      }

      // Exponential backoff: baseDelay * 2^attempt
      const delay = Math.min(
        finalConfig.baseDelay * Math.pow(2, attempt),
        finalConfig.maxDelay
      );

      logger.warn('Retrying after error', {
        attempt: attempt + 1,
        maxRetries: finalConfig.maxRetries,
        delay,
        error: lastError.message,
      });

      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError!;
}

export async function retryWithCircuitBreaker<T>(
  fn: () => Promise<T>,
  endpoint: string,
  circuitBreaker: any,
  config: Partial<RetryConfig> = {}
): Promise<T> {
  if (circuitBreaker.isOpen(endpoint)) {
    throw new Error(`Circuit breaker is open for ${endpoint}`);
  }

  try {
    const result = await retryWithBackoff(fn, config);
    circuitBreaker.recordSuccess(endpoint);
    return result;
  } catch (error) {
    circuitBreaker.recordFailure(endpoint);
    throw error;
  }
}
'''
        self._write_file(package_path / "src" / "retry.ts", retry_ts)
        files_created.append("src/retry.ts")

        # src/ErrorBoundary.tsx (simplified from EventRelay GlobalErrorBoundary)
        error_boundary_tsx = '''import React, { Component, ErrorInfo, ReactNode } from 'react';
import { getLogger } from '@repo/logger';

const logger = getLogger({ name: 'error-boundary' });

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorId?: string;
  recoveryAttempts: number;
}

export class ErrorBoundary extends Component<Props, State> {
  private readonly MAX_RECOVERY_ATTEMPTS = 3;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      recoveryAttempts: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      errorId: `ERR_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    logger.error(error, {
      errorId: this.state.errorId,
      componentStack: errorInfo.componentStack,
      recoveryAttempts: this.state.recoveryAttempts,
    });

    this.props.onError?.(error, errorInfo);

    // Auto-recover from recoverable errors
    if (this.isRecoverableError(error) && this.state.recoveryAttempts < this.MAX_RECOVERY_ATTEMPTS) {
      this.attemptRecovery();
    }
  }

  private isRecoverableError(error: Error): boolean {
    const recoverablePatterns = [
      /ChunkLoadError/,
      /Loading chunk.*failed/,
      /Network.*Error/,
      /ResizeObserver loop/,
    ];

    return recoverablePatterns.some((pattern) =>
      pattern.test(error.message) || pattern.test(error.name)
    );
  }

  private attemptRecovery = () => {
    const recoveryDelay = Math.pow(2, this.state.recoveryAttempts) * 2000;

    setTimeout(() => {
      this.setState({
        hasError: false,
        error: undefined,
        recoveryAttempts: this.state.recoveryAttempts + 1,
      });

      logger.info('Automatic recovery attempted', {
        attempt: this.state.recoveryAttempts + 1,
        delay: recoveryDelay,
      });
    }, recoveryDelay);
  };

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: undefined,
      recoveryAttempts: this.state.recoveryAttempts + 1,
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full">
            <div className="text-center">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>

              <h2 className="text-xl font-semibold text-gray-900 mb-2">Something went wrong</h2>
              <p className="text-gray-600 mb-6">We encountered an error. Please try again.</p>

              {this.state.errorId && (
                <div className="bg-gray-50 rounded p-3 mb-6">
                  <div className="text-xs text-gray-500 mb-1">Error Reference</div>
                  <div className="font-mono text-sm text-gray-700">{this.state.errorId}</div>
                </div>
              )}

              <div className="space-y-2">
                {this.state.recoveryAttempts < this.MAX_RECOVERY_ATTEMPTS && (
                  <button
                    onClick={this.handleRetry}
                    className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Try Again
                  </button>
                )}

                <button
                  onClick={() => window.location.reload()}
                  className="w-full bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  Reload Page
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
'''
        self._write_file(package_path / "src" / "ErrorBoundary.tsx", error_boundary_tsx)
        files_created.append("src/ErrorBoundary.tsx")

        # src/index.ts - barrel export
        index_ts = '''export { ErrorBoundary } from './ErrorBoundary';
export { CircuitBreaker, globalCircuitBreaker } from './circuit-breaker';
export { retryWithBackoff, retryWithCircuitBreaker } from './retry';
export type { RetryConfig, CircuitBreakerConfig, ErrorContext } from './types';
'''
        self._write_file(package_path / "src" / "index.ts", index_ts)
        files_created.append("src/index.ts")

        # tsconfig.json
        tsconfig = {
            "extends": "@repo/typescript-config/react-library.json",
            "compilerOptions": {
                "outDir": "dist",
                "rootDir": "src"
            },
            "include": ["src"],
            "exclude": ["node_modules", "dist"]
        }
        self._write_file(package_path / "tsconfig.json", json.dumps(tsconfig, indent=2))
        files_created.append("tsconfig.json")

        # README.md
        readme = '''# @repo/error-handling

Production-grade error handling with boundaries, retry logic, and circuit breakers.

## Features

- ✅ **Error Boundaries**: React error boundaries with auto-recovery
- ✅ **Retry Logic**: Exponential backoff with configurable conditions
- ✅ **Circuit Breakers**: Prevent cascading failures
- ✅ **Structured Logging**: Integrated with @repo/logger
- ✅ **TypeScript**: Full type safety

## Usage

### Error Boundary

```typescript
import { ErrorBoundary } from '@repo/error-handling';

function App() {
  return (
    <ErrorBoundary fallback={<div>Custom error UI</div>}>
      <YourApp />
    </ErrorBoundary>
  );
}
```

### Retry with Backoff

```typescript
import { retryWithBackoff } from '@repo/error-handling';

const data = await retryWithBackoff(
  async () => fetch('/api/data').then(r => r.json()),
  {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000,
  }
);
```

### Circuit Breaker

```typescript
import { globalCircuitBreaker } from '@repo/error-handling';

if (globalCircuitBreaker.isOpen('/api/endpoint')) {
  // Serve fallback or cached data
  return getCachedData();
}

try {
  const result = await fetch('/api/endpoint');
  globalCircuitBreaker.recordSuccess('/api/endpoint');
  return result;
} catch (error) {
  globalCircuitBreaker.recordFailure('/api/endpoint');
  throw error;
}
```

## Based On

EventRelay production implementations:
- frontend/src/components/ErrorBoundary/GlobalErrorBoundary.tsx
- frontend/src/services/api.ts
'''
        self._write_file(package_path / "README.md", readme)
        files_created.append("README.md")

        logger.info(f"✅ Generated error handling package with {len(files_created)} files")
        return files_created

    async def _generate_database_package(self, package_path: Path, architecture: Dict[str, Any]) -> List[str]:
        """Generate Prisma + Supabase database package (Phase 3.2)"""
        logger.info("🗄️ Generating Prisma + Supabase database package...")

        package_path.mkdir(parents=True, exist_ok=True)
        files_created = []

        # package.json
        package_json = {
            "name": "@repo/database",
            "version": "0.0.0",
            "private": True,
            "type": "module",
            "exports": {
                ".": "./src/index.ts",
                "./client": "./src/client.ts",
                "./seed": "./src/seed.ts"
            },
            "scripts": {
                "db:generate": "prisma generate",
                "db:push": "prisma db push",
                "db:migrate": "prisma migrate dev",
                "db:migrate:prod": "prisma migrate deploy",
                "db:seed": "tsx src/seed.ts",
                "db:studio": "prisma studio",
                "db:reset": "prisma migrate reset --force"
            },
            "dependencies": {
                "@prisma/client": "^5.7.0",
                "@supabase/supabase-js": "^2.39.0"
            },
            "devDependencies": {
                "prisma": "^5.7.0",
                "tsx": "^4.7.0",
                "typescript": "^5",
                "@types/node": "^20"
            }
        }
        self._write_file(package_path / "package.json", json.dumps(package_json, indent=2))
        files_created.append("package.json")

        # prisma/schema.prisma
        prisma_schema = '''generator client {
  provider = "prisma-client-js"
  previewFeatures = ["driverAdapters"]
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
  directUrl = env("DIRECT_URL")
}

model User {
  id            String    @id @default(cuid())
  email         String    @unique
  name          String?
  emailVerified DateTime?
  image         String?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt

  sessions      Session[]
  apiKeys       ApiKey[]

  @@map("users")
}

model Session {
  id           String   @id @default(cuid())
  sessionToken String   @unique
  userId       String
  expires      DateTime
  user         User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  createdAt    DateTime @default(now())
  updatedAt    DateTime @updatedAt

  @@map("sessions")
}

model ApiKey {
  id        String   @id @default(cuid())
  name      String
  key       String   @unique
  userId    String
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  expiresAt DateTime?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@map("api_keys")
}

model AuditLog {
  id        String   @id @default(cuid())
  action    String
  userId    String?
  metadata  Json?
  createdAt DateTime @default(now())

  @@index([userId])
  @@index([createdAt])
  @@map("audit_logs")
}
'''
        (package_path / "prisma").mkdir(exist_ok=True)
        self._write_file(package_path / "prisma" / "schema.prisma", prisma_schema)
        files_created.append("prisma/schema.prisma")

        # src/client.ts
        client_ts = '''import { PrismaClient } from '@prisma/client';
import { getLogger } from '@repo/logger';

const logger = getLogger({ name: 'database' });

declare global {
  var prisma: PrismaClient | undefined;
}

export const prisma =
  global.prisma ||
  new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
  });

if (process.env.NODE_ENV !== 'production') {
  global.prisma = prisma;
}

// Graceful shutdown
process.on('beforeExit', async () => {
  logger.info('Disconnecting from database');
  await prisma.$disconnect();
});

export default prisma;
'''
        (package_path / "src").mkdir(exist_ok=True)
        self._write_file(package_path / "src" / "client.ts", client_ts)
        files_created.append("src/client.ts")

        # src/supabase.ts
        supabase_ts = '''import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
  },
});

// For server-side usage with service role key
export function getServerSupabase() {
  const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseServiceKey) {
    throw new Error('Missing SUPABASE_SERVICE_ROLE_KEY');
  }

  return createClient(supabaseUrl, supabaseServiceKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}
'''
        self._write_file(package_path / "src" / "supabase.ts", supabase_ts)
        files_created.append("src/supabase.ts")

        # src/seed.ts
        seed_ts = '''import { prisma } from './client';
import { getLogger } from '@repo/logger';

const logger = getLogger({ name: 'seed' });

async function main() {
  logger.info('Starting database seed');

  // Create demo user
  const user = await prisma.user.upsert({
    where: { email: 'demo@example.com' },
    update: {},
    create: {
      email: 'demo@example.com',
      name: 'Demo User',
      emailVerified: new Date(),
    },
  });

  logger.info('Created demo user', { userId: user.id });

  // Create demo API key
  const apiKey = await prisma.apiKey.upsert({
    where: { key: 'demo_api_key_12345' },
    update: {},
    create: {
      name: 'Demo API Key',
      key: 'demo_api_key_12345',
      userId: user.id,
      expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000), // 1 year
    },
  });

  logger.info('Created demo API key', { apiKeyId: apiKey.id });

  logger.info('Database seed completed');
}

main()
  .catch((e) => {
    logger.error('Seed failed', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
'''
        self._write_file(package_path / "src" / "seed.ts", seed_ts)
        files_created.append("src/seed.ts")

        # src/migrations.ts
        migrations_ts = '''import { prisma } from './client';
import { getLogger } from '@repo/logger';

const logger = getLogger({ name: 'migrations' });

export async function runMigrations() {
  try {
    logger.info('Running database migrations');

    // Prisma handles migrations via CLI
    // This is for application-level data migrations

    logger.info('Migrations completed');
    return { success: true };
  } catch (error) {
    logger.error('Migration failed', error);
    throw error;
  }
}

export async function checkDatabaseConnection() {
  try {
    await prisma.$queryRaw`SELECT 1`;
    logger.info('Database connection successful');
    return true;
  } catch (error) {
    logger.error('Database connection failed', error);
    return false;
  }
}
'''
        self._write_file(package_path / "src" / "migrations.ts", migrations_ts)
        files_created.append("src/migrations.ts")

        # src/index.ts
        index_ts = '''export { prisma } from './client';
export { supabase, getServerSupabase } from './supabase';
export { runMigrations, checkDatabaseConnection } from './migrations';
export * from '@prisma/client';
'''
        self._write_file(package_path / "src" / "index.ts", index_ts)
        files_created.append("src/index.ts")

        # .env.example
        env_example = '''# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Database URLs (from Supabase)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?pgbouncer=true
DIRECT_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
'''
        self._write_file(package_path / ".env.example", env_example)
        files_created.append(".env.example")

        # tsconfig.json
        tsconfig = {
            "extends": "@repo/typescript-config/base.json",
            "compilerOptions": {
                "outDir": "dist",
                "rootDir": "src"
            },
            "include": ["src"],
            "exclude": ["node_modules", "dist"]
        }
        self._write_file(package_path / "tsconfig.json", json.dumps(tsconfig, indent=2))
        files_created.append("tsconfig.json")

        # README.md
        readme = '''# @repo/database

Prisma ORM + Supabase PostgreSQL database package.

## Features

- ✅ **Prisma ORM**: Type-safe database access
- ✅ **Supabase**: Managed PostgreSQL + real-time + auth
- ✅ **Migrations**: Version-controlled schema changes
- ✅ **Seed Data**: Development data utilities
- ✅ **TypeScript**: Full type safety

## Setup

### 1. Create Supabase Project

```bash
# Visit https://supabase.com/dashboard
# Create new project and get connection details
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Fill in your Supabase credentials
```

### 3. Generate Prisma Client

```bash
npm run db:generate
```

### 4. Push Schema to Database

```bash
# Development (creates tables without migrations)
npm run db:push

# Production (runs migrations)
npm run db:migrate:prod
```

### 5. Seed Database

```bash
npm run db:seed
```

## Usage

### Basic Queries

```typescript
import { prisma } from '@repo/database';

// Create user
const user = await prisma.user.create({
  data: {
    email: 'user@example.com',
    name: 'John Doe',
  },
});

// Find users
const users = await prisma.user.findMany({
  where: {
    emailVerified: { not: null },
  },
  include: {
    sessions: true,
  },
});

// Update user
await prisma.user.update({
  where: { id: user.id },
  data: { name: 'Jane Doe' },
});
```

### With Supabase Real-time

```typescript
import { supabase } from '@repo/database';

// Subscribe to table changes
const subscription = supabase
  .channel('users')
  .on('postgres_changes', {
    event: '*',
    schema: 'public',
    table: 'users',
  }, (payload) => {
    console.log('Change received!', payload);
  })
  .subscribe();
```

### Server-side with Service Role

```typescript
import { getServerSupabase } from '@repo/database';

// Use in API routes for admin operations
const supabase = getServerSupabase();

const { data, error } = await supabase
  .from('users')
  .select('*')
  .eq('id', userId);
```

## Database Scripts

```bash
# Generate Prisma client
npm run db:generate

# Push schema changes (dev)
npm run db:push

# Create migration
npm run db:migrate

# Deploy migrations (prod)
npm run db:migrate:prod

# Seed database
npm run db:seed

# Open Prisma Studio
npm run db:studio

# Reset database
npm run db:reset
```

## Schema

Current schema includes:
- **User**: User accounts
- **Session**: User sessions
- **ApiKey**: API authentication keys
- **AuditLog**: Activity logging

Add your models to `prisma/schema.prisma`:

```prisma
model Post {
  id        String   @id @default(cuid())
  title     String
  content   String?
  published Boolean  @default(false)
  authorId  String
  author    User     @relation(fields: [authorId], references: [id])
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@map("posts")
}
```

Then run:
```bash
npm run db:generate
npm run db:migrate
```

## Supabase Features

### Authentication

```typescript
import { supabase } from '@repo/database';

// Sign up
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password',
});

// Sign in
await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password',
});

// Get session
const { data: { session } } = await supabase.auth.getSession();
```

### Storage

```typescript
// Upload file
const { data, error } = await supabase.storage
  .from('avatars')
  .upload('public/avatar.png', file);

// Get public URL
const { data } = supabase.storage
  .from('avatars')
  .getPublicUrl('public/avatar.png');
```

## Production Checklist

- [ ] Set `DATABASE_URL` and `DIRECT_URL` in production
- [ ] Run `db:migrate:prod` on deployment
- [ ] Enable Row Level Security (RLS) in Supabase
- [ ] Set up database backups
- [ ] Configure connection pooling
- [ ] Monitor query performance

## Resources

- [Prisma Docs](https://www.prisma.io/docs)
- [Supabase Docs](https://supabase.com/docs)
- [Prisma + Supabase Guide](https://supabase.com/docs/guides/integrations/prisma)
'''
        self._write_file(package_path / "README.md", readme)
        files_created.append("README.md")

        logger.info(f"✅ Generated Prisma + Supabase database package with {len(files_created)} files")
        return files_created

    async def _generate_config_package(self, package_path: Path, architecture: Dict[str, Any]) -> List[str]:
        """Generate environment configuration package (Phase 3.3)"""
        logger.info("⚙️ Generating environment configuration package...")

        package_path.mkdir(parents=True, exist_ok=True)
        files_created = []

        # package.json
        package_json = {
            "name": "@repo/config",
            "version": "0.0.0",
            "private": True,
            "type": "module",
            "exports": {
                ".": "./src/index.ts",
                "./env": "./src/env.ts",
                "./constants": "./src/constants.ts"
            },
            "scripts": {
                "lint": "eslint . --max-warnings 0",
                "type-check": "tsc --noEmit"
            },
            "dependencies": {
                "zod": "^3.22.4"
            },
            "devDependencies": {
                "typescript": "^5",
                "@types/node": "^20"
            }
        }
        self._write_file(package_path / "package.json", json.dumps(package_json, indent=2))
        files_created.append("package.json")

        # src/env.ts - Type-safe environment variables with Zod
        env_ts = '''import { z } from 'zod';

const envSchema = z.object({
  // Node Environment
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),

  // Supabase
  NEXT_PUBLIC_SUPABASE_URL: z.string().url().optional(),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().optional(),
  SUPABASE_SERVICE_ROLE_KEY: z.string().optional(),

  // Database
  DATABASE_URL: z.string().optional(),
  DIRECT_URL: z.string().optional(),

  // AI Providers
  XAI_API_KEY: z.string().optional(),
  ANTHROPIC_API_KEY: z.string().optional(),
  GOOGLE_GENERATIVE_AI_API_KEY: z.string().optional(),
  OPENAI_API_KEY: z.string().optional(),

  // Observability
  OTEL_EXPORTER_OTLP_ENDPOINT: z.string().url().optional(),

  // App Configuration
  NEXT_PUBLIC_APP_URL: z.string().url().optional(),
  NEXTAUTH_SECRET: z.string().optional(),
  NEXTAUTH_URL: z.string().url().optional(),
});

export type Env = z.infer<typeof envSchema>;

function validateEnv(): Env {
  const parsed = envSchema.safeParse(process.env);

  if (!parsed.success) {
    console.error('❌ Invalid environment variables:');
    console.error(JSON.stringify(parsed.error.format(), null, 2));
    throw new Error('Invalid environment variables');
  }

  return parsed.data;
}

export const env = validateEnv();

// Runtime environment checks
export const isDevelopment = env.NODE_ENV === 'development';
export const isProduction = env.NODE_ENV === 'production';
export const isTest = env.NODE_ENV === 'test';
'''
        (package_path / "src").mkdir(exist_ok=True)
        self._write_file(package_path / "src" / "env.ts", env_ts)
        files_created.append("src/env.ts")

        # src/constants.ts
        constants_ts = '''export const APP_NAME = 'AI Infrastructure Platform';
export const APP_DESCRIPTION = 'Production-ready AI infrastructure';

export const API_VERSION = 'v1';
export const API_PREFIX = `/api/${API_VERSION}`;

export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

export const CACHE_TTL = {
  SHORT: 60, // 1 minute
  MEDIUM: 300, // 5 minutes
  LONG: 3600, // 1 hour
  DAY: 86400, // 24 hours
} as const;

export const RATE_LIMITS = {
  ANONYMOUS: {
    requests: 10,
    window: 60, // per minute
  },
  AUTHENTICATED: {
    requests: 100,
    window: 60,
  },
  PREMIUM: {
    requests: 1000,
    window: 60,
  },
} as const;

export const RETRY_CONFIG = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
} as const;
'''
        self._write_file(package_path / "src" / "constants.ts", constants_ts)
        files_created.append("src/constants.ts")

        # src/index.ts
        index_ts = '''export { env, isDevelopment, isProduction, isTest } from './env';
export type { Env } from './env';
export * from './constants';
'''
        self._write_file(package_path / "src" / "index.ts", index_ts)
        files_created.append("src/index.ts")

        # .env.example
        env_example = '''# Node Environment
NODE_ENV=development

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Database
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?pgbouncer=true
DIRECT_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# AI Providers (add keys for providers you want to use)
XAI_API_KEY=your-grok-api-key
ANTHROPIC_API_KEY=your-claude-api-key
GOOGLE_GENERATIVE_AI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# Observability (optional)
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-otel-collector:4318

# App Configuration
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3000
'''
        self._write_file(package_path / ".env.example", env_example)
        files_created.append(".env.example")

        # tsconfig.json
        tsconfig = {
            "extends": "@repo/typescript-config/base.json",
            "compilerOptions": {
                "outDir": "dist",
                "rootDir": "src"
            },
            "include": ["src"],
            "exclude": ["node_modules", "dist"]
        }
        self._write_file(package_path / "tsconfig.json", json.dumps(tsconfig, indent=2))
        files_created.append("tsconfig.json")

        # README.md
        readme = '''# @repo/config

Type-safe environment configuration with Zod validation.

## Features

- ✅ **Type Safety**: Zod schema validation
- ✅ **Runtime Validation**: Catches missing/invalid env vars at startup
- ✅ **Auto-completion**: Full TypeScript support
- ✅ **Constants**: Centralized configuration values

## Usage

### Environment Variables

```typescript
import { env, isDevelopment, isProduction } from '@repo/config';

// Type-safe access to env vars
const supabaseUrl = env.NEXT_PUBLIC_SUPABASE_URL;
const apiKey = env.ANTHROPIC_API_KEY;

// Runtime checks
if (isDevelopment) {
  console.log('Running in development mode');
}
```

### Constants

```typescript
import {
  APP_NAME,
  API_PREFIX,
  CACHE_TTL,
  RATE_LIMITS,
  RETRY_CONFIG,
} from '@repo/config';

// Use in your application
const cacheKey = `${APP_NAME}:user:${userId}`;
const ttl = CACHE_TTL.MEDIUM;

// Rate limiting
const limit = RATE_LIMITS.AUTHENTICATED.requests;
```

## Setup

1. Copy `.env.example` to `.env` in your app root:

```bash
cp packages/config/.env.example .env
```

2. Fill in your environment variables

3. The config package will validate on startup:

```typescript
import '@repo/config'; // Validates env on import

// Or explicitly validate
import { env } from '@repo/config';
```

## Adding New Environment Variables

1. Update `src/env.ts`:

```typescript
const envSchema = z.object({
  // ... existing vars

  // Add your new variable
  MY_NEW_VAR: z.string().min(1),
});
```

2. Update `.env.example`

3. TypeScript will now require this variable

## Environment Variable Types

- **Public** (`NEXT_PUBLIC_*`): Exposed to browser
- **Private**: Server-only, never sent to browser
- **Optional** (`.optional()`): Not required
- **With Default** (`.default(value)`): Fallback value

## Validation

The package will throw an error on startup if:
- Required variables are missing
- Variables don't match the schema (wrong type, invalid URL, etc.)

```typescript
// ❌ Invalid environment variables:
// {
//   "_errors": [],
//   "DATABASE_URL": {
//     "_errors": ["Required"]
//   }
// }
```

## Best Practices

1. **Never commit `.env`**: Add to `.gitignore`
2. **Use Vercel for secrets**: Set in dashboard for production
3. **Rotate keys regularly**: Update in all environments
4. **Type everything**: Use Zod for validation
5. **Document variables**: Update `.env.example`

## Vercel Deployment

Set environment variables in Vercel dashboard:

```bash
# Or use Vercel CLI
vercel env add DATABASE_URL
vercel env add ANTHROPIC_API_KEY
```

## Resources

- [Zod Documentation](https://zod.dev/)
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)
- [Next.js Environment Variables](https://nextjs.org/docs/basic-features/environment-variables)
'''
        self._write_file(package_path / "README.md", readme)
        files_created.append("README.md")

        logger.info(f"✅ Generated environment configuration package with {len(files_created)} files")
        return files_created

    async def _generate_fastapi_project(
        self,
        project_path: Path,
        architecture: Dict[str, Any],
        video_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate Python FastAPI project - placeholder for future"""
        # For now, delegate to Next.js
        return await self._generate_nextjs_project(
            project_path, architecture, video_analysis
        )


# Global instance
_ai_code_generator = None

def get_ai_code_generator() -> AICodeGenerator:
    """Get or create global AI code generator instance"""
    global _ai_code_generator
    if _ai_code_generator is None:
        _ai_code_generator = AICodeGenerator()
    return _ai_code_generator
