## 2024-05-31 - Ruff Exception Chaining

**Learning:** When catching and re-raising exceptions in Python, `ruff` rule `B904` requires specifying the cause (e.g., `raise Exception("msg") from e`). This preserves the stack trace for proper debugging.
**Action:** Always use `from e` when re-raising an exception inside an `except Exception as e:` block.
