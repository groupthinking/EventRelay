# UVAI YouTube Extension - Development Usage Guide

## 🚀 Quick Start Commands

### Virtual Environment Activation
```bash
source .venv/bin/activate
```

### Package Import Test
```bash
python -c "import youtube_extension; print('✅ Package working')"
```

### Development Server
```bash
uvicorn youtube_extension.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
pytest tests/
pytest tests/ -v --cov=youtube_extension
```

### Code Quality
```bash
black src/youtube_extension/
isort src/youtube_extension/
ruff check src/youtube_extension/
mypy src/youtube_extension/
```

## 📁 Project Structure

```
youtube_extension/
├── src/youtube_extension/    # Main package
├── frontend/                 # React/TypeScript
├── scripts/                  # Utility scripts
├── config/                   # Configuration files
├── docs/                     # Documentation
├── tests/                    # Test suites
├── infrastructure/           # Docker/K8s configs
├── development/              # Development tools
├── external/                 # External integrations
├── legacy/                   # Legacy projects
└── research/                 # Experimental work
```

## 🔧 Development Workflow

1. **Activate Environment**: `source .venv/bin/activate`
2. **Install Dependencies**: `pip install -e .`
3. **Run Tests**: `pytest tests/`
4. **Start Development**: `uvicorn youtube_extension.main:app --reload`
5. **Check Quality**: `ruff check src/youtube_extension/`

## ⚠️ Important Notes

- Always work within the virtual environment
- Use `pip install -e .` for development installs
- Run tests before committing changes
- Follow the established project structure
- Use the organized directories for new files

## 🐛 Troubleshooting

### Import Issues
```bash
# Test package import
python -c "import youtube_extension"

# Check Python path
python -c "import sys; print(sys.path)"
```

### Virtual Environment Issues
```bash
# Recreate if corrupted
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

**Remember**: This guide is automatically displayed when you activate the virtual environment!
