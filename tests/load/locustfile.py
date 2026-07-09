from locust import HttpUser, task, between, constant
import json

class EventRelayUser(HttpUser):
    # More realistic wait time for a "thinking" or "observing" user
    wait_time = between(2, 5)

    @task(10)
    def health_warmup(self):
        """GET /health - warmup"""
        self.client.get("/health")

    @task(5)
    def status_check(self):
        """GET /api/v1/capabilities - status check"""
        self.client.get("/api/v1/capabilities")

    @task(2)
    def api_health(self):
        """GET /api/v1/health - detailed health"""
        self.client.get("/api/v1/health")

    # High-impact endpoints (simulated)
    @task(1)
    def process_video_simulation(self):
        """POST /api/v1/process-video - video processing"""
        payload = {
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "options": {"force_refresh": False}
        }
        headers = {"Content-Type": "application/json"}
        # Note: This is an expensive operation; in real load tests we might mock the processing delay
        self.client.post("/api/v1/process-video", json=payload, headers=headers)
