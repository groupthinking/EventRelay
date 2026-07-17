from locust import HttpUser, task, between
import json

class EventRelayUser(HttpUser):
    # Simulate users waiting between 1 to 5 seconds between tasks
    wait_time = between(1, 5)

    @task(3)
    def test_health(self):
        """Warmup and health-check monitoring endpoint"""
        self.client.get("/api/v1/health")

    @task(1)
    def test_cloud_ai_status(self):
        """Provider status check"""
        self.client.get("/api/v1/cloud-ai/providers/status")

    @task(2)
    def test_transcript_action(self):
        """Primary workflow: transcript action processing"""
        headers = {"Content-Type": "application/json"}
        payload = {
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "language": "en",
            "transcript_text": "Hello, welcome to this video tutorial. Today we will build an AI service.",
            "video_options": {
                "model_name": "gemini-2.5-flash",
                "temperature": 0.2
            }
        }
        self.client.post("/api/v1/transcript-action", json=payload, headers=headers)

    @task(2)
    def test_process_video(self):
        """Video processing endpoint"""
        headers = {"Content-Type": "application/json"}
        payload = {
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "options": {
                "extract_audio": False,
                "transcribe": True
            }
        }
        self.client.post("/api/v1/process-video", json=payload, headers=headers)
