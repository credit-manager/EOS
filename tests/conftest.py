"""
EOS Platform - Pytest Fixtures and Configuration

This module provides shared fixtures for all tests:
- Database session management with rollback
- Test client setup
- Authentication tokens
- Tenant isolation context
- Mock services
"""
import os
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Set test environment variables BEFORE importing main
os.environ["DATABASE_URL"] = "postgresql://eos_test:test_password@localhost:5432/eos_test"
os.environ["SECRET_KEY"] = "test_secret_key_for_testing_only_12345678901234567890"
os.environ["ENVIRONMENT"] = "test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine."""
    database_url = os.getenv("DATABASE_URL", "postgresql://eos_test:test_password@localhost:5432/eos_test")
    engine = create_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.
    The session is rolled back after the test to ensure isolation.
    
    Usage:
        def test_something(db_session):
            # Use db_session in your test
            pass
    """
    # Create all tables
    from models import Base
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        # Rollback all changes to ensure test isolation
        session.rollback()
        session.close()
        
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
async def async_db_session(test_engine) -> AsyncGenerator[Session, None]:
    """
    Async version of db_session fixture for async tests.
    
    Usage:
        async def test_something(async_db_session):
            # Use async_db_session in your async test
            pass
    """
    from models import Base
    Base.metadata.create_all(bind=test_engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session")
def test_client():
    """
    Create a test client for making HTTP requests.
    
    Usage:
        def test_api_endpoint(test_client):
            response = test_client.get("/api/v1/some-endpoint")
            assert response.status_code == 200
    """
    from main import app
    
    # Override dependency injection if needed
    # Example: override_get_db = lambda: db_session
    
    with TestClient(app, base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="function")
def auth_token(test_client) -> str:
    """
    Create an authenticated user and return their access token.
    
    Usage:
        def test_authenticated_endpoint(test_client, auth_token):
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = test_client.get("/api/v1/protected", headers=headers)
            assert response.status_code == 200
    """
    # Create test user credentials
    login_data = {
        "email": f"test_{pytest.request.node.nodeid[:50]}@test.com",
        "password": "TestPassword123!"
    }
    
    # Try to login (user might already exist from previous runs)
    response = test_client.post("/api/v1/auth/login", json=login_data)
    
    if response.status_code == 401:
        # User doesn't exist, create it first
        register_data = {
            "email": login_data["email"],
            "password": login_data["password"],
            "full_name": "Test User",
            "company_name": "Test Company"
        }
        register_response = test_client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code in [200, 201], f"Registration failed: {register_response.text}"
        
        # Login again
        response = test_client.post("/api/v1/auth/login", json=login_data)
    
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    
    return data.get("data", {}).get("access_token", data.get("access_token"))


@pytest.fixture(scope="function")
def tenant_context(db_session) -> dict:
    """
    Create a test tenant and return tenant context.
    
    Usage:
        def test_tenant_isolation(tenant_context):
            tenant_id = tenant_context["tenant_id"]
            # Use tenant_id in your test
    """
    from models import Tenant, Company
    
    # Create test tenant
    tenant = Tenant(
        name=f"Test Tenant {pytest.request.node.nodeid[:30]}",
        slug=f"test-tenant-{pytest.request.node.nodeid[:20]}",
        is_active=True
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    
    # Create test company
    company = Company(
        tenant_id=tenant.id,
        name="Test Company",
        tax_id="TEST123456"
    )
    db_session.add(company)
    db_session.commit()
    
    yield {
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
        "company_id": company.id
    }
    
    # Cleanup
    db_session.delete(company)
    db_session.delete(tenant)
    db_session.commit()


@pytest.fixture(scope="function")
def mock_ai_service():
    """
    Mock AI service for testing without calling external APIs.
    
    Usage:
        def test_ai_composer(mock_ai_service):
            # AI calls will use the mock
            pass
    """
    from unittest.mock import MagicMock, AsyncMock
    
    mock = MagicMock()
    mock.analyze_business = AsyncMock(return_value={
        "industry": "trading",
        "modules": ["accounting", "inventory", "sales"],
        "entities": []
    })
    
    return mock


@pytest.fixture(scope="function")
def mock_email_service():
    """
    Mock email service for testing without sending real emails.
    
    Usage:
        def test_email_notification(mock_email_service):
            # Email calls will use the mock
            pass
    """
    from unittest.mock import MagicMock, AsyncMock
    
    mock = MagicMock()
    mock.send_email = AsyncMock(return_value=True)
    mock.send_verification_email = AsyncMock(return_value=True)
    mock.send_password_reset = AsyncMock(return_value=True)
    
    return mock


@pytest.fixture(params=["tourism", "construction", "manufacturing", "trading"])
def industry_type(request):
    """
    Parametrized fixture for testing different industry types.
    
    Usage:
        @pytest.mark.parametrize("industry_type", ["tourism", "construction"])
        def test_industry_pack(industry_type):
            # Test with different industries
            pass
    """
    return request.param


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "user@example.com",
        "password": "SecurePassword123!",
        "full_name": "John Doe",
        "company_name": "Acme Corp",
        "phone": "+1234567890"
    }


@pytest.fixture
def sample_company_data():
    """Sample company data for testing."""
    return {
        "name": "Test Company LLC",
        "tax_id": "TAX123456789",
        "address": "123 Test Street",
        "city": "Test City",
        "country": "EG",
        "phone": "+201234567890"
    }


# Helper functions for common test operations

def create_test_user(db_session, email=None, password="TestPassword123!"):
    """Helper to create a test user."""
    from models import User
    import uuid
    
    if email is None:
        email = f"user_{uuid.uuid4().hex[:8]}@test.com"
    
    user = User(
        email=email,
        full_name="Test User",
        is_active=True
    )
    user.set_password(password)
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user


def cleanup_all_data(db_session):
    """Helper to clean up all test data."""
    # Import all models that need cleanup
    from models import Base
    
    # Drop and recreate all tables
    Base.metadata.drop_all(bind=db_session.get_bind())
    Base.metadata.create_all(bind=db_session.get_bind())


# Markers documentation
"""
Available markers:

@pytest.mark.unit - Fast, isolated unit tests
@pytest.mark.integration - Tests involving multiple components
@pytest.mark.e2e - Full end-to-end tests
@pytest.mark.slow - Tests that take longer than 1 second
@pytest.mark.requires_db - Tests requiring database connection
@pytest.mark.requires_redis - Tests requiring Redis
@pytest.mark.security - Security-related tests
@pytest.mark.tenant_isolation - Multi-tenancy isolation tests
@pytest.mark.industry_tourism - Tourism industry pack tests
@pytest.mark.industry_construction - Construction industry pack tests

Usage:
    @pytest.mark.unit
    def test_something():
        pass
    
    @pytest.mark.slow
    @pytest.mark.requires_db
    def test_slow_db_operation():
        pass

Run specific markers:
    pytest -m unit
    pytest -m "not slow"
    pytest -m "integration and requires_db"
"""
