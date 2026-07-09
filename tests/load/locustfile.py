from locust import HttpUser, task, between

class EventRelayUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def health_check(self):
        self.client.get("/health")

    @task(3)
    def api_health_check(self):
        self.client.get("/api/v1/health")

    # Add more tasks as needed based on defined endpoints
