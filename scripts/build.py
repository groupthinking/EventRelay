#!/usr/bin/env python3
"""
Production Build System for YouTube AI Extension
Handles building, packaging, and deployment
"""

import os
import sys
import json
import shutil
import zipfile
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExtensionBuilder:
    """Production build system for the YouTube AI extension"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.extension_dir = self.project_root / "extension"
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.api_dir = self.project_root / "api"
        
        # Build configuration
        self.config = {
            "name": "youtube-ai-assistant",
            "version": "1.0.0",
            "description": "AI-powered YouTube tutorial processor",
            "author": "YouTube AI Assistant Team",
            "browsers": ["chrome", "firefox", "safari"],
            "include_source_maps": False,
            "minify": True,
            "optimize_images": True
        }
        
        # Load custom config if exists
        config_file = self.project_root / "build.config.json"
        if config_file.exists():
            with open(config_file) as f:
                custom_config = json.load(f)
                self.config.update(custom_config)
    
    def clean(self):
        """Clean build and dist directories"""
        logger.info("Cleaning build directories...")
        
        for directory in [self.build_dir, self.dist_dir]:
            if directory.exists():
                shutil.rmtree(directory)
                logger.info(f"Removed {directory}")
            directory.mkdir(parents=True, exist_ok=True)
    
    def validate_extension_files(self):
        """Validate that all required extension files exist"""
        required_files = [
            "manifest.json",
            "background.js",
            "content.js",
            "content.css",
            "popup.html",
            "popup.js"
        ]
        
        missing_files = []
        for file in required_files:
            if not (self.extension_dir / file).exists():
                missing_files.append(file)
        
        if missing_files:
            raise FileNotFoundError(f"Missing required extension files: {missing_files}")
        
        logger.info("All required extension files validated")
    
    def build_extension(self, browser: str = "chrome") -> Path:
        """Build extension for specific browser"""
        logger.info(f"Building extension for {browser}...")
        
        # Create browser-specific build directory
        browser_build_dir = self.build_dir / browser
        browser_build_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy extension files
        self.copy_extension_files(browser_build_dir, browser)
        
        # Generate icons if they don't exist
        self.generate_icons(browser_build_dir)
        
        # Modify manifest for browser compatibility
        self.modify_manifest_for_browser(browser_build_dir, browser)
        
        # Minify JavaScript if enabled
        if self.config["minify"]:
            self.minify_javascript(browser_build_dir)
        
        # Optimize CSS
        self.optimize_css(browser_build_dir)
        
        # Validate final build
        self.validate_build(browser_build_dir, browser)
        
        logger.info(f"Extension built successfully for {browser}")
        return browser_build_dir
    
    def copy_extension_files(self, target_dir: Path, browser: str):
        """Copy extension files to build directory"""
        logger.info("Copying extension files...")
        
        # Copy all files from extension directory
        for item in self.extension_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, target_dir)
            elif item.is_dir() and item.name not in ['.git', '__pycache__', 'node_modules']:
                shutil.copytree(item, target_dir / item.name, dirs_exist_ok=True)
        
        # Copy API documentation if exists
        docs_dir = self.project_root / "docs"
        if docs_dir.exists():
            shutil.copytree(docs_dir, target_dir / "docs", dirs_exist_ok=True)
    
    def generate_icons(self, build_dir: Path):
        """Generate extension icons if they don't exist"""
        icons_dir = build_dir / "icons"
        icons_dir.mkdir(exist_ok=True)
        
        # Check if icons already exist
        icon_sizes = [16, 32, 48, 128]
        existing_icons = [icons_dir / f"icon{size}.png" for size in icon_sizes]
        
        if all(icon.exists() for icon in existing_icons):
            logger.info("Icons already exist, skipping generation")
            return
        
        # Generate simple placeholder icons
        logger.info("Generating placeholder icons...")
        self.create_placeholder_icons(icons_dir, icon_sizes)
    
    def create_placeholder_icons(self, icons_dir: Path, sizes: List[int]):
        """Create simple placeholder icons"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            for size in sizes:
                # Create a simple colored square icon
                img = Image.new('RGBA', (size, size), (30, 136, 229, 255))  # Blue background
                draw = ImageDraw.Draw(img)
                
                # Add brain emoji-like symbol
                if size >= 32:
                    font_size = max(size // 3, 12)
                    try:
                        # Try to use a system font
                        font = ImageFont.truetype("Arial.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                    
                    # Draw "AI" text
                    text = "🧠" if size >= 48 else "AI"
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    position = ((size - text_width) // 2, (size - text_height) // 2)
                    draw.text(position, text, fill='white', font=font)
                
                # Save icon
                icon_path = icons_dir / f"icon{size}.png"
                img.save(icon_path, "PNG")
                logger.info(f"Generated icon: {icon_path}")
                
        except ImportError:
            logger.warning("PIL not available, creating dummy icon files")
            # Create empty files as placeholders
            for size in sizes:
                (icons_dir / f"icon{size}.png").touch()
    
    def modify_manifest_for_browser(self, build_dir: Path, browser: str):
        """Modify manifest.json for browser-specific compatibility"""
        manifest_path = build_dir / "manifest.json"
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Browser-specific modifications
        if browser == "firefox":
            # Firefox uses manifest v2
            manifest["manifest_version"] = 2
            
            # Convert service worker to background script
            if "background" in manifest and "service_worker" in manifest["background"]:
                manifest["background"] = {
                    "scripts": [manifest["background"]["service_worker"]],
                    "persistent": False
                }
            
            # Add browser_specific_settings
            manifest["browser_specific_settings"] = {
                "gecko": {
                    "id": f"{self.config['name']}@example.com"
                }
            }
            
            # Update permissions format
            if "host_permissions" in manifest:
                if "permissions" not in manifest:
                    manifest["permissions"] = []
                manifest["permissions"].extend(manifest["host_permissions"])
                del manifest["host_permissions"]
        
        elif browser == "safari":
            # Safari-specific modifications
            manifest["background"] = {
                "page": "background.html",
                "persistent": False
            }
            
            # Create background.html for Safari
            self.create_safari_background_html(build_dir)
        
        # Update version and build info
        manifest["version"] = self.config["version"]
        manifest["description"] = self.config["description"]
        
        # Add build timestamp to description in development
        if not self.config.get("production", False):
            build_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            manifest["description"] += f" (Built: {build_time})"
        
        # Write modified manifest
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Modified manifest for {browser}")
    
    def create_safari_background_html(self, build_dir: Path):
        """Create background.html for Safari compatibility"""
        background_html = build_dir / "background.html"
        
        html_content = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Background Page</title>
</head>
<body>
    <script src="background.js"></script>
</body>
</html>'''
        
        with open(background_html, 'w') as f:
            f.write(html_content)
        
        logger.info("Created background.html for Safari")
    
    def minify_javascript(self, build_dir: Path):
        """Minify JavaScript files"""
        if not self.config["minify"]:
            return
        
        logger.info("Minifying JavaScript files...")
        
        js_files = list(build_dir.glob("*.js"))
        
        for js_file in js_files:
            try:
                # Simple minification (remove comments and extra whitespace)
                with open(js_file, 'r') as f:
                    content = f.read()
                
                # Remove single-line comments
                import re
                content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
                
                # Remove multi-line comments
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
                
                # Remove extra whitespace
                content = re.sub(r'\s+', ' ', content)
                content = content.strip()
                
                with open(js_file, 'w') as f:
                    f.write(content)
                
                logger.info(f"Minified {js_file.name}")
                
            except Exception as e:
                logger.warning(f"Failed to minify {js_file.name}: {e}")
    
    def optimize_css(self, build_dir: Path):
        """Optimize CSS files"""
        logger.info("Optimizing CSS files...")
        
        css_files = list(build_dir.glob("*.css"))
        
        for css_file in css_files:
            try:
                with open(css_file, 'r') as f:
                    content = f.read()
                
                # Remove comments and extra whitespace
                import re
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
                content = re.sub(r'\s+', ' ', content)
                content = content.strip()
                
                with open(css_file, 'w') as f:
                    f.write(content)
                
                logger.info(f"Optimized {css_file.name}")
                
            except Exception as e:
                logger.warning(f"Failed to optimize {css_file.name}: {e}")
    
    def validate_build(self, build_dir: Path, browser: str):
        """Validate the built extension"""
        logger.info(f"Validating {browser} build...")
        
        # Check manifest
        manifest_path = build_dir / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        # Validate required fields
        required_fields = ["name", "version", "manifest_version"]
        for field in required_fields:
            if field not in manifest:
                raise ValueError(f"Missing required manifest field: {field}")
        
        # Check for required files
        required_files = ["background.js", "content.js", "popup.html"]
        for file in required_files:
            if not (build_dir / file).exists():
                raise FileNotFoundError(f"Missing required file: {file}")
        
        # Check icon files
        icons_dir = build_dir / "icons"
        if icons_dir.exists():
            icon_files = list(icons_dir.glob("*.png"))
            if not icon_files:
                logger.warning("No icon files found")
        
        logger.info(f"{browser} build validation passed")
    
    def package_extension(self, browser: str) -> Path:
        """Package extension as zip file"""
        logger.info(f"Packaging {browser} extension...")
        
        browser_build_dir = self.build_dir / browser
        if not browser_build_dir.exists():
            raise FileNotFoundError(f"Build directory not found: {browser_build_dir}")
        
        # Create package filename
        package_name = f"{self.config['name']}-{browser}-v{self.config['version']}.zip"
        package_path = self.dist_dir / package_name
        
        # Create zip package
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in browser_build_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(browser_build_dir)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Package created: {package_path}")
        return package_path
    
    def build_api_service(self):
        """Build the API service component"""
        logger.info("Building API service...")
        
        api_build_dir = self.build_dir / "api"
        api_build_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy API files
        if self.api_dir.exists():
            shutil.copytree(self.api_dir, api_build_dir, dirs_exist_ok=True)
        
        # Create installation instructions using pyproject extras
        (api_build_dir / "INSTALL.md").write_text(
            """Install dependencies using pyproject extras:\n\n"
            "pip install -e .[youtube,ml,postgres]\n"
            "pip install -e .\n"
            """
        )
        
        # Create API deployment files
        self.create_api_deployment_files(api_build_dir)
        
        logger.info("API service built successfully")
    
    def create_api_deployment_files(self, api_dir: Path):
        """Create deployment files for the API service"""
        
        # Create Dockerfile
        dockerfile_content = f'''FROM python:3.11-slim

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -e .[youtube,ml,postgres] && pip install --no-cache-dir -e .

EXPOSE 8005

CMD ["python", "mcp_service.py", "--host", "0.0.0.0", "--port", "8005"]
'''
        
        with open(api_dir / "Dockerfile", 'w') as f:
            f.write(dockerfile_content)
        
        # Create docker-compose.yml
        compose_content = f'''version: '3.8'

services:
  youtube-ai-api:
    build: .
    ports:
      - "8005:8005"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - youtube-ai-api
    restart: unless-stopped
'''
        
        with open(api_dir / "docker-compose.yml", 'w') as f:
            f.write(compose_content)
        
        # Create nginx.conf
        nginx_content = '''events {
    worker_connections 1024;
}

http {
    upstream api {
        server youtube-ai-api:8005;
    }

    server {
        listen 80;
        
        location / {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}'''
        
        with open(api_dir / "nginx.conf", 'w') as f:
            f.write(nginx_content)
        
        logger.info("Created API deployment files")
    
    def build_all(self):
        """Build everything for production"""
        logger.info("Starting full production build...")
        
        # Clean first
        self.clean()
        
        # Validate source files
        self.validate_extension_files()
        
        # Build extensions for all browsers
        built_extensions = []
        for browser in self.config["browsers"]:
            try:
                build_dir = self.build_extension(browser)
                package_path = self.package_extension(browser)
                built_extensions.append({
                    "browser": browser,
                    "build_dir": build_dir,
                    "package": package_path
                })
            except Exception as e:
                logger.error(f"Failed to build {browser} extension: {e}")
                continue
        
        # Build API service
        try:
            self.build_api_service()
        except Exception as e:
            logger.error(f"Failed to build API service: {e}")
        
        # Generate build report
        self.generate_build_report(built_extensions)
        
        logger.info("Full production build completed!")
        return built_extensions
    
    def generate_build_report(self, built_extensions: List[Dict]):
        """Generate build report"""
        report = {
            "build_time": datetime.now().isoformat(),
            "version": self.config["version"],
            "extensions": [],
            "api_service": True
        }
        
        for ext in built_extensions:
            package_size = ext["package"].stat().st_size if ext["package"].exists() else 0
            report["extensions"].append({
                "browser": ext["browser"],
                "package_path": str(ext["package"]),
                "package_size_mb": round(package_size / (1024 * 1024), 2)
            })
        
        report_path = self.dist_dir / "build-report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Build report generated: {report_path}")

def main():
    parser = argparse.ArgumentParser(description="YouTube AI Extension Build System")
    parser.add_argument("--clean", action="store_true", help="Clean build directories")
    parser.add_argument("--browser", choices=["chrome", "firefox", "safari"], help="Build for specific browser")
    parser.add_argument("--api-only", action="store_true", help="Build only the API service")
    parser.add_argument("--package", action="store_true", help="Create distribution packages")
    parser.add_argument("--production", action="store_true", help="Production build (minified)")
    parser.add_argument("--config", help="Path to build config file")
    
    args = parser.parse_args()
    
    # Initialize builder
    builder = ExtensionBuilder()
    
    # Update config for production
    if args.production:
        builder.config.update({
            "minify": True,
            "optimize_images": True,
            "production": True
        })
    
    try:
        if args.clean:
            builder.clean()
            return
        
        if args.api_only:
            builder.build_api_service()
            return
        
        if args.browser:
            # Build single browser
            builder.validate_extension_files()
            build_dir = builder.build_extension(args.browser)
            
            if args.package:
                package_path = builder.package_extension(args.browser)
                logger.info(f"Package created: {package_path}")
        else:
            # Build all
            builder.build_all()
        
        logger.info("Build process completed successfully!")
        
    except Exception as e:
        logger.error(f"Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()