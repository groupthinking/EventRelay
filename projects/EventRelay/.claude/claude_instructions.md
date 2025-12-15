# Claude Code Instructions - YouTube Extension

## 🚨 CRITICAL RULES

### Test Data Standards
- **DEFAULT TEST VIDEO ID**: `auJzb1D-fag` (use this for ALL test data)
- **NEVER** use `dQw4w9WgXcQ` (Rick Roll video) in ANY test data
- **PRODUCTION**: Accept any valid YouTube URL or media type
- **TESTING**: Always use `auJzb1D-fag` for consistency

### Code Consistency Rules
1. **Test Assertions Must Match Test Data**
   - If test data uses `auJzb1D-fag`, assertions must expect `auJzb1D-fag`
   - No mismatched video IDs between setup and verification

2. **File Organization**
   - Keep test files in `tests/` directory
   - Keep main code in `src/youtube_extension/`
   - NO loose Python files in project root

3. **Before Making Changes**
   - Read existing test files completely
   - Understand current test data patterns
   - Maintain consistency with existing valid patterns

## 📁 Project Structure Rules
- Main package: `src/youtube_extension/`
- Tests: `tests/`
- Docs: `docs/` (NOT root directory)
- Scripts: `scripts/`

## 🔧 When Debugging Tests
1. Check what video IDs are currently used
2. Ensure ALL instances use the same valid test ID
3. Update both test data AND assertions together
4. Run tests to verify before claiming completion
5. **Use real temporary directories, not mock filesystems**
6. **Clean up test files after completion**
7. **Use tempfile.mkdtemp() and shutil.rmtree() for test isolation**

## ❌ BANNED PRACTICES
- Using `dQw4w9WgXcQ` in any context
- Creating loose Python files in root
- Claiming "job complete" without running tests
- Ignoring existing project structure
- **NEVER use mock/fake filesystems (pyfakefs, etc.)**
- **NEVER create fake test data - use real temporary files**
- **AVOID any .md file bloat or unnecessary documentation generation**

## ✅ REQUIRED VERIFICATION
Before claiming any task complete:
1. Run `pytest tests/` to verify all tests pass
2. Run `python scripts/verify_tests.py` if it exists
3. Confirm no banned video IDs remain in codebase
