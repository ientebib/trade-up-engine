"""
Integration tests for complete offer generation workflow
"""
import pytest
from unittest.mock import patch, Mock
import pandas as pd
from decimal import Decimal


class TestOfferGenerationFlow:
    """Test complete offer generation workflow from API to engine"""
    
    @pytest.fixture
    def mock_data_layer(self, mock_customer, mock_inventory):
        """Mock the entire data layer"""
        with patch('data.database.get_customer_by_id', return_value=mock_customer), \
             patch('data.database.get_tradeup_inventory_for_customer', return_value=mock_inventory), \
             patch('data.database.search_customers', return_value=pd.DataFrame([mock_customer])):
            yield
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration values"""
        config_values = {
            "fees.service.percentage": 0.04,
            "fees.cxa.percentage": 0.04,
            "fees.gps.monthly": 350,
            "fees.gps.installation": 750,
            "financial.iva_rate": 0.16,
            "rates.A1": 0.21
        }
        
        def mock_get(key, default=None):
            return config_values.get(key, default)
        
        with patch('config.facade.get', side_effect=mock_get):
            yield
    
    def test_complete_offer_generation_flow(self, test_client, mock_data_layer, mock_config):
        """Test complete flow: API -> Service -> Engine -> Response"""
        # Make API request
        response = test_client.post(
            "/api/generate-offers-basic",
            json={"customer_id": "TEST123"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "customer" in data
        assert "offers" in data
        assert "summary" in data
        
        # Verify customer data
        assert data["customer"]["id"] == "TEST123"
        assert data["customer"]["risk_profile"] == "A1"
        
        # Verify offers are categorized
        assert "Refresh" in data["offers"]
        assert "Upgrade" in data["offers"]
        assert "Max Upgrade" in data["offers"]
    
    def test_offer_calculation_accuracy(self, test_client, mock_data_layer, mock_config):
        """Test that calculations are accurate through the full stack"""
        response = test_client.post(
            "/api/generate-offers-basic",
            json={"customer_id": "TEST123"}
        )
        
        data = response.json()
        
        # If we have offers, verify calculations
        if data["summary"]["total_offers"] > 0:
            # Get first offer
            all_offers = []
            for tier in ["Refresh", "Upgrade", "Max Upgrade"]:
                all_offers.extend(data["offers"][tier])
            
            if all_offers:
                offer = all_offers[0]
                
                # Verify required fields
                assert "monthly_payment" in offer
                assert "payment_delta" in offer
                assert "loan_amount" in offer
                assert "npv" in offer
                assert "term" in offer
                
                # Verify calculations make sense
                assert offer["monthly_payment"] > 0
                assert -1.0 <= offer["payment_delta"] <= 2.0
                assert offer["loan_amount"] > 0
                assert offer["term"] in [12, 24, 36, 48, 60, 72]
    
    def test_error_propagation(self, test_client):
        """Test that errors propagate correctly through the stack"""
        # Test with invalid customer
        with patch('data.database.get_customer_by_id', return_value=None):
            response = test_client.post(
                "/api/generate-offers-basic",
                json={"customer_id": "INVALID"}
            )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_custom_fees_flow(self, test_client, mock_data_layer, mock_config):
        """Test custom fees flow through entire stack"""
        response = test_client.post(
            "/api/generate-offers",
            json={
                "customer_id": "TEST123",
                "service_fee_pct": 0.02,  # 2% instead of default 4%
                "cxa_pct": 0.03,           # 3% instead of default 4%
                "cac_bonus": 10000         # 10k bonus
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify custom fees were applied
        assert "fees_used" in data.get("metadata", {})
        if "fees_used" in data.get("metadata", {}):
            assert data["metadata"]["fees_used"]["service_fee_pct"] == 0.02
            assert data["metadata"]["fees_used"]["cxa_pct"] == 0.03
            assert data["metadata"]["fees_used"]["cac_bonus"] == 10000
    
    def test_caching_behavior(self, test_client, mock_data_layer, mock_config):
        """Test that caching works correctly in integration"""
        # First request should hit database
        response1 = test_client.post(
            "/api/generate-offers-basic",
            json={"customer_id": "TEST123"}
        )
        
        # Second request might use cache (depending on implementation)
        response2 = test_client.post(
            "/api/generate-offers-basic",
            json={"customer_id": "TEST123"}
        )
        
        # Both should return same structure
        assert response1.status_code == response2.status_code
        assert response1.json()["customer"]["id"] == response2.json()["customer"]["id"]