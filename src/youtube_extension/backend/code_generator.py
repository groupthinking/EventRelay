#!/usr/bin/env python3
"""
Code Generator for UVAI Video-to-Software Pipeline
==================================================

This module generates actual project code based on video analysis,
creating deployable applications from YouTube tutorial content.
"""

import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class ProjectCodeGenerator:
    """
    Generates project code based on video analysis results
    """

    def __init__(self):
        self.templates_dir = Path(__file__).parent / "templates"
        self.ensure_templates_directory()

    def ensure_templates_directory(self):
        """Ensure templates directory exists"""
        self.templates_dir.mkdir(exist_ok=True)

        # Create basic templates if they don't exist
        self._create_basic_templates()

    async def generate_project(self, video_analysis: dict[str, Any], project_config: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a complete project based on video analysis
        """
        logger.info(f"🏗️ Generating project: {project_config.get('type', 'web')}")

        try:
            # Extract project information
            extracted_info = video_analysis.get("extracted_info", {})
            project_type = project_config.get("type", extracted_info.get("project_type", "web"))
            technologies = extracted_info.get("technologies", ["javascript", "html", "css"])
            features = project_config.get("features", extracted_info.get("features", []))

            # Create temporary project directory
            temp_dir = tempfile.mkdtemp(prefix="uvai_project_")
            project_path = Path(temp_dir)

            # Generate project structure based on type
            if project_type == "web":
                result = await self._generate_web_project(project_path, video_analysis, technologies, features)
            elif project_type == "api":
                result = await self._generate_api_project(project_path, video_analysis, technologies, features)
            elif project_type == "mobile":
                result = await self._generate_mobile_project(project_path, video_analysis, technologies, features)
            else:
                result = await self._generate_web_project(project_path, video_analysis, technologies, features)

            result["project_path"] = str(project_path)
            result["project_type"] = project_type
            result["technologies"] = technologies
            result["features"] = features

            logger.info(f"✅ Project generated successfully at {project_path}")
            return result

        except Exception as e:
            logger.error(f"❌ Project generation failed: {e}")
            raise

    async def _generate_web_project(self, project_path: Path, video_analysis: dict, technologies: list[str], features: list[str]) -> dict[str, Any]:
        """Generate a web application project"""

        extracted_info = video_analysis.get("extracted_info", {})
        extracted_info.get("title", "UVAI Generated Project")

        # Determine the tech stack
        if "react" in technologies:
            return await self._generate_react_project(project_path, video_analysis, features)
        elif "vue" in technologies:
            return await self._generate_vue_project(project_path, video_analysis, features)
        else:
            return await self._generate_vanilla_js_project(project_path, video_analysis, features)

    async def _generate_react_project(self, project_path: Path, video_analysis: dict, features: list[str]) -> dict[str, Any]:
        """Generate a React project"""

        extracted_info = video_analysis.get("extracted_info", {})
        title = extracted_info.get("title", "UVAI React App")
        tutorial_steps = extracted_info.get("tutorial_steps", [])

        # Create package.json
        package_json = {
            "name": self._sanitize_name(title),
            "version": "1.0.0",
            "description": f"Generated from YouTube tutorial: {title}",
            "main": "src/index.js",
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build",
                "test": "react-scripts test",
                "eject": "react-scripts eject"
            },
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-scripts": "5.0.1"
            },
            "browserslist": {
                "production": [">0.2%", "not dead", "not op_mini all"],
                "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]
            }
        }

        # Add additional dependencies based on features
        if "authentication" in features:
            package_json["dependencies"]["@auth0/auth0-react"] = "^2.2.0"
        if "api_integration" in features:
            package_json["dependencies"]["axios"] = "^1.4.0"
        if "responsive_design" in features or "tailwind" in video_analysis.get("extracted_info", {}).get("technologies", []):
            package_json["dependencies"]["tailwindcss"] = "^3.3.0"
            package_json["devDependencies"] = {"autoprefixer": "^10.4.14", "postcss": "^8.4.24"}

        # Write package.json
        with open(project_path / "package.json", "w") as f:
            json.dump(package_json, f, indent=2)

        # Create src directory
        src_dir = project_path / "src"
        src_dir.mkdir(exist_ok=True)

        # Create public directory
        public_dir = project_path / "public"
        public_dir.mkdir(exist_ok=True)

        # Generate index.html
        index_html = self._generate_index_html(title)
        with open(public_dir / "index.html", "w") as f:
            f.write(index_html)

        # Generate main App component
        technologies = extracted_info.get("technologies", [])
        app_component = self._generate_react_app_component(title, technologies, tutorial_steps, features)
        with open(src_dir / "App.js", "w") as f:
            f.write(app_component)

        # Generate index.js
        index_js = self._generate_react_index_js()
        with open(src_dir / "index.js", "w") as f:
            f.write(index_js)

        # Generate CSS
        app_css = self._generate_app_css(features)
        with open(src_dir / "App.css", "w") as f:
            f.write(app_css)

        # Generate README
        readme = self._generate_readme(title, "React", video_analysis)
        with open(project_path / "README.md", "w") as f:
            f.write(readme)

        return {
            "framework": "react",
            "entry_point": "src/App.js",
            "build_command": "npm run build",
            "start_command": "npm start",
            "files_created": ["package.json", "src/App.js", "src/index.js", "src/App.css", "public/index.html", "README.md"]
        }

    async def _generate_vanilla_js_project(self, project_path: Path, video_analysis: dict, features: list[str]) -> dict[str, Any]:
        """Generate a vanilla JavaScript project"""

        extracted_info = video_analysis.get("extracted_info", {})
        title = extracted_info.get("title", "UVAI Web App")
        technologies = extracted_info.get("technologies", [])
        tutorial_steps = extracted_info.get("tutorial_steps", [])

        # Generate index.html
        index_html = self._generate_vanilla_index_html(title, technologies, tutorial_steps, features)
        with open(project_path / "index.html", "w") as f:
            f.write(index_html)

        # Generate main.js
        main_js = self._generate_vanilla_main_js(tutorial_steps, features)
        with open(project_path / "main.js", "w") as f:
            f.write(main_js)

        # Generate styles.css
        styles_css = self._generate_vanilla_styles_css(features)
        with open(project_path / "styles.css", "w") as f:
            f.write(styles_css)

        # Generate README
        readme = self._generate_readme(title, "Vanilla JavaScript", video_analysis)
        with open(project_path / "README.md", "w") as f:
            f.write(readme)

        return {
            "framework": "vanilla",
            "entry_point": "index.html",
            "build_command": None,
            "start_command": "Open index.html in browser",
            "files_created": ["index.html", "main.js", "styles.css", "README.md"]
        }

    async def _generate_api_project(self, project_path: Path, video_analysis: dict, technologies: list[str], features: list[str]) -> dict[str, Any]:
        """Generate an API project"""

        extracted_info = video_analysis.get("extracted_info", {})
        extracted_info.get("title", "UVAI API")

        if "python" in technologies:
            return await self._generate_python_api(project_path, video_analysis, features)
        elif "nodejs" in technologies:
            return await self._generate_node_api(project_path, video_analysis, features)
        else:
            return await self._generate_python_api(project_path, video_analysis, features)

    async def _generate_python_api(self, project_path: Path, video_analysis: dict, features: list[str]) -> dict[str, Any]:
        """Generate a Python FastAPI project"""

        extracted_info = video_analysis.get("extracted_info", {})
        title = extracted_info.get("title", "UVAI Python API")

        # Create requirements.txt for generated project
        requirements = [
            "fastapi==0.104.1",
            "uvicorn==0.24.0",
            "pydantic==2.5.0"
        ]
        if "database" in features:
            requirements.append("sqlalchemy==2.0.23")
        if "authentication" in features:
            requirements.append("python-jose[cryptography]==3.3.0")
        with open(project_path / "requirements.txt", "w") as f:
            f.write("\n".join(requirements))

        # Generate main.py
        main_py = self._generate_fastapi_main(title, features, extracted_info)
        with open(project_path / "main.py", "w") as f:
            f.write(main_py)

        # Generate README
        readme = self._generate_readme(title, "Python FastAPI", video_analysis)
        with open(project_path / "README.md", "w") as f:
            f.write(readme)

        return {
            "framework": "fastapi",
            "entry_point": "main.py",
            "build_command": "pip install -r requirements.txt",
            "start_command": "uvicorn main:app --reload",
            "files_created": ["main.py", "requirements.txt", "README.md"]
        }

    def _generate_index_html(self, title: str) -> str:
        """Generate index.html for React projects"""
        return f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta name="description" content="{title} - Generated by UVAI" />
    <title>{title}</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>'''

    def _generate_react_app_component(self, title: str, technologies: list[str], tutorial_steps: list[str], features: list[str]) -> str:
        """Generate the main React App component"""
        steps_jsx = ""
        if tutorial_steps:
            steps_list = "\\n".join([f"        <li key={i}>{step[:100]}...</li>" for i, step in enumerate(tutorial_steps[:5])])
            steps_jsx = f'''
      <section className="tutorial-steps">
        <h2>Tutorial Steps</h2>
        <ol>
{steps_list}
        </ol>
      </section>'''

        tech_jsx = ""
        if technologies:
            tech_items = "\\n".join([f"          <div key='{tech}' className='tech-card'>{tech}</div>" for tech in technologies])
            tech_jsx = f'''
      <section className="technologies">
        <h2>Technologies Used</h2>
        <div className="tech-cards">
{tech_items}
        </div>
      </section>'''

        features_jsx = ""
        if features:
            feature_items = "\\n".join([f"          <div key='{feature}' className='feature-card'>{feature.replace('_', ' ').title()}</div>" for feature in features[:8]])
            features_jsx = f'''
      <section className="features">
        <h2>Features</h2>
        <div className="feature-cards">
{feature_items}
        </div>
      </section>'''

        return f'''import React from 'react';
import './App.css';

function App() {{
  return (
    <div className="App">
      <header className="App-header">
        <h1>{title}</h1>
        <p>Generated by UVAI from YouTube tutorial</p>
      </header>

      <main className="App-main">
        <section className="welcome">
          <h2>Built from Video Analysis</h2>
          <p>This project was generated by analyzing the video tutorial
             &ldquo;<strong>{title}</strong>&rdquo; and extracting the key
             technologies, features, and implementation steps.</p>
        </section>
{tech_jsx}
{steps_jsx}
{features_jsx}
      </main>

      <footer className="App-footer">
        <p>Powered by UVAI - Universal Video-to-Action Intelligence</p>
      </footer>
    </div>
  );
}}

export default App;'''

    def _generate_react_index_js(self) -> str:
        """Generate React index.js"""
        return '''import React from 'react';
import ReactDOM from 'react-dom/client';
import './App.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);'''

    def _generate_app_css(self, features: list[str]) -> str:
        """Generate App.css"""
        responsive_css = ""
        if "responsive_design" in features:
            responsive_css = '''
@media (max-width: 768px) {
  .App-main {
    padding: 1rem;
  }

  .App-header h1 {
    font-size: 2rem;
  }
}'''

        return f'''body {{
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}

.App {{
  text-align: center;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}}

.App-header {{
  background-color: #282c34;
  padding: 2rem;
  color: white;
}}

.App-header h1 {{
  margin: 0 0 1rem 0;
  font-size: 2.5rem;
}}

.App-main {{
  flex: 1;
  padding: 2rem;
  background-color: #f5f5f5;
}}

.welcome {{
  background: white;
  padding: 2rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}}

.tutorial-steps, .features, .technologies {{
  background: white;
  padding: 2rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  text-align: left;
}}

.tech-cards, .feature-cards {{
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: center;
  margin-top: 1rem;
}}

.tech-card {{
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 0.75rem 1.25rem;
  border-radius: 8px;
  font-weight: 600;
}}

.feature-card {{
  background: #e3f2fd;
  padding: 0.75rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  color: #1565c0;
}}

.tutorial-steps ol {{
  max-width: 800px;
  margin: 0 auto;
}}

.tutorial-steps li {{
  margin-bottom: 0.5rem;
  line-height: 1.5;
}}

.App-footer {{
  background-color: #282c34;
  color: white;
  padding: 1rem;
  margin-top: auto;
}}
{responsive_css}'''

    def _generate_vanilla_index_html(self, title: str, technologies: list[str], tutorial_steps: list[str], features: list[str]) -> str:
        """Generate index.html for vanilla JS projects"""
        steps_html = ""
        if tutorial_steps:
            steps_list = "\\n".join([f"      <li>{step[:100]}...</li>" for step in tutorial_steps[:5]])
            steps_html = f'''
    <section class="tutorial-steps">
      <h2>Tutorial Steps</h2>
      <ol>
{steps_list}
      </ol>
    </section>'''

        tech_html = ""
        if technologies:
            tech_cards = "\\n".join([f'            <div class="tech-card">{tech}</div>' for tech in technologies])
            tech_html = f'''
    <section class="technologies">
      <h2>Technologies Used</h2>
      <div class="tech-cards">
{tech_cards}
      </div>
    </section>'''

        features_html = ""
        if features:
            feature_cards = "\\n".join([f'            <div class="feature-card">{feature.replace("_", " ").title()}</div>' for feature in features[:8]])
            features_html = f'''
    <section class="features">
      <h2>Features</h2>
      <div class="feature-cards">
{feature_cards}
      </div>
    </section>'''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="app">
        <header class="app-header">
            <h1>{title}</h1>
            <p>Generated by UVAI from YouTube tutorial</p>
        </header>

        <main class="app-main">
            <section class="welcome">
                <h2>Built from Video Analysis</h2>
                <p>This project was generated by analyzing the video tutorial
                   &ldquo;<strong>{title}</strong>&rdquo; and extracting the key
                   technologies, features, and implementation steps.</p>
            </section>
{tech_html}
{steps_html}
{features_html}
        </main>

        <footer class="app-footer">
            <p>Powered by UVAI - Universal Video-to-Action Intelligence</p>
        </footer>
    </div>

    <script src="main.js"></script>
</body>
</html>'''

    def _generate_vanilla_main_js(self, tutorial_steps: list[str], features: list[str]) -> str:
        """Generate main.js for vanilla projects, tailored to tutorial steps and features"""
        # Build per-step functions from extracted tutorial steps
        step_functions = ""
        step_calls = ""
        for i, step in enumerate(tutorial_steps[:8], 1):
            safe_desc = step[:100].replace("\\", "\\\\").replace("'", "\\'").replace("`", "\\`")
            func_name = f"executeStep{i}"
            step_functions += f"""
function {func_name}() {{
    // Step {i}: {safe_desc}
    console.log('Step {i}: {safe_desc}');
    updateStatus('Completed step {i}');
}}
"""
            step_calls += f"    {func_name}();\n"

        if not step_calls:
            step_calls = "    // No tutorial steps extracted – add your own steps here\n"

        # Build feature-specific initialisation code
        feature_init = ""
        if any(f in features for f in ("form", "input", "form_handling")):
            feature_init += "\n    setupFormHandlers();"
        if any(f in features for f in ("api_integration", "fetch", "http")):
            feature_init += "\n    fetchInitialData();"
        if "dark_mode" in features:
            feature_init += "\n    setupDarkModeToggle();"
        if any(f in features for f in ("search", "filtering")):
            feature_init += "\n    initSearch();"

        # Build feature-specific helper functions
        feature_helpers = ""
        if any(f in features for f in ("form", "input", "form_handling")):
            feature_helpers += """
function setupFormHandlers() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('Form submitted:', new FormData(form));
        });
    });
}
"""
        if any(f in features for f in ("api_integration", "fetch", "http")):
            feature_helpers += """
async function fetchInitialData() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        console.log('Data loaded:', data);
    } catch (err) {
        console.error('Failed to load data:', err);
    }
}
"""
        if "dark_mode" in features:
            feature_helpers += """
function setupDarkModeToggle() {
    const toggle = document.getElementById('dark-mode-toggle');
    if (toggle) {
        toggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
        });
    }
}
"""
        if any(f in features for f in ("search", "filtering")):
            feature_helpers += """
function initSearch() {
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            document.querySelectorAll('[data-searchable]').forEach(el => {
                el.style.display = el.textContent.toLowerCase().includes(query) ? '' : 'none';
            });
        });
    }
}
"""

        steps_comment = (
            f"// Tutorial steps ({len(tutorial_steps)}): "
            + " | ".join(s[:60] for s in tutorial_steps[:3])
            if tutorial_steps
            else "// No tutorial steps extracted from video"
        )
        features_comment = (
            f"// Features: {', '.join(features)}" if features else "// No specific features detected"
        )

        return f"""// UVAI Generated JavaScript
{steps_comment}
{features_comment}

function updateStatus(message) {{
    const statusEl = document.getElementById('status');
    if (statusEl) statusEl.textContent = message;
    console.log('[Status]', message);
}}

document.addEventListener('DOMContentLoaded', function() {{
    console.log('App loaded successfully');

    // Run tutorial-specific workflow
    runTutorialSteps();
{feature_init}

    // Animate sections into view
    addInteractiveFeatures();
}});

