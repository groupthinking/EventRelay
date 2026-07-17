# Bitmovin AI Scene Analysis Validation Run

Run timestamp: 2026-06-10T23:35:48.878319+00:00

## Verdict

Partial validation run completed. EventRelay baseline extraction ran, but Bitmovin AISA uplift could not be measured because no Bitmovin credentials/direct media inputs or AISA JSON outputs were available.

## Bitmovin Readiness

- API key present: False
- Output ID present: False
- Live AISA status: blocked_missing_bitmovin_credentials

## Per-Video Results

### ChatGPT Agent Builder Full Tutorial: Building AI Agents in 2025 for Beginners

- URL: https://www.youtube.com/watch?v=mjkecNwp1X0
- Category: tutorial_demo
- Transcript: 4930 words across 653 segments
- Baseline events/actions/topics: 5 / 3 / 5
- Timestamped baseline events: 0
- Bitmovin AISA: not_run
- Value evaluation: Cannot evaluate Bitmovin uplift without real AISA JSON for the same assets.

Baseline event titles:
- ChatGPT Agent Builder
- Agent Customization
- Creating an Agent
- Set Output Format
- Building Classifier Logic

### How to Build AI Agents Using Make.com (FREE COURSE 2025)

- URL: https://www.youtube.com/watch?v=rfonp8KiIso
- Category: workflow_automation
- Transcript: 8085 words across 1072 segments
- Baseline events/actions/topics: 6 / 4 / 5
- Timestamped baseline events: 0
- Bitmovin AISA: not_run
- Value evaluation: Cannot evaluate Bitmovin uplift without real AISA JSON for the same assets.

Baseline event titles:
- Differences between Automation, AI Workflow, and AI Agents
- Understanding AI Agents
- Real World Example of AI Implementation
- Task Manager Agent
- Create a new Scenario in Make

### 8 Hour AI Agents Course in 30 Minutes (DeepLearning.AI)

- URL: https://www.youtube.com/watch?v=ftBWgcwvEk4
- Category: course_summary
- Transcript: 6840 words across 980 segments
- Baseline events/actions/topics: 4 / 4 / 4
- Timestamped baseline events: 4
- Bitmovin AISA: not_run
- Value evaluation: Cannot evaluate Bitmovin uplift without real AISA JSON for the same assets.

Baseline event titles:
- Structure of the Agentic AI Course
- Definition of Agentic AI Workflows
- Spectrum of Autonomy in Agentic AI
- Building Blocks of Agentic AI

## Interpretation

The current run can judge EventRelay's transcript-first extraction behavior, but it cannot make a defensible yes/no call on Bitmovin uplift until real scene-level metadata exists for the same assets. Do not treat synthetic or model-generated scene descriptions as Bitmovin validation evidence.

## Sources

- EventRelay baseline: local transcript-first OpenAI Responses API extraction, matching the app schema.
- Bitmovin AISA docs: https://developer.bitmovin.com/encoding/docs/getting-started-with-ai-scene-analysis
- Bitmovin AISA API result shape: https://developer.bitmovin.com/encoding/docs/ai-scene-analysis
