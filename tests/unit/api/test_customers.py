"""
Unit tests for customer API endpoints
"""
import pytest
from unittest.mock import patch, Mock
from fastapi import status


class TestCustomersAPI:
    """Test suite for customer endpoints"""
    
    @pytest.fixture
    def mock_customer_service(self, mock_customer):
        """Mock the customer service"""
        mock_service = Mock()
        mock_service.get_customer_by_id.return_value = mock_customer
        mock_service.search_customers.return_value = [mock_customer]
        mock_service.get_all_customers.return_value = [mock_customer]
        return mock_service
    
    def test_get_customers_list(self, test_client, mock_customer_service):
        """Test retrieving list of customers"""
        with patch('app.api.customers.CustomerService', return_value=mock_customer_service):
            response = test_client.get("/api/customers?limit=10")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["customer_id"] == "TEST123"
    
    def test_get_customer_by_id_success(self, test_client, mock_customer_service, mock_customer):
        """Test retrieving specific customer by ID"""
        with patch('app.api.customers.CustomerService', return_value=mock_customer_service):
            response = test_client.get("/api/customers/TEST123")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["customer_id"] == "TEST123"
        assert data["risk_profile_name"] == "A1"
    
    def test_get_customer_by_id_not_found(self, test_client, mock_customer_service):
        """Test retrieving non-existent customer"""
        mock_customer_service.get_customer_by_id.side_effect = ValueError("Customer not found")
        
        with patch('app.api.customers.CustomerService', return_value=mock_customer_service):
            response = test_client.get("/api/customers/INVALID")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Customer not found" in response.json()["detail"]
    
    def test_search_customers(self, test_client, mock_customer_service):
        """Test customer search functionality"""
        with patch('app.api.customers.CustomerService', return_value=mock_customer_service):
            response = test_client.post(
                "/api/search/customers",
                json={"query": "John", "limit": 20}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        mock_customer_service.search_customers.assert_called_once_with("John", limit=20)
    
    def test_get_customer_stats(self, test_client, mock_customer_service):
        """Test retrieving customer statistics"""
        mock_customer_service.get_customer_stats.return_value = {
            "loan_to_value": 0.6,
            "risk_score": "Good",
            "payment_to_income_estimate": 0.25
        }
        
        with patch('app.api.customers.CustomerService', return_value=mock_customer_service):
            response = test_client.get("/api/customers/TEST123/stats")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["loan_to_value"] == 0.6
        assert data["risk_score"] == "Good"
    
    def test_validate_customer_eligibility(self, test_client, mock_customer_service):
        """Test customer eligibility check"""
        mock_customer_service.validate_customer_eligibility.return_value = {
            "eligible": True,
            "reasons": []
        }
        
        with patch('app.api.customers.CustomerService', return_value=mock_customer_service):
            response = test_client.get("/api/customers/TEST123/eligibility")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["eligible"] is True
        assert len(data["reasons"]) == 0
    
    def test_get_customers_by_risk_profile(self, test_client, mock_customer_service):
        """Test filtering customers by risk profile"""
        with patch('app.api.customers.CustomerService', return_value=mock_customer_service):
            response = test_client.get("/api/customers/risk-profile/A1")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["risk_profile_name"] == "A1"
    
    def test_export_customers_csv(self, test_client, mock_customer_service):
        """Test exporting customers to CSV"""
        with patch('app.api.customers.CustomerService', return_value=mock_customer_service):
            response = test_client.get("/api/customers/export/csv")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]