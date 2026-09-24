"""Locust performance tests for EOS API.

This module provides distributed load testing using Locust.
It simulates realistic user behavior against the EOS API endpoints.

Usage:
    # Single instance
    locust -f tests/performance/locustfile.py --host=http://localhost:8000

    # Distributed mode (master)
    locust -f tests/performance/locustfile.py --host=http://localhost:8000 --master

    # Distributed mode (worker)
    locust -f tests/performance/locustfile.py --host=http://localhost:8000 --worker --master-host=127.0.0.1

    # Headless mode (no web UI)
    locust -f tests/performance/locustfile.py --host=http://localhost:8000 \\
        --headless -u 100 -r 10 --run-time 5m

Requirements:
    pip install locust
"""

from locust import HttpUser, task, between, events
import logging

logger = logging.getLogger(__name__)


class EOSUser(HttpUser):
    """Simulates a typical EOS user interacting with the API.

    Weight distribution reflects real-world usage patterns:
    - Health checks are frequent (monitoring, load balancers)
    - Dashboard/analytics are heavily used
    - AI copilot and graph queries are moderately used
    - Settings and workflow management are less frequent
    """

    wait_time = between(1, 3)

    def on_start(self):
        """Login and obtain authentication token.

        Attempts registration first, falls back to login if user exists.
        Stores the JWT token for subsequent authenticated requests.
        """
        user_id = self.environment.runner.user_count if self.environment.runner else 0
        email = f"perf-test-{user_id}@test.com"
        password = "TestPass12345!"

        # Try to register a new user
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "tenant_name": f"Perf Test {user_id}",
            },
            name="/api/v1/auth/register",
        )

        if response.status_code == 201:
            self.token = response.json().get("access_token", "")
            logger.debug(f"Registered new user: {email}")
        else:
            # User likely exists, try login
            response = self.client.post(
                "/api/v1/auth/token",
                json={"email": email, "password": password},
                name="/api/v1/auth/token",
            )
            self.token = response.json().get("access_token", "") if response.ok else ""
            logger.debug(f"Login for {email}: {'success' if self.token else 'failed'}")

    def _auth_headers(self):
        """Return authorization headers for authenticated requests."""
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(10)
    def health_check(self):
        """High-frequency health check endpoint.

        Weight: 10 — this is the most common endpoint hit by
        load balancers, monitoring tools, and client health checks.
        """
        self.client.get("/api/v1/health", name="/api/v1/health")

    @task(5)
    def get_dashboard(self):
        """Dashboard analytics data retrieval.

        Weight: 5 — heavily used when users open the main dashboard.
        """
        self.client.get(
            "/api/v1/analytics/home",
            headers=self._auth_headers(),
            name="/api/v1/analytics/home",
        )

    @task(3)
    def list_entities(self):
        """Metadata entity listing.

        Weight: 3 — moderately used for browsing business entities.
        """
        self.client.get(
            "/api/v1/metadata/entities",
            headers=self._auth_headers(),
            name="/api/v1/metadata/entities",
        )

    @task(2)
    def ask_eos(self):
        """AI copilot chat interaction.

        Weight: 2 — used for natural language queries against business data.
        This is typically the slowest endpoint due to AI processing.
        """
        self.client.post(
            "/api/v1/ai/copilot/chat",
            json={"message": "Show me overdue invoices", "context": {}},
            headers=self._auth_headers(),
            name="/api/v1/ai/copilot/chat",
        )

    @task(2)
    def business_graph(self):
        """Business relationship graph retrieval.

        Weight: 2 — used for visualizing entity relationships.
        """
        self.client.get(
            "/api/v1/graph/map",
            headers=self._auth_headers(),
            name="/api/v1/graph/map",
        )

    @task(1)
    def workflow_list(self):
        """Workflow instance listing.

        Weight: 1 — less frequently accessed than main dashboards.
        """
        self.client.get(
            "/api/v1/workflows/instances",
            headers=self._auth_headers(),
            name="/api/v1/workflows/instances",
        )

    @task(1)
    def settings(self):
        """Application settings retrieval.

        Weight: 1 — least frequently accessed endpoint.
        """
        self.client.get(
            "/api/v1/settings",
            headers=self._auth_headers(),
            name="/api/v1/settings",
        )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start information."""
    logger.info("=" * 60)
    logger.info("EOS Performance Test Starting")
    logger.info(f"Host: {environment.host}")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test stop information."""
    logger.info("=" * 60)
    logger.info("EOS Performance Test Completed")
    logger.info("=" * 60)
