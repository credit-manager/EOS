from locust import HttpUser, between, task


class EOSHealthUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(10)
    def live(self):
        self.client.get("/health/live", name="GET /health/live")

    @task(2)
    def ready(self):
        self.client.get("/health/ready", name="GET /health/ready")
