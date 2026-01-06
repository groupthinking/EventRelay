#!/usr/bin/env python3
"""
Validation script for GitHub Copilot instructions.

This script validates that the .github/copilot-instructions.md file
contains all required sections and content as per best practices.
"""

import sys
from pathlib import Path


def validate_copilot_instructions() -> bool:
    """Validate the Copilot instructions file."""

    # Path to instructions file
    instructions_file = Path(__file__).parent.parent / ".github" / "copilot-instructions.md"

    if not instructions_file.exists():
        print("❌ ERROR: .github/copilot-instructions.md file not found")
        return False

    # Read content
    content = instructions_file.read_text()

    # Required sections
    required_sections = {
        "Project Overview": "## 🎯 Project Overview",
        "Quick Start Guide": "## 🚀 Quick Start Guide",
        "Technology Stack": "## 🔧 Technology Stack",
        "Environment Variables": "## 🔑 Environment Variables",
        "Backend-Frontend Compatibility": "## 🔄 Backend-Frontend Compatibility",
        "Database Connections": "## 💾 Database Connections",
        "Security Best Practices": "## 🔐 Security Best Practices",
        "Common Commands": "## 📦 Common Commands",
        "Development Guidelines": "## 💻 Development Guidelines",
        "Troubleshooting": "## 🐛 Common Troubleshooting",
    }

    # Required keywords/topics
    required_keywords = {
        "environment variable": "Environment variables documentation",
        "database": "Database configuration",
        "backend": "Backend Python/FastAPI references",
        "frontend": "Frontend React/TypeScript references",
        "api key": "API key management",
        "compatibility": "Backend-frontend compatibility",
        "postgresql": "PostgreSQL database",
        "sqlite": "SQLite database",
        "fastapi": "FastAPI framework",
        "react": "React framework",
        "typescript": "TypeScript",
    }

    # Validation results
    all_valid = True

    print("🔍 Validating GitHub Copilot Instructions...\n")

    # Check file size
    line_count = len(content.split('\n'))
    print(f"📄 File size: {line_count} lines")
    if line_count < 200:
        print("   ⚠️  Warning: File seems short, expected 400+ lines")
    else:
        print("   ✓ Good file size")
    print()

    # Check required sections
    print("📋 Checking Required Sections:")
    for section_name, section_marker in required_sections.items():
        if section_marker in content:
            print(f"   ✓ {section_name}")
        else:
            print(f"   ❌ Missing: {section_name}")
            all_valid = False
    print()

    # Check required keywords
    print("🔑 Checking Required Keywords:")
    content_lower = content.lower()
    for keyword, description in required_keywords.items():
        if keyword.lower() in content_lower:
            print(f"   ✓ {keyword}: {description}")
        else:
            print(f"   ❌ Missing: {keyword} - {description}")
            all_valid = False
    print()

    # Check for specific environment variables
    print("🔐 Checking Environment Variable Documentation:")
    env_vars = [
        "YOUTUBE_API_KEY",
        "GEMINI_API_KEY",
        "DATABASE_URL",
        "REACT_APP_API_URL",
    ]
    for var in env_vars:
        if var in content:
            print(f"   ✓ {var}")
        else:
            print(f"   ⚠️  {var} not explicitly documented")
    print()

    # Check for code examples
    print("💻 Checking Code Examples:")
    code_markers = ["```python", "```typescript", "```bash"]
    for marker in code_markers:
        count = content.count(marker)
        if count > 0:
            print(f"   ✓ {marker[3:]} examples: {count}")
        else:
            print(f"   ⚠️  No {marker[3:]} code examples")
    print()

    # Final result
    if all_valid:
        print("✅ SUCCESS: All validations passed!")
        print("\nThe .github/copilot-instructions.md file meets all requirements:")
        print("  • Contains all required sections")
        print("  • Documents environment variables")
        print("  • Covers backend-frontend compatibility")
        print("  • Includes database connection guidance")
        print("  • Provides API key management instructions")
        return True
    else:
        print("❌ FAILED: Some validations failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = validate_copilot_instructions()
    sys.exit(0 if success else 1)
