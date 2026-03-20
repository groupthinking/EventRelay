import { defineConfig } from "stainless";

export default defineConfig({
  openapi: "./openapi/eventrelay.openapi.json",
  sdks: [
    { language: "typescript", output: "./sdks/typescript" },
    { language: "python", output: "./sdks/python" },
  ],
  resources: {
    health: {
      methods: {
        basic: { operationId: "health_check_v1_api_v1_health_get" },
        detailed: { operationId: "detailed_health_check_v1_api_v1_health_detailed_get" },
      },
    },
    videos: {
      models: {
        videoProcessingRequest: "#/components/schemas/VideoProcessingRequest",
        videoToSoftwareRequest: "#/components/schemas/VideoToSoftwareRequest",
        transcriptActionRequest: "#/components/schemas/TranscriptActionRequest",
      },
      methods: {
        process: { operationId: "process_video_v1_api_v1_process_video_post" },
        transcriptAction: { operationId: "run_transcript_action_api_v1_transcript_action_post" },
        videoToSoftware: { operationId: "video_to_software_v1_api_v1_video_to_software_post" },
        markdown: { operationId: "process_video_markdown_v1_api_v1_process_video_markdown_post" },
        jobStatus: { operationId: "get_video_job_status_api_v1_videos__job_id__status_get" },
      },
    },
    events: {
      methods: {
        extract: { operationId: "extract_events_api_v1_events_extract_post" },
      },
      models: {
        eventExtractRequest: "#/components/schemas/EventExtractRequest",
      },
    },
  },
});
