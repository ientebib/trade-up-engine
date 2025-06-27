"""
Unit tests for offer generation API endpoints
"""
import pytest
from unittest.mock import patch, Mock
from fastapi import status


class TestOffersAPI:
    """Test suite for offer generation endpoints"""
    
    @pytest.fixture
    def mock_offer_service(self):
        """Mock the offer service"""
        mock_service = Mock()
        mock_service.generate_offers_for_customer.return_value = {
            "status": "success",
            "customer_id": "TEST123",
            "offers": {
                "Refresh": [{"payment_delta": 0.02}],
                "Upgrade": [],
                "Max Upgrade": []
            },
            "total_offers": 1
        }
        return mock_service
    
    def test_generate_offers_basic_success(self, test_client, mock_offer_service):
        """Test successful basic offer generation"""
        with patch('app.api.offers.OfferService', return_value=mock_offer_service):
            response = test_client.post(
                "/api/generate-offers-basic",
                json={"customer_id": "TEST123"}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["customer_id"] == "TEST123"
        assert data["total_offers"] == 1
    
    def test_generate_offers_invalid_customer(self, test_client, mock_offer_service):
        """Test offer generation with invalid customer ID"""
        mock_offer_service.generate_offers_for_customer.side_effect = ValueError("Customer not found")
        
        with patch('app.api.offers.OfferService', return_value=mock_offer_service):
            response = test_client.post(
                "/api/generate-offers-basic",
                json={"customer_id": "INVALID"}
            )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Customer not found" in response.json()["detail"]
    
    def test_generate_offers_with_custom_fees(self, test_client, mock_offer_service):
        """Test offer generation with custom fee parameters"""
        with patch('app.api.offers.OfferService', return_value=mock_offer_service):
            response = test_client.post(
                "/api/generate-offers",
                json={
                    "customer_id": "TEST123",
                    "service_fee_pct": 0.03,
                    "cxa_pct": 0.02,
                    "cac_bonus": 5000
                }
            )
        
        assert response.status_code == status.HTTP_200_OK
        # Verify custom fees were passed to service
        call_args = mock_offer_service.generate_offers_for_customer.call_args
        assert call_args[1]["custom_fees"]["service_fee_pct"] == 0.03
    
    def test_generate_offers_missing_customer_id(self, test_client):
        """Test offer generation without customer ID"""
        response = test_client.post(
            "/api/generate-offers-basic",
            json={}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "customer_id" in response.json()["detail"][0]["loc"]
    
    def test_bulk_generate_offers_success(self, test_client, mock_offer_service):
        """Test bulk offer generation for multiple customers"""
        mock_offer_service.bulk_generate_offers.return_value = [
            {"customer_id": "CUST001", "status": "success", "total_offers": 5},
            {"customer_id": "CUST002", "status": "success", "total_offers": 3}
        ]
        
        with patch('app.api.offers.OfferService', return_value=mock_offer_service):
            response = test_client.post(
                "/api/bulk-generate-offers",
                json={
                    "customer_ids": ["CUST001", "CUST002"],
                    "max_offers_per_customer": 5
                }
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_customers"] == 2
        assert data["successful"] == 2
        assert len(data["results"]) == 2
    
    def test_bulk_generate_offers_partial_failure(self, test_client, mock_offer_service):
        """Test bulk generation with some failures"""
        mock_offer_service.bulk_generate_offers.return_value = [
            {"customer_id": "CUST001", "status": "success", "total_offers": 5},
            {"customer_id": "CUST002", "status": "error", "message": "Customer not found"}
        ]
        
        with patch('app.api.offers.OfferService', return_value=mock_offer_service):
            response = test_client.post(
                "/api/bulk-generate-offers",
                json={"customer_ids": ["CUST001", "CUST002"]}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["successful"] == 1
        assert data["failed"] == 1
    
    def test_get_offer_details(self, test_client, mock_offer_service):
        """Test retrieving specific offer details"""
        mock_offer_service.get_offer_details.return_value = {
            "offer_id": "OFF123",
            "customer_id": "TEST123",
            "car_id": "VEH456",
            "monthly_payment": 16500,
            "npv": 25000
        }
        
        with patch('app.api.offers.OfferService', return_value=mock_offer_service):
            response = test_client.get("/api/offers/OFF123")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["offer_id"] == "OFF123"
        assert data["monthly_payment"] == 16500