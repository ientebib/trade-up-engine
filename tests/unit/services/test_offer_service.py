"""
Unit tests for OfferService
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from decimal import Decimal

from app.services.offer_service import OfferService
from app.models import OfferRequest


class TestOfferService:
    """Test suite for OfferService"""
    
    @pytest.fixture
    def offer_service(self):
        """Create OfferService instance for testing"""
        return OfferService()
    
    @pytest.fixture
    def mock_dependencies(self, mock_database, mock_cache_manager):
        """Mock all dependencies for OfferService"""
        with patch('app.services.offer_service.database', mock_database), \
             patch('app.services.offer_service.get_cache_manager', return_value=mock_cache_manager), \
             patch('app.services.offer_service.basic_matcher') as mock_matcher:
            
            # Mock the matcher's find_all_viable method
            mock_matcher.find_all_viable.return_value = {
                "offers": {
                    "Refresh": [{"payment_delta": 0.02, "npv": 25000}],
                    "Upgrade": [{"payment_delta": 0.15, "npv": 30000}],
                    "Max Upgrade": [{"payment_delta": 0.50, "npv": 35000}]
                },
                "total_offers": 3,
                "cars_tested": 100,
                "processing_time": 1.5
            }
            
            yield {
                "database": mock_database,
                "cache_manager": mock_cache_manager,
                "matcher": mock_matcher
            }
    
    def test_generate_offers_for_customer_success(self, offer_service, mock_dependencies, mock_customer):
        """Test successful offer generation for a single customer"""
        # Arrange
        request = OfferRequest(customer_id="TEST123")
        
        # Act
        with patch('app.services.offer_service.database', mock_dependencies["database"]):
            with patch('app.services.offer_service.basic_matcher', mock_dependencies["matcher"]):
                result = offer_service.generate_offers_for_customer(request)
        
        # Assert
        assert result["status"] == "success"
        assert result["customer_id"] == "TEST123"
        assert "offers" in result
        assert result["total_offers"] == 3
        assert mock_dependencies["database"].get_customer_by_id.called
        assert mock_dependencies["matcher"].find_all_viable.called
    
    def test_generate_offers_customer_not_found(self, offer_service, mock_dependencies):
        """Test offer generation when customer doesn't exist"""
        # Arrange
        request = OfferRequest(customer_id="INVALID")
        mock_dependencies["database"].get_customer_by_id.return_value = None
        
        # Act & Assert
        with patch('app.services.offer_service.database', mock_dependencies["database"]):
            with pytest.raises(ValueError, match="Customer not found"):
                offer_service.generate_offers_for_customer(request)
    
    def test_generate_offers_with_custom_fees(self, offer_service, mock_dependencies):
        """Test offer generation with custom fee structure"""
        # Arrange
        request = OfferRequest(customer_id="TEST123")
        custom_fees = {
            "service_fee_pct": 0.03,
            "cxa_pct": 0.02,
            "cac_bonus": 5000
        }
        
        # Act
        with patch('app.services.offer_service.database', mock_dependencies["database"]):
            with patch('app.services.offer_service.basic_matcher', mock_dependencies["matcher"]):
                result = offer_service.generate_offers_for_customer(request, custom_fees)
        
        # Assert
        # Verify custom fees were passed to matcher
        call_args = mock_dependencies["matcher"].find_all_viable.call_args
        assert call_args[1]["custom_fees"] == custom_fees
    
    def test_prepare_offer_response(self, offer_service, mock_customer):
        """Test offer response preparation"""
        # Arrange
        offers = {
            "offers": {
                "Refresh": [{"payment_delta": 0.02, "car_id": "1"}],
                "Upgrade": [],
                "Max Upgrade": []
            },
            "total_offers": 1,
            "processing_time": 0.5
        }
        
        # Act
        result = offer_service.prepare_offer_response(mock_customer, offers)
        
        # Assert
        assert result["customer"]["id"] == "TEST123"
        assert result["customer"]["current_payment"] == 15000.0
        assert result["summary"]["total_offers"] == 1
        assert result["summary"]["refresh_count"] == 1
        assert result["summary"]["upgrade_count"] == 0
        assert result["summary"]["max_upgrade_count"] == 0
    
    def test_bulk_generate_offers(self, offer_service, mock_dependencies):
        """Test bulk offer generation for multiple customers"""
        # Arrange
        customer_ids = ["CUST001", "CUST002", "CUST003"]
        
        # Mock different customers
        mock_dependencies["database"].get_customer_by_id.side_effect = [
            {"customer_id": cid, "current_monthly_payment": 10000} 
            for cid in customer_ids
        ]
        
        # Act
        with patch('app.services.offer_service.database', mock_dependencies["database"]):
            with patch('app.services.offer_service.basic_matcher', mock_dependencies["matcher"]):
                results = offer_service.bulk_generate_offers(customer_ids, max_offers_per_customer=5)
        
        # Assert
        assert len(results) == 3
        assert all(r["status"] == "success" for r in results)
        assert mock_dependencies["database"].get_customer_by_id.call_count == 3
    
    def test_validate_offer_filters(self, offer_service):
        """Test offer filtering validation"""
        # Arrange
        offers = {
            "Refresh": [
                {"payment_delta": 0.02, "npv": 25000},
                {"payment_delta": -0.03, "npv": 20000}
            ],
            "Upgrade": [
                {"payment_delta": 0.30, "npv": 30000}  # Should be filtered out
            ]
        }
        max_payment_increase = 0.25
        
        # Act
        filtered = offer_service.validate_offer_filters(offers, max_payment_increase)
        
        # Assert
        assert len(filtered["Refresh"]) == 2
        assert len(filtered["Upgrade"]) == 0  # Filtered out due to payment increase
    
    def test_enrich_offer_with_metadata(self, offer_service):
        """Test offer enrichment with additional metadata"""
        # Arrange
        offer = {
            "car_id": "VEH123",
            "monthly_payment": 15000,
            "payment_delta": 0.10
        }
        
        # Act
        enriched = offer_service.enrich_offer_with_metadata(offer)
        
        # Assert
        assert "generated_at" in enriched
        assert enriched["payment_increase_pct"] == 10.0
        assert enriched["tier"] == "Upgrade"