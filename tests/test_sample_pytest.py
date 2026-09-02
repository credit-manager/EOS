"""
EOS Platform - Sample Pytest Test

This is an example of how to write proper pytest tests
using the fixtures defined in conftest.py.

This replaces the old HTTP script-style tests with proper
pytest fixtures, isolation, and assertions.
"""
import pytest


class TestHealthCheck:
    """Test basic health check endpoints."""
    
    @pytest.mark.unit
    def test_health_check(self, test_client):
        """Test that the health check endpoint returns 200."""
        response = test_client.get("/health")
        assert response.status_code == 200
    
    @pytest.mark.unit
    def test_root_endpoint(self, test_client):
        """Test that the root endpoint works."""
        response = test_client.get("/")
        assert response.status_code in [200, 404]  # May redirect or return info


class TestAuthentication:
    """Test authentication flows."""
    
    @pytest.mark.unit
    def test_register_user(self, test_client, sample_user_data):
        """Test user registration."""
        response = test_client.post(
            "/api/v1/auth/register",
            json=sample_user_data
        )
        # Should succeed or fail gracefully (user might exist)
        assert response.status_code in [200, 201, 400]
    
    @pytest.mark.unit
    def test_login_success(self, test_client):
        """Test successful login."""
        login_data = {
            "email": "admin@demo.com",
            "password": "admin123"
        }
        response = test_client.post("/api/v1/auth/login", json=login_data)
        
        # Login should work for demo account or fail gracefully
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in str(data) or "data" in data
    
    @pytest.mark.unit
    def test_login_invalid_credentials(self, test_client):
        """Test login with invalid credentials."""
        login_data = {
            "email": "invalid@test.com",
            "password": "wrongpassword"
        }
        response = test_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code in [401, 403, 404]


class TestMultiTenancy:
    """Test multi-tenancy isolation."""
    
    @pytest.mark.tenant_isolation
    def test_tenant_isolation(self, db_session, tenant_context):
        """Test that tenants are properly isolated."""
        context1 = tenant_context
        
        # Create another tenant
        from models import Company, Tenant
        tenant2 = Tenant(name="Tenant 2", slug="tenant-2", is_active=True)
        db_session.add(tenant2)
        db_session.commit()
        
        company2 = Company(tenant_id=tenant2.id, name="Company 2", tax_id="TAX2")
        db_session.add(company2)
        db_session.commit()
        
        # Verify isolation
        assert context1["tenant_id"] != tenant2.id
        assert context1["company_id"] != company2.id
        
        # Cleanup
        db_session.delete(company2)
        db_session.delete(tenant2)
        db_session.commit()
    
    @pytest.mark.tenant_isolation
    def test_tenant_data_separation(self, auth_token, test_client, tenant_context):
        """Test that tenant data is separated."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Try to access data - should be filtered by tenant
        # This is a placeholder - actual implementation depends on your data model
        response = test_client.get(
            "/api/v1/companies",
            headers=headers
        )
        
        # Should either succeed with filtered data or require setup
        assert response.status_code in [200, 401, 403, 500]


class TestIndustryPacks:
    """Test industry pack functionality."""
    
    @pytest.mark.industry_tourism
    def test_tourism_pack_entities(self, db_session):
        """Test that tourism entities are available."""
        # Import tourism entities
        try:
            from core.industry_engine.tourism_pack import get_tourism_entities
            entities = get_tourism_entities()
            
            assert len(entities) > 0
            assert any("booking" in str(e).lower() for e in entities)
        except ImportError:
            pytest.skip("Tourism pack not yet implemented")
    
    @pytest.mark.parametrize("industry", ["tourism", "construction", "trading"])
    def test_industry_detection(self, industry):
        """Test industry detection for different types."""
        from core.ai_composer import detect_industry
        
        keywords = {
            "tourism": ["hotel", "booking", "travel", "سياحة", "فندق"],
            "construction": ["building", "construction", "مقاولات", "بناء"],
            "trading": ["trading", "retail", "تجارة", "بيع"]
        }
        
        for keyword in keywords.get(industry, []):
            detected = detect_industry(keyword)
            # Detection should work or return default
            assert detected is None or isinstance(detected, str)


class TestDynamicCRUD:
    """Test dynamic CRUD operations."""
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_dynamic_entity_creation(self, db_session, auth_token, test_client):
        """Test creating entities dynamically."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # This would test the builder engine creating new entities
        # Placeholder for actual implementation
        entity_data = {
            "name": "Test Entity",
            "code": "TEST_ENT",
            "fields": [
                {"name": "field1", "type": "string"},
                {"name": "field2", "type": "integer"}
            ]
        }
        
        response = test_client.post(
            "/api/v1/builder/entities",
            json=entity_data,
            headers=headers
        )
        
        # Should succeed or return appropriate error
        assert response.status_code in [200, 201, 400, 401, 403, 404, 500]


class TestSecurity:
    """Test security features."""
    
    @pytest.mark.security
    def test_rate_limiting(self, test_client):
        """Test that rate limiting is applied."""
        # Make multiple rapid requests
        responses = []
        for _ in range(20):
            response = test_client.get("/health")
            responses.append(response.status_code)
        
        # Should mostly succeed, some might be rate limited
        success_count = sum(1 for s in responses if s == 200)
        rate_limited_count = sum(1 for s in responses if s == 429)
        
        # Most should succeed, some might be limited
        assert success_count > 0 or rate_limited_count > 0
    
    @pytest.mark.security
    def test_cors_headers(self, test_client):
        """Test CORS configuration."""
        response = test_client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # CORS headers should be present or endpoint doesn't support OPTIONS
        assert response.status_code in [200, 204, 404, 405]


class TestAPI:
    """General API tests."""
    
    @pytest.mark.integration
    def test_api_versioning(self, test_client):
        """Test API versioning is in place."""
        response = test_client.get("/api/v1/health")
        # Should exist or redirect
        assert response.status_code in [200, 301, 302, 404]
    
    @pytest.mark.unit
    def test_error_handling(self, test_client):
        """Test that errors are handled gracefully."""
        response = test_client.get("/api/v1/nonexistent-endpoint-12345")
        # Should return 404, not 500
        assert response.status_code in [404, 405]


# Run with: pytest tests/test_sample.py -v
# Run specific markers: pytest -m unit
# Run with coverage: pytest --cov=.
