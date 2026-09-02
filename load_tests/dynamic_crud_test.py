"""
EOS Platform - Dynamic CRUD Operations Load Test
=================================================

Tests read/write operations on dynamically created entities across multiple tenants.

Usage:
    locust -f load_tests/dynamic_crud_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10
"""

from locust import HttpUser, task, between, events
import json
import time
import uuid


class CRUDEntityUser(HttpUser):
    """Simulates users performing CRUD operations on dynamic entities."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize with test data."""
        self.tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"
        self.entity_code = f"test_entity_{uuid.uuid4().hex[:6]}"
        self.created_ids = []
        self._setup_entity()
    
    def _setup_entity(self):
        """Create a test entity to work with."""
        try:
            response = self.client.post(
                "/api/metadata/entities",
                json={
                    "tenant_id": self.tenant_id,
                    "code": self.entity_code,
                    "name_en": f"Test Entity {self.entity_code[-6:]}",
                    "faculty": "testing",
                    "table_mapping": f"tbl_{self.entity_code}",
                    "fields": [
                        {"code": "name", "field_type": "string", "is_required": True},
                        {"code": "description", "field_type": "text", "is_required": False},
                        {"code": "status", "field_type": "string", "is_required": True, 
                         "enum_values": ["active", "inactive", "pending"]},
                        {"code": "amount", "field_type": "decimal", "is_required": False},
                        {"code": "created_date", "field_type": "date", "is_required": False}
                    ]
                },
                headers={"Authorization": "Bearer test_token"},
                name="SETUP /api/metadata/entities"
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Setup complete for tenant {self.tenant_id[-6:]}, entity {self.entity_code[-6:]}")
            else:
                print(f"⚠️  Setup status: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  Setup failed (continuing anyway): {e}")
    
    @task(5)
    def create_record(self):
        """Create a new record in the dynamic entity."""
        record_id = str(uuid.uuid4())
        
        start_time = time.time()
        
        try:
            response = self.client.post(
                f"/api/crud/{self.tenant_id}/{self.entity_code}",
                json={
                    "id": record_id,
                    "name": f"Record {record_id[:8]}",
                    "description": f"Test record created at {time.time()}",
                    "status": "active",
                    "amount": round(float(uuid.uuid4().int % 10000) / 100, 2),
                    "created_date": time.strftime("%Y-%m-%d")
                },
                headers={"Authorization": "Bearer test_token"},
                name="POST /api/crud/[tenant]/[entity]"
            )
            
            if response.status_code in [200, 201]:
                self.created_ids.append(record_id)
                creation_time = time.time() - start_time
                
                events.request.fire(
                    request_type="CUSTOM",
                    name="crud_create_total",
                    response_time=creation_time,
                    response_length=len(response.content),
                    exception=None
                )
            else:
                print(f"⚠️  Create status: {response.status_code}")
                
        except Exception as e:
            events.request.fire(
                request_type="CUSTOM",
                name="crud_create_total",
                response_time=0,
                response_length=0,
                exception=e
            )
    
    @task(8)
    def read_records(self):
        """Read records from the dynamic entity (with pagination)."""
        start_time = time.time()
        
        try:
            response = self.client.get(
                f"/api/crud/{self.tenant_id}/{self.entity_code}?limit=20&offset=0",
                headers={"Authorization": "Bearer test_token"},
                name="GET /api/crud/[tenant]/[entity]"
            )
            
            read_time = time.time() - start_time
            
            if response.status_code == 200:
                events.request.fire(
                    request_type="CUSTOM",
                    name="crud_read_total",
                    response_time=read_time,
                    response_length=len(response.content),
                    exception=None
                )
                
        except Exception as e:
            events.request.fire(
                request_type="CUSTOM",
                name="crud_read_total",
                response_time=0,
                response_length=0,
                exception=e
            )
    
    @task(4)
    def update_record(self):
        """Update an existing record."""
        if not self.created_ids:
            return
        
        record_id = self.created_ids[0]  # Update first created record
        
        start_time = time.time()
        
        try:
            response = self.client.put(
                f"/api/crud/{self.tenant_id}/{self.entity_code}/{record_id}",
                json={
                    "name": f"Updated Record {record_id[:8]}",
                    "description": f"Updated at {time.time()}",
                    "status": "pending" if uuid.uuid4().int % 2 == 0 else "active",
                    "amount": round(float(uuid.uuid4().int % 10000) / 100, 2)
                },
                headers={"Authorization": "Bearer test_token"},
                name="PUT /api/crud/[tenant]/[entity]/[id]"
            )
            
            update_time = time.time() - start_time
            
            if response.status_code in [200, 204]:
                events.request.fire(
                    request_type="CUSTOM",
                    name="crud_update_total",
                    response_time=update_time,
                    response_length=len(response.content),
                    exception=None
                )
                
        except Exception as e:
            events.request.fire(
                request_type="CUSTOM",
                name="crud_update_total",
                response_time=0,
                response_length=0,
                exception=e
            )
    
    @task(2)
    def delete_record(self):
        """Delete a record."""
        if len(self.created_ids) < 2:
            return
        
        record_id = self.created_ids.pop()  # Remove last created record
        
        start_time = time.time()
        
        try:
            response = self.client.delete(
                f"/api/crud/{self.tenant_id}/{self.entity_code}/{record_id}",
                headers={"Authorization": "Bearer test_token"},
                name="DELETE /api/crud/[tenant]/[entity]/[id]"
            )
            
            delete_time = time.time() - start_time
            
            if response.status_code in [200, 204]:
                events.request.fire(
                    request_type="CUSTOM",
                    name="crud_delete_total",
                    response_time=delete_time,
                    response_length=len(response.content),
                    exception=None
                )
                
        except Exception as e:
            events.request.fire(
                request_type="CUSTOM",
                name="crud_delete_total",
                response_time=0,
                response_length=0,
                exception=e
            )
    
    @task(3)
    def search_records(self):
        """Search/filter records."""
        try:
            response = self.client.get(
                f"/api/crud/{self.tenant_id}/{self.entity_code}/search?status=active&limit=10",
                headers={"Authorization": "Bearer test_token"},
                name="GET /api/crud/[tenant]/[entity]/search"
            )
            
            if response.status_code == 200:
                events.request.fire(
                    request_type="CUSTOM",
                    name="crud_search_total",
                    response_time=response.elapsed.total_seconds() * 1000,
                    response_length=len(response.content),
                    exception=None
                )
                
        except Exception as e:
            events.request.fire(
                request_type="CUSTOM",
                name="crud_search_total",
                response_time=0,
                response_length=0,
                exception=e
            )


# Event hooks
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n🚀 Starting EOS Dynamic CRUD Load Test")
    print(f"Target: {environment.host}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    
    print("\n" + "=" * 60)
    print("✅ CRUD Load Test Completed")
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Failed requests: {stats.total.num_failures}")
    print(f"Avg response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Requests/sec: {stats.total.current_rps():.2f}")
    print("=" * 60)
    
    # Print breakdown by operation type
    print("\n📊 Operation Breakdown:")
    for name in ["crud_create_total", "crud_read_total", "crud_update_total", 
                 "crud_delete_total", "crud_search_total"]:
        if name in stats.by_name:
            s = stats.by_name[name]
            print(f"  {name}: {s.num_requests} reqs, " +
                  f"avg={s.avg_response_time:.1f}ms, " +
                  f"failures={s.num_failures}")
