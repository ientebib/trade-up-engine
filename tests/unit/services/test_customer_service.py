"""
Unit tests for CustomerService
"""
import pytest
from unittest.mock import Mock, patch
import pandas as pd

from app.services.customer_service import CustomerService


class TestCustomerService:
    """Test suite for CustomerService"""
    
    @pytest.fixture
    def customer_service(self):
        """Create CustomerService instance for testing"""
        return CustomerService()
    
    @pytest.fixture  
    def mock_dependencies(self, mock_database, mock_cache_manager):
        """Mock all dependencies for CustomerService"""
        return {
            "database": mock_database,
            "cache_manager": mock_cache_manager
        }
    
    def test_get_customer_by_id_success(self, customer_service, mock_dependencies, mock_customer):
        """Test successful customer retrieval by ID"""
        # Act
        with patch('app.services.customer_service.database', mock_dependencies["database"]):
            result = customer_service.get_customer_by_id("TEST123")
        
        # Assert
        assert result == mock_customer
        mock_dependencies["database"].get_customer_by_id.assert_called_once_with("TEST123")
    
    def test_get_customer_by_id_not_found(self, customer_service, mock_dependencies):
        """Test customer retrieval when not found"""
        # Arrange
        mock_dependencies["database"].get_customer_by_id.return_value = None
        
        # Act & Assert
        with patch('app.services.customer_service.database', mock_dependencies["database"]):
            with pytest.raises(ValueError, match="Customer not found"):
                customer_service.get_customer_by_id("INVALID")
    
    def test_search_customers(self, customer_service, mock_dependencies):
        """Test customer search functionality"""
        # Arrange
        search_results = pd.DataFrame([
            {"customer_id": "CUST001", "risk_profile_name": "A1"},
            {"customer_id": "CUST002", "risk_profile_name": "B2"}
        ])
        mock_dependencies["database"].search_customers.return_value = search_results
        
        # Act
        with patch('app.services.customer_service.database', mock_dependencies["database"]):
            results = customer_service.search_customers("test query", limit=10)
        
        # Assert
        assert len(results) == 2
        assert results[0]["customer_id"] == "CUST001"
        mock_dependencies["database"].search_customers.assert_called_once()
    
    def test_get_customer_stats(self, customer_service, mock_customer):
        """Test customer statistics calculation"""
        # Act
        stats = customer_service.get_customer_stats(mock_customer)
        
        # Assert
        assert stats["loan_to_value"] == 0.6  # 150000 / 250000
        assert stats["payment_to_income_estimate"] > 0
        assert stats["months_remaining_estimate"] > 0
        assert stats["risk_score"] in ["Excellent", "Good", "Fair", "Poor"]
    
    def test_validate_customer_eligibility(self, customer_service, mock_customer):
        """Test customer eligibility validation"""
        # Test eligible customer
        result = customer_service.validate_customer_eligibility(mock_customer)
        assert result["eligible"] is True
        
        # Test ineligible customer (negative equity)
        mock_customer["vehicle_equity"] = -10000
        result = customer_service.validate_customer_eligibility(mock_customer)
        assert result["eligible"] is False
        assert "Negative equity" in result["reasons"][0]
    
    def test_get_customers_by_risk_profile(self, customer_service, mock_dependencies):
        """Test fetching customers by risk profile"""
        # Arrange
        customers_df = pd.DataFrame([
            {"customer_id": "CUST001", "risk_profile_name": "A1"},
            {"customer_id": "CUST002", "risk_profile_name": "A1"},
            {"customer_id": "CUST003", "risk_profile_name": "B2"}
        ])
        mock_dependencies["database"].get_all_customers.return_value = customers_df
        
        # Act
        with patch('app.services.customer_service.database', mock_dependencies["database"]):
            results = customer_service.get_customers_by_risk_profile("A1")
        
        # Assert
        assert len(results) == 2
        assert all(c["risk_profile_name"] == "A1" for c in results)
    
    def test_calculate_customer_score(self, customer_service, mock_customer):
        """Test customer scoring algorithm"""
        # Act
        score = customer_service.calculate_customer_score(mock_customer)
        
        # Assert
        assert 0 <= score <= 100
        assert isinstance(score, (int, float))
    
    def test_get_customer_history(self, customer_service, mock_dependencies):
        """Test retrieving customer payment history"""
        # Arrange
        mock_history = [
            {"month": "2024-01", "payment": 15000, "on_time": True},
            {"month": "2024-02", "payment": 15000, "on_time": True}
        ]
        mock_dependencies["database"].get_payment_history = Mock(return_value=mock_history)
        
        # Act
        with patch('app.services.customer_service.database', mock_dependencies["database"]):
            history = customer_service.get_customer_history("TEST123")
        
        # Assert
        assert len(history) == 2
        assert history[0]["on_time"] is True