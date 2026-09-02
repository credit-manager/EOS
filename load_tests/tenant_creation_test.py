"""
EOS Platform - Multi-Tenant Table Creation Load Test
=====================================================

Tests the builder engine's ability to create dynamic tables for multiple tenants simultaneously.

Usage:
    locust -f load_tests/tenant_creation_test.py --host=http://localhost:8000 --users=50 --spawn-rate=5
"""

import time
import uuid

from locust import HttpUser, between, events, task


class TenantCreationUser(HttpUser):
    """Simulates users creating new tenants with dynamic table generation."""
    
    wait_time = between(2, 5)  # Wait 2-5 seconds between tasks
    
    def on_start(self):
        """Called when a simulated user starts."""
        self.admin_token = None
        self._login_admin()
    
    def _login_admin(self):
        """Login as admin to create tenants."""
        try:
            response = self.client.post("/api/auth/login", json={
                "username": "admin@eos.com",
                "password": "admin123"
            })
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                print("✅ Admin login successful")
        except Exception as e:
            print(f"⚠️  Admin login failed (may need manual setup): {e}")
            self.admin_token = "test_token"
    
    @task(3)
    def create_tenant_with_entities(self):
        """Create a new tenant with default industry pack entities."""
        tenant_id = str(uuid.uuid4())
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Step 1: Create tenant
        start_time = time.time()
        try:
            response = self.client.post(
                "/api/tenants",
                json={
                    "id": tenant_id,
                    "name": f"Test Tenant {tenant_id[:8]}",
                    "industry": "trading",
                    "subscription_plan": "professional"
                },
                headers=headers,
                name="POST /api/tenants"
            )
            
            if response.status_code in [200, 201, 409]:  # 409 = already exists (OK for load test)
                creation_time = time.time() - start_time
                
                # Step 2: Trigger builder engine to create entities
                builder_start = time.time()
                response = self.client.post(
                    f"/api/builder/{tenant_id}/initialize",
                    json={"industry_pack": "trading"},
                    headers=headers,
                    name="POST /api/builder/initialize"
                )
                builder_time = time.time() - builder_start
                
                total_time = time.time() - start_time
                
                # Log metrics
                events.request.fire(
                    request_type="CUSTOM",
                    name="tenant_full_creation",
                    response_time=total_time,
                    response_length=0,
                    exception=None
                )
                
                print(f"✅ Tenant {tenant_id[:8]} created in {total_time:.2f}s " +
                      f"(tenant: {creation_time:.2f}s, builder: {builder_time:.2f}s)")
            else:
                print(f"❌ Tenant creation failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error creating tenant: {e}")
            events.request.fire(
                request_type="CUSTOM",
                name="tenant_full_creation",
                response_time=0,
                response_length=0,
                exception=e
            )
    
    @task(2)
    def list_tenants(self):
        """List all tenants (read operation)."""
        headers = {"Authorization": "Bearer self.admin_token"}
        self.client.get(
            "/api/tenants",
            headers=headers,
            name="GET /api/tenants"
        )
    
    @task(1)
    def get_tenant_stats(self):
        """Get statistics for a random tenant."""
        tenant_id = str(uuid.uuid4())
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        self.client.get(
            f"/api/tenants/{tenant_id}/stats",
            headers=headers,
            name="GET /api/tenants/[id]/stats"
        )


class DynamicEntityUser(HttpUser):
    """Simulates users creating custom entities dynamically."""
    
    wait_time = between(3, 7)
    
    @task(5)
    def create_custom_entity(self):
        """Create a custom entity with dynamic fields."""
        tenant_id = "test-tenant-" + str(uuid.uuid4())[:8]
        entity_name = f"custom_entity_{uuid.uuid4().hex[:8]}"
        
        headers = {"Authorization": "Bearer test_token"}
        
        start_time = time.time()
        
        try:
            # Create entity definition
            response = self.client.post(
                "/api/metadata/entities",
                json={
                    "tenant_id": tenant_id,
                    "code": entity_name,
                    "name_en": f"Custom Entity {entity_name[-6:]}",
                    "faculty": "custom",
                    "table_mapping": f"tbl_{entity_name}",
                    "fields": [
                        {"code": "field1", "field_type": "string", "is_required": True},
                        {"code": "field2", "field_type": "integer", "is_required": False},
                        {"code": "field3", "field_type": "date", "is_required": False},
                        {"code": "amount", "field_type": "decimal", "is_required": True}
                    ]
                },
                headers=headers,
                name="POST /api/metadata/entities"
            )
            
            if response.status_code in [200, 201]:
                creation_time = time.time() - start_time
                print(f"✅ Entity {entity_name[-6:]} created in {creation_time:.2f}s")
            else:
                print(f"⚠️  Entity creation status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error creating entity: {e}")


# Event hooks for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n🚀 Starting EOS Multi-Tenant Load Test")
    print(f"Target: {environment.host}")
    print(f"Users: {environment.runner.user_classes_count}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n" + "=" * 60)
    print("✅ Load Test Completed")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Failed requests: {environment.stats.total.num_failures}")
    print(f"Avg response time: {environment.stats.total.avg_response_time:.2f}ms")
    print("=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log slow requests."""
    if response_time > 2000:  # More than 2 seconds
        print(f"⚠️  SLOW REQUEST: {name} took {response_time:.2f}ms")
