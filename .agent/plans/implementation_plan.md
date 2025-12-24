# Implementation Plan - Robustness Fix & Tool Enhancement

## Problem
The `benchmark_and_commit` tool failed with `FileNotFoundError` when running git commands because it didn't strictly set the working directory. Additionally, the user requested a `list_tools` feature for better discoverability.

## Proposed Changes

### 1. Robustness Fix (Verified)
-   **Goal**: Ensure all git invocations use `cwd=repo_dir`.
-   **Status**: Verified that `profiling_server.py` already contains this logic in:
    -   `git_create_branch`
    -   `git_commit_optimization`
    -   `git_reset_hard`

### 2. New Feature: `list_tools`
-   **Goal**: Add an MCP tool to list all available tools.
-   **Implementation**:
    -   Define `@mcp.tool() def list_tools()`.
    -   Iterate over a hardcoded list of known tool functions (robust method).
    -   Extract `__name__` and `__doc__`.
    -   Return formatted string.

### 3. Execution & Verification
-   **Command**: `python3 profiling_server.py benchmark_and_commit slow_fibonacci 30 0.4`
-   **Audit**: Run `audit_codebase` on the server file itself.

## Verification Plan
-   [x] Run `list_tools` -> Output list.
-   [x] Run `audit_codebase` -> Output candidates (expecting self-detection).
-   [x] Run `benchmark_and_commit` -> Success message and git commit.
