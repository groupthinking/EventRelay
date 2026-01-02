# ADR-001: Unified Video Pipeline

## Status

Accepted

## Context

The project evolved to have three competing video processing agents:

1.  `EnhancedVideoExtractor` (The Core Engine)
2.  `GeminiVideoMasterAgent` (Standalone benchmarking script)
3.  `MCPEnhancedVideoProcessor` (Metadata/Scoring analyzer)

This "Processor Schism" created architectural entropy, confusion on which agent to use, and duplicated logic.

## Decision

We will **unify** all video processing logic into `EnhancedVideoExtractor` as the **Single Source of Truth**.

1.  **Core Entity**: `EnhancedVideoExtractor` is the only entity authorized to process videos.
2.  **Deprecation**:
    - `GeminiVideoMasterAgent` is deprecated. Its benchmarking logic is considered an optional separate concern.
    - `MCPEnhancedVideoProcessor` is deprecated. Its "World Class Scoring" logic is merged into `EnhancedVideoExtractor` as a post-processing step.
3.  **Coordinator**: The `MCPEcosystemCoordinator` must exclusively use `EnhancedVideoExtractor`.

## Consequences

- **Positive**: Reduced codebase entropy, single maintenance point for schema preservation, simplified MCP routing.
- **Negative**: `EnhancedVideoExtractor` becomes larger (mitigated by modularizing logic).

## Technical Implementation

The `EnhancedVideoExtractor` will now return a `UnifiedVideoResult` containing:

- Summary/Analysis (Gemini/FastVLM)
- World Class Score (Ported Logic)
- Actionable Insights (Ported Logic)
