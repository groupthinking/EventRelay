# Deep Research Agent Configuration

## Agent Overview

- **Name**: Deep Research Agent
- **Model**: `deep-research-pro-preview-12-2025`
- **Type**: specialized-intelligence
- **Deployment**: On-Demand / Background
- **Access Level**: `v1beta` Interactions API

## Mission profile

The Deep Research Agent is designed to perform comprehensive, multi-step research tasks that require synthesizing information from vast datasets or complex queries. Unlike standard chat models, this agent operates asynchronously to compile detailed reports.

## Configuration Parameters

### Identity

- **Agent Name**: `DeepSearch-Alpha`
- **Role**: Senior Research Analyst

### Operational Constraints

- **Background Mode**: `true` (Agent runs as a background process to allow for extended computation)
- **Thinking Summaries**: `auto` (Exposes intermediate reasoning steps for transparency)

### Interaction Schema

**Input**:

- `input` (string): Natural language query describing the research topic.
- `agent` (string): Must be set to `deep-research-pro-preview-12-2025`.

**Output**:

- `status`: `completed` | `in_progress` | `failed`
- `outputs`: Array containing the final research report in Markdown format.

## Integration Points

1. **Frontend**: Triggers research via `POST /interactions` with `background=true`.
2. **Notification System**: Listens for `interaction.complete` webhooks or polls status.
3. **Storage**: Saves generated reports to the persistent knowledge base.

## Success Metrics

- **Accuracy**: Validated by cross-referencing citations.
- **Depth**: Measure of unique sub-topics covered.
- **Latency**: Time to completion (expected range: 2-10 minutes).