function runTutorialSteps() {{
{step_calls}}}
{step_functions}{feature_helpers}
function addInteractiveFeatures() {{
    const sections = document.querySelectorAll('section');
    sections.forEach((section, index) => {{
        section.style.opacity = '0';
        section.style.transform = 'translateY(20px)';

        setTimeout(() => {{
            section.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            section.style.opacity = '1';
            section.style.transform = 'translateY(0)';
        }}, index * 200);
    }});
}}"""

    def _generate_vanilla_styles_css(self, features: list[str]) -> str:
        """Generate styles.css for vanilla projects"""
        responsive_css = ""
        if "responsive_design" in features:
            responsive_css = '''
@media (max-width: 768px) {
    .app-main {
        padding: 1rem;
    }

    .app-header h1 {
        font-size: 2rem;
    }

    .welcome {
        padding: 1rem;
    }
}'''

        return f'''* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
        'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
        sans-serif;
    line-height: 1.6;
    color: #333;
}}

.app {{
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}}

.app-header {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem;
    text-align: center;
}}

.app-header h1 {{
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}}

.app-main {{
    flex: 1;
    padding: 2rem;
    background-color: #f8f9fa;
}}

.welcome, .tutorial-steps, .features {{
    background: white;
    padding: 2rem;
    border-radius: 12px;
    margin-bottom: 2rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}}

.welcome {{
    text-align: center;
}}

.tech-cards, .feature-cards {{
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    justify-content: center;
    margin-top: 1rem;
}}

.tech-card {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    font-weight: 600;
    font-size: 1rem;
}}

.feature-card {{
    background: #e3f2fd;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    font-weight: 500;
    color: #1565c0;
}}

.tutorial-steps ol {{
    margin-left: 1.5rem;
}}

.tutorial-steps li {{
    margin-bottom: 0.5rem;
}}

.app-footer {{
    background-color: #2c3e50;
    color: white;
    text-align: center;
    padding: 1rem;
}}
{responsive_css}'''

    def _generate_fastapi_main(self, title: str, features: list[str], extracted_info: dict | None = None) -> str:
        """Generate main.py for FastAPI projects, using tutorial context for unique endpoints"""
        extracted_info = extracted_info or {}
        tutorial_steps = extracted_info.get("tutorial_steps", [])
        keywords = extracted_info.get("keywords", [])
        description = extracted_info.get("description", f"Generated by UVAI from YouTube tutorial: {title}")

        auth_imports = ""
        auth_code = ""

        if "authentication" in features:
            auth_imports = '''
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext'''
            auth_code = '''
# Authentication setup
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.post("/auth/login")
async def login():
    """Placeholder login endpoint"""
    return {"message": "Login endpoint - implement authentication logic"}'''

        database_code = ""
        if "database" in features:
            database_code = '''
@app.get("/api/data")
async def get_data():
    """Placeholder data endpoint"""
    return {"data": "Connect to your database here"}'''

        # Build tutorial-specific endpoints from extracted steps
        tutorial_endpoints = ""
        if tutorial_steps:
            steps_repr = "\n".join(
                f'        {{"step": {i + 1}, "description": "{s[:120].replace(chr(34), chr(39))}"}}'
                for i, s in enumerate(tutorial_steps[:10])
            )
            tutorial_endpoints += f'''

@app.get("/api/tutorial/steps")
async def get_tutorial_steps():
    """Return the tutorial steps extracted from the source video"""
    return {{
        "title": "{title}",
        "steps": [
{steps_repr}
        ]
    }}'''

        # Build keyword-based domain endpoints
        domain_endpoints = ""
        for kw in keywords[:3]:
            safe_kw = kw.lower().replace(" ", "_").replace("-", "_")
            safe_kw = "".join(c for c in safe_kw if c.isalnum() or c == "_")
            if safe_kw:
                domain_endpoints += f'''

@app.get("/api/{safe_kw}")
async def get_{safe_kw}():
    """Get {kw} data (extracted from tutorial keywords)"""
    return {{"resource": "{kw}", "status": "ready", "data": []}}'''

        # Fallback generic endpoints when no domain context exists
        if not tutorial_endpoints and not domain_endpoints:
            domain_endpoints = f'''

@app.get("/api/resources")
async def get_resources():
    """List resources for {title}"""
    return [{{"id": 1, "name": "Sample resource for {title}", "status": "active"}}]

@app.post("/api/resources")
async def create_resource(payload: dict):
    """Create a resource for {title}"""
    return {{"created": True, "data": payload}}'''

        steps_comment = (
            "\n".join(f"# Step {i+1}: {s[:100]}" for i, s in enumerate(tutorial_steps[:5]))
            if tutorial_steps
            else "# No tutorial steps extracted from source video"
        )

        return f'''from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional{auth_imports}

# Tutorial context
# Title: {title}
{steps_comment}

app = FastAPI(
    title="{title}",
    description="{description}",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ResourceItem(BaseModel):
    name: str
    description: Optional[str] = None

class ResourceResponse(BaseModel):
    id: int
    name: str
    status: str

@app.get("/")
async def root():
    """Root endpoint"""
    return {{
        "title": "{title}",
        "description": "{description}",
        "endpoints": ["/docs", "/api/tutorial/steps", "/api/health"]
    }}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return {{"status": "healthy", "service": "{title}", "timestamp": datetime.utcnow().isoformat()}}
{tutorial_endpoints}
{domain_endpoints}
{auth_code}
{database_code}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)'''

    def _generate_readme(self, title: str, framework: str, video_analysis: dict) -> str:
        """Generate README.md"""
        video_data = video_analysis.get("video_data", {})
        video_url = video_data.get("video_url", "Unknown")
        extracted_info = video_analysis.get("extracted_info", {})
        technologies = extracted_info.get("technologies", [])
        features = extracted_info.get("features", [])
        tech_section = "\n".join([f"- {tech}" for tech in technologies]) if technologies else "- See source video for details"
        feature_section = "\n".join([f"- {f.replace('_', ' ').title()}" for f in features]) if features else "- See source video for details"

        return f'''# {title}

This project was automatically generated by UVAI from a YouTube video tutorial.

## Source Video
- **URL**: {video_url}
- **Framework**: {framework}
- **Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Watch the original video to follow along with the implementation details.

## Technologies
{tech_section}

## Features
{feature_section}

## Getting Started

### Prerequisites
- Node.js (for React/JavaScript projects)
- Python 3.8+ (for Python projects)

### Installation
```bash
# For React projects
npm install

# For Python projects
pip install -r requirements.txt
```

### Running the Project
```bash
# For React projects
npm start

# For Python projects
uvicorn main:app --reload
```

## Development
This is a starting point generated from video analysis. You can:
- Customize the generated code
- Add more features
- Deploy to your preferred platform
- Integrate with databases and APIs

---
*Generated with ❤️ by UVAI from [{video_url}]({video_url})*'''

    def _sanitize_name(self, name: str) -> str:
        """Sanitize project name for package.json"""
        import re
        # Remove special characters and convert to lowercase
        name = re.sub(r'[^a-zA-Z0-9\s-]', '', name)
        name = re.sub(r'\s+', '-', name.strip().lower())
        # Ensure it starts with a letter
        if name and not name[0].isalpha():
            name = 'uvai-' + name
        return name[:50] if name else 'uvai-project'

    def _create_basic_templates(self):
        """Create basic template files if they don't exist"""
        # This method can be expanded to create template files
        # For now, we generate everything programmatically
        pass

    async def _generate_vue_project(self, project_path: Path, video_analysis: dict, features: list[str]) -> dict[str, Any]:
        """Generate a Vue.js project (placeholder for future implementation)"""
        # For now, fall back to vanilla JS
        return await self._generate_vanilla_js_project(project_path, video_analysis, features)

    async def _generate_mobile_project(self, project_path: Path, video_analysis: dict, technologies: list[str], features: list[str]) -> dict[str, Any]:
        """Generate a mobile project (placeholder for future implementation)"""
        # For now, generate a responsive web app
        return await self._generate_web_project(project_path, video_analysis, technologies, features)

    async def _generate_node_api(self, project_path: Path, video_analysis: dict, features: list[str]) -> dict[str, Any]:
        """Generate a Node.js API project (placeholder for future implementation)"""
        # For now, fall back to Python API
        return await self._generate_python_api(project_path, video_analysis, features)


# Global instance
_code_generator = None

def get_code_generator() -> ProjectCodeGenerator:
    """Get or create global code generator instance"""
    global _code_generator
    if _code_generator is None:
        _code_generator = ProjectCodeGenerator()
    return _code_generator
