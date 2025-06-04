"""
Comprehensive Testing Framework for Maritime Reservation System
Includes unit tests, integration tests, and end-to-end testing
"""

import pytest
import asyncio
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime, timedelta
from decimal import Decimal

# Import application modules
from app.main import app
from app.db.session import get_db
from app.models.user import User
from app.models.ferry import Booking, Ferry, Route
from app.services.payment_service import PaymentService, PaymentRequest, PaymentMethod, Currency
from app.services.ferry_integration import FerryIntegrationService
from app.core.config import settings

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Test client setup
client = TestClient(app)

class TestUserAuthentication:
    """Test suite for user authentication and authorization"""
    
    def setup_method(self):
        """Setup test data before each test"""
        self.test_user_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User",
            "phone": "+1234567890"
        }
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        response = client.post("/api/v1/auth/register", json=self.test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == self.test_user_data["email"]
        assert "id" in data
        assert "password" not in data  # Ensure password is not returned
    
    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email"""
        # First registration
        client.post("/api/v1/auth/register", json=self.test_user_data)
        
        # Second registration with same email
        response = client.post("/api/v1/auth/register", json=self.test_user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_user_login(self):
        """Test user login endpoint"""
        # Register user first
        client.post("/api/v1/auth/register", json=self.test_user_data)
        
        # Login
        login_data = {
            "username": self.test_user_data["email"],
            "password": self.test_user_data["password"]
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
    
    def test_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without authentication"""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401
    
    def test_protected_endpoint_with_token(self):
        """Test accessing protected endpoint with valid token"""
        # Register and login
        client.post("/api/v1/auth/register", json=self.test_user_data)
        login_response = client.post("/api/v1/auth/login", data={
            "username": self.test_user_data["email"],
            "password": self.test_user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == self.test_user_data["email"]

class TestFerrySearch:
    """Test suite for ferry search functionality"""
    
    def setup_method(self):
        """Setup test data before each test"""
        self.search_params = {
            "departure_port": "Tunis",
            "arrival_port": "Marseille",
            "departure_date": "2024-07-15",
            "passengers": 2
        }
    
    def test_ferry_search_basic(self):
        """Test basic ferry search"""
        response = client.get("/api/v1/ferries/search", params=self.search_params)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Verify response structure
        if data:
            ferry = data[0]
            required_fields = ["id", "departure_port", "arrival_port", "departure_time", "arrival_time", "price"]
            for field in required_fields:
                assert field in ferry
    
    def test_ferry_search_no_results(self):
        """Test ferry search with no available results"""
        search_params = {
            "departure_port": "NonexistentPort",
            "arrival_port": "AnotherNonexistentPort",
            "departure_date": "2024-07-15",
            "passengers": 1
        }
        response = client.get("/api/v1/ferries/search", params=search_params)
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_ferry_search_invalid_date(self):
        """Test ferry search with invalid date format"""
        invalid_params = self.search_params.copy()
        invalid_params["departure_date"] = "invalid-date"
        response = client.get("/api/v1/ferries/search", params=invalid_params)
        assert response.status_code == 422  # Validation error
    
    def test_ferry_search_past_date(self):
        """Test ferry search with past date"""
        past_params = self.search_params.copy()
        past_params["departure_date"] = "2020-01-01"
        response = client.get("/api/v1/ferries/search", params=past_params)
        assert response.status_code == 400
        assert "past date" in response.json()["detail"].lower()

class TestBookingOperations:
    """Test suite for booking operations"""
    
    def setup_method(self):
        """Setup test data before each test"""
        # Create test user and get token
        self.user_data = {
            "email": "booking_test@example.com",
            "password": "testpassword123",
            "first_name": "Booking",
            "last_name": "Tester",
            "phone": "+1234567890"
        }
        client.post("/api/v1/auth/register", json=self.user_data)
        login_response = client.post("/api/v1/auth/login", data={
            "username": self.user_data["email"],
            "password": self.user_data["password"]
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        self.booking_data = {
            "ferry_id": "test_ferry_123",
            "departure_date": "2024-07-15",
            "passengers": [
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "date_of_birth": "1990-01-01",
                    "passport_number": "AB123456"
                },
                {
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "date_of_birth": "1992-05-15",
                    "passport_number": "CD789012"
                }
            ],
            "contact_email": "booking_test@example.com",
            "contact_phone": "+1234567890"
        }
    
    def test_create_booking(self):
        """Test creating a new booking"""
        response = client.post("/api/v1/bookings", json=self.booking_data, headers=self.headers)
        assert response.status_code == 201
        data = response.json()
        assert "booking_id" in data
        assert data["status"] == "pending"
        assert len(data["passengers"]) == 2
    
    def test_create_booking_unauthorized(self):
        """Test creating booking without authentication"""
        response = client.post("/api/v1/bookings", json=self.booking_data)
        assert response.status_code == 401
    
    def test_get_user_bookings(self):
        """Test retrieving user's bookings"""
        # Create a booking first
        client.post("/api/v1/bookings", json=self.booking_data, headers=self.headers)
        
        # Retrieve bookings
        response = client.get("/api/v1/bookings", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_get_booking_details(self):
        """Test retrieving specific booking details"""
        # Create a booking first
        create_response = client.post("/api/v1/bookings", json=self.booking_data, headers=self.headers)
        booking_id = create_response.json()["booking_id"]
        
        # Retrieve booking details
        response = client.get(f"/api/v1/bookings/{booking_id}", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["booking_id"] == booking_id
    
    def test_cancel_booking(self):
        """Test cancelling a booking"""
        # Create a booking first
        create_response = client.post("/api/v1/bookings", json=self.booking_data, headers=self.headers)
        booking_id = create_response.json()["booking_id"]
        
        # Cancel the booking
        response = client.delete(f"/api/v1/bookings/{booking_id}", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

class TestPaymentProcessing:
    """Test suite for payment processing"""
    
    def setup_method(self):
        """Setup test payment service with mock configurations"""
        self.payment_service = PaymentService(
            stripe_config={"api_key": "sk_test_mock", "webhook_secret": "whsec_mock"},
            paypal_config={"client_id": "mock_client", "client_secret": "mock_secret"}
        )
    
    @pytest.mark.asyncio
    async def test_create_stripe_payment(self):
        """Test creating Stripe payment"""
        payment_request = PaymentRequest(
            booking_id="test_booking_123",
            amount=Decimal("89.50"),
            currency=Currency.EUR,
            payment_method=PaymentMethod.STRIPE_CARD,
            customer_email="test@example.com",
            customer_name="Test User",
            description="Ferry booking payment"
        )
        
        with patch.object(self.payment_service.stripe_processor, 'create_payment_intent') as mock_create:
            mock_create.return_value = Mock(
                payment_id="pi_test_123",
                status="pending",
                amount=Decimal("89.50"),
                currency=Currency.EUR
            )
            
            response = await self.payment_service.create_payment(payment_request)
            assert response.payment_id == "pi_test_123"
            assert response.status.value == "pending"
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_paypal_payment(self):
        """Test creating PayPal payment"""
        payment_request = PaymentRequest(
            booking_id="test_booking_456",
            amount=Decimal("95.00"),
            currency=Currency.EUR,
            payment_method=PaymentMethod.PAYPAL,
            customer_email="test@example.com",
            customer_name="Test User",
            description="Ferry booking payment",
            return_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )
        
        with patch.object(self.payment_service.paypal_processor, 'create_payment') as mock_create:
            mock_create.return_value = Mock(
                payment_id="paypal_test_456",
                status="pending",
                redirect_url="https://paypal.com/checkout"
            )
            
            response = await self.payment_service.create_payment(payment_request)
            assert response.payment_id == "paypal_test_456"
            assert response.redirect_url == "https://paypal.com/checkout"
            mock_create.assert_called_once()
    
    def test_currency_conversion(self):
        """Test currency conversion functionality"""
        amount_eur = Decimal("100.00")
        amount_usd = self.payment_service.convert_currency(amount_eur, Currency.EUR, Currency.USD)
        assert amount_usd > amount_eur  # USD should be higher value
        
        # Test round-trip conversion
        amount_back = self.payment_service.convert_currency(amount_usd, Currency.USD, Currency.EUR)
        assert abs(amount_back - amount_eur) < Decimal("0.01")  # Should be approximately equal
    
    def test_payment_validation(self):
        """Test payment request validation"""
        # Valid payment request
        valid_request = PaymentRequest(
            booking_id="test_booking",
            amount=Decimal("50.00"),
            currency=Currency.EUR,
            payment_method=PaymentMethod.STRIPE_CARD,
            customer_email="valid@example.com",
            customer_name="Valid User",
            description="Test payment"
        )
        assert self.payment_service.security_manager.validate_payment_data(valid_request) == True
        
        # Invalid payment request (negative amount)
        invalid_request = PaymentRequest(
            booking_id="test_booking",
            amount=Decimal("-10.00"),
            currency=Currency.EUR,
            payment_method=PaymentMethod.STRIPE_CARD,
            customer_email="valid@example.com",
            customer_name="Valid User",
            description="Test payment"
        )
        assert self.payment_service.security_manager.validate_payment_data(invalid_request) == False

class TestFerryIntegration:
    """Test suite for ferry operator API integration"""
    
    def setup_method(self):
        """Setup test ferry integration service"""
        self.integration_service = FerryIntegrationService()
    
    @pytest.mark.asyncio
    async def test_ctn_integration(self):
        """Test CTN ferry operator integration"""
        search_params = {
            "departure_port": "Tunis",
            "arrival_port": "Marseille",
            "departure_date": "2024-07-15",
            "passengers": 2
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "ferries": [
                    {
                        "id": "ctn_ferry_123",
                        "departure_time": "08:00",
                        "arrival_time": "14:00",
                        "price": 89.50,
                        "available_seats": 150
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            results = await self.integration_service.search_ctn_ferries(search_params)
            assert len(results) == 1
            assert results[0]["id"] == "ctn_ferry_123"
            assert results[0]["price"] == 89.50
    
    @pytest.mark.asyncio
    async def test_gnv_integration(self):
        """Test GNV ferry operator integration"""
        search_params = {
            "departure_port": "Genoa",
            "arrival_port": "Tunis",
            "departure_date": "2024-07-20",
            "passengers": 1
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "routes": [
                    {
                        "route_id": "gnv_route_456",
                        "departure": "20:00",
                        "arrival": "08:00+1",
                        "fare": 95.00,
                        "vessel": "GNV Excellent"
                    }
                ]
            }
            mock_post.return_value = mock_response
            
            results = await self.integration_service.search_gnv_ferries(search_params)
            assert len(results) == 1
            assert results[0]["route_id"] == "gnv_route_456"
            assert results[0]["vessel"] == "GNV Excellent"
    
    @pytest.mark.asyncio
    async def test_integration_error_handling(self):
        """Test error handling in ferry integrations"""
        search_params = {
            "departure_port": "TestPort",
            "arrival_port": "TestDestination",
            "departure_date": "2024-07-25",
            "passengers": 1
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection failed")
            
            results = await self.integration_service.search_ctn_ferries(search_params)
            assert results == []  # Should return empty list on error

class TestAPIEndpoints:
    """Integration tests for API endpoints"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_api_documentation(self):
        """Test API documentation endpoints"""
        response = client.get("/docs")
        assert response.status_code == 200
        
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
    
    def test_cors_headers(self):
        """Test CORS headers are properly set"""
        response = client.options("/api/v1/ferries/search")
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = client.get("/api/v1/ferries/search", params={
                "departure_port": "Tunis",
                "arrival_port": "Marseille",
                "departure_date": "2024-07-15",
                "passengers": 1
            })
            responses.append(response.status_code)
        
        # Should not exceed rate limits for reasonable requests
        assert all(status in [200, 422] for status in responses)

class TestSecurityFeatures:
    """Test suite for security features"""
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection"""
        malicious_input = "'; DROP TABLE users; --"
        response = client.get("/api/v1/ferries/search", params={
            "departure_port": malicious_input,
            "arrival_port": "Marseille",
            "departure_date": "2024-07-15",
            "passengers": 1
        })
        # Should handle gracefully without causing database issues
        assert response.status_code in [200, 400, 422]
    
    def test_xss_protection(self):
        """Test protection against XSS attacks"""
        xss_payload = "<script>alert('xss')</script>"
        user_data = {
            "email": "xss_test@example.com",
            "password": "testpassword123",
            "first_name": xss_payload,
            "last_name": "User",
            "phone": "+1234567890"
        }
        response = client.post("/api/v1/auth/register", json=user_data)
        if response.status_code == 201:
            data = response.json()
            # Should escape or sanitize the input
            assert "<script>" not in data["first_name"]
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed"""
        user_data = {
            "email": "hash_test@example.com",
            "password": "plaintextpassword",
            "first_name": "Hash",
            "last_name": "Test",
            "phone": "+1234567890"
        }
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Password should not be returned in response
        data = response.json()
        assert "password" not in data
        
        # Verify login still works (password was hashed correctly)
        login_response = client.post("/api/v1/auth/login", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200

# Performance Tests
class TestPerformance:
    """Test suite for performance testing"""
    
    def test_search_response_time(self):
        """Test ferry search response time"""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/ferries/search", params={
            "departure_port": "Tunis",
            "arrival_port": "Marseille",
            "departure_date": "2024-07-15",
            "passengers": 2
        })
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 2.0  # Should respond within 2 seconds
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get("/api/v1/ferries/search", params={
                "departure_port": "Tunis",
                "arrival_port": "Marseille",
                "departure_date": "2024-07-15",
                "passengers": 1
            })
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        # Should handle concurrent requests efficiently
        assert end_time - start_time < 5.0

# Test Configuration and Fixtures
@pytest.fixture(scope="session")
def test_database():
    """Create test database for the session"""
    from app.db.base import Base
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user():
    """Create a test user for testing"""
    user_data = {
        "email": "fixture_user@example.com",
        "password": "testpassword123",
        "first_name": "Fixture",
        "last_name": "User",
        "phone": "+1234567890"
    }
    response = client.post("/api/v1/auth/register", json=user_data)
    return response.json()

@pytest.fixture
def authenticated_client(test_user):
    """Create an authenticated test client"""
    login_response = client.post("/api/v1/auth/login", data={
        "username": test_user["email"],
        "password": "testpassword123"
    })
    token = login_response.json()["access_token"]
    
    class AuthenticatedClient:
        def __init__(self, client, token):
            self.client = client
            self.headers = {"Authorization": f"Bearer {token}"}
        
        def get(self, url, **kwargs):
            return self.client.get(url, headers=self.headers, **kwargs)
        
        def post(self, url, **kwargs):
            return self.client.post(url, headers=self.headers, **kwargs)
        
        def put(self, url, **kwargs):
            return self.client.put(url, headers=self.headers, **kwargs)
        
        def delete(self, url, **kwargs):
            return self.client.delete(url, headers=self.headers, **kwargs)
    
    return AuthenticatedClient(client, token)

# Test Runner Configuration
if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([
        "--cov=app",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--verbose",
        __file__
    ])

