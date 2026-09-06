from __future__ import annotations

from locust import HttpUser, between, task


class EOSHealthUser(HttpUser):
    """Deterministic baseline load profile for platform availability SLOs."""

    wait_time = between(0.1, 0.5)

    @task(8)
    def live(self):
        self.client.get("/health/live", name="GET /health/live")

    @task(3)
    def ready(self):
        self.client.get("/health/ready", name="GET /health/ready")

    @task(2)
    def system_info(self):
        self.client.get("/api/v1/system/info", name="GET /api/v1/system/info")

    @task(1)
    def root(self):
        self.client.get("/", name="GET /")
