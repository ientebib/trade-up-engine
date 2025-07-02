"""
Offer Service - Centralized business logic for offer generation and management
This keeps routes clean and focused on HTTP/rendering concerns only.
"""
import logging
from typing import Dict, List, Optional, Any
from engine.basic_matcher_sync import basic_matcher_sync as basic_matcher
from engine.calculator import generate_amortization_table
from data import database
from app.utils.validation import UnifiedValidator as DataValidator, DataIntegrityError

logger = logging.getLogger(__name__)


class OfferService:
    """
    Service layer for all offer-related business logic.
    Routes should only call these methods, not implement business logic directly.
    """
    
    @staticmethod
    def generate_offers_for_customer(customer_id: str, custom_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate all viable offers for a customer using two-stage filtering.
        
        Stage 1: Pre-filter inventory to logical trade-up candidates
        Stage 2: Apply financial matching and business rules
        
        Args:
            customer_id: Customer identifier
            custom_config: Optional custom configuration overrides
            
        Returns:
            Dict containing offers and metadata
            
        Raises:
            ValueError: If customer not found
            RuntimeError: If inventory not available
        """
        # Get customer data
        customer = database.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        # Stage 1: Get pre-filtered inventory (logical trade-ups only)
        logger.info(f"🎯 Stage 1: Pre-filtering inventory for customer {customer_id}")
        inventory_records = database.get_tradeup_inventory_for_customer(customer)
        
        if not inventory_records:
            logger.warning(f"⚠️ No logical trade-up candidates found for customer {customer_id}")
            return {
                "offers": {"refresh": [], "upgrade": [], "max_upgrade": []},
                "customer": customer,
                "stats": {"total_evaluated": 0, "total_viable": 0}
            }
        
        logger.info(f"✅ Stage 1 complete: {len(inventory_records)} potential trade-ups found")
        
        # Stage 2: Apply financial matching and business rules
        logger.info(f"🎯 Stage 2: Applying financial matching for {customer_id}")
        if custom_config:
            result = basic_matcher.find_all_viable(customer, inventory_records, custom_config)
        else:
            result = basic_matcher.find_all_viable(customer, inventory_records)
        
        # Map from basic_matcher keys to frontend keys
        tier_mapping = {
            "Refresh": "refresh",
            "Upgrade": "upgrade", 
            "Max Upgrade": "max_upgrade"
        }
        
        validated_offers = {"refresh": [], "upgrade": [], "max_upgrade": []}
        for backend_tier, frontend_tier in tier_mapping.items():
            for offer in result.get("offers", {}).get(backend_tier, []):
                # Skip validation for now - just pass through
                validated_offers[frontend_tier].append(offer)
        
        # Calculate total offers across all tiers
        total_offers = sum(len(offers) for offers in validated_offers.values())
        
        # Return result with lowercase keys for frontend compatibility
        return {
            "offers": validated_offers,
            "total_offers": total_offers,
            "cars_tested": result.get("stats", {}).get("total_cars_evaluated", 0),
            "processing_time": result.get("stats", {}).get("processing_time", 0),
            "fees_used": result.get("fees_used", {}),
            "message": result.get("message", ""),
            "customer": customer,
            "stats": result.get("stats", {})
        }
    
    @staticmethod
    def get_customer_details(customer_id: str) -> Optional[Dict]:
        """
        Get customer details - delegates to database layer.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            Customer dict or None if not found
        """
        return database.get_customer_by_id(customer_id)
    
    @staticmethod
    def get_offer_for_car(customer_id: str, car_id: str) -> Optional[Dict]:
        """
        Get a specific offer for a customer and car combination.
        
        Args:
            customer_id: Customer identifier
            car_id: Car identifier
            
        Returns:
            Offer dict or None if not found
            
        Raises:
            ValueError: If customer or car not found
        """
        # Get customer
        customer = database.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        # Get specific car efficiently
        car = database.get_car_by_id(car_id)
        if not car:
            raise ValueError(f"Car {car_id} not found in inventory")
        
        # Generate offer for this specific car
        offers = basic_matcher.find_all_viable(customer, [car])
        
        # Find the specific offer in results
        for tier_offers in offers['offers'].values():
            for offer in tier_offers:
                if str(offer['car_id']) == str(car_id):
                    return offer
        
        return None
    
    @staticmethod
    def generate_amortization_for_offer(customer_id: str, car_id: str) -> Dict[str, Any]:
        """
        Generate amortization table for a specific offer.
        
        Args:
            customer_id: Customer identifier
            car_id: Car identifier
            
        Returns:
            Dict containing offer details and amortization schedule
            
        Raises:
            ValueError: If offer cannot be generated
        """
        # Get the specific offer
        offer = OfferService.get_offer_for_car(customer_id, car_id)
        if not offer:
            raise ValueError(f"No offer found for customer {customer_id} and car {car_id}")
        
        # Generate amortization schedule
        schedule = generate_amortization_table(offer)
        
        # Calculate totals
        total_payments = sum(row['payment'] for row in schedule)
        total_interest = sum(row['interest'] for row in schedule)
        
        return {
            "offer": offer,
            "schedule": schedule,
            "term": offer['term'],
            "total_payments": total_payments,
            "total_interest": total_interest
        }
    
    @staticmethod
    def prepare_customer_detail_data(customer_id: str, generate_offers: bool = False) -> Dict[str, Any]:
        """
        Prepare all data needed for customer detail page.
        
        Args:
            customer_id: Customer identifier
            generate_offers: Whether to generate offers
            
        Returns:
            Dict with customer data and optional offers
            
        Raises:
            ValueError: If customer not found
        """
        # Get customer
        customer = database.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        # Format customer data directly (presenter was removed)
        formatted_customer = customer.copy()
        
        # Add mapped interest rate based on risk profile for display purposes
        try:
            from config.facade import get as cfg_get
            risk_profile = customer.get('risk_profile_name') or customer.get('risk_profile')
            if risk_profile:
                mapped_rate = cfg_get(f"rates.{risk_profile}")
                if mapped_rate is not None:
                    formatted_customer['mapped_interest_rate'] = float(mapped_rate)
        except Exception:
            # Fallback: leave field absent if lookup fails
            pass
        
        # Prepare response
        result = {"customer": formatted_customer}
        
        # Generate offers if requested
        if generate_offers:
            try:
                offers_data = OfferService.generate_offers_for_customer(customer_id)
                result["offers_data"] = offers_data
            except Exception as e:
                logger.error(f"Failed to generate offers for {customer_id}: {e}")
                result["offers_data"] = None
                result["offers_error"] = str(e)
        
        return result
    
    @staticmethod
    def format_amortization_for_frontend(offer: Dict) -> Dict[str, Any]:
        """
        Generate and format amortization schedule for frontend display.
        
        Args:
            offer: Offer dict from matcher
            
        Returns:
            Formatted amortization data for frontend
        """
        # Generate schedule
        schedule = generate_amortization_table(offer)
        
        # Format for frontend expectations
        for row in schedule:
            # Frontend expects 'balance' field
            row['balance'] = row.get('ending_balance', 0)
        
        # Extract summary data
        first_row = schedule[0] if schedule else {}
        
        return {
            "schedule": schedule,
            "table": schedule,  # Frontend expects 'table' field
            "payment_total": first_row.get("payment", 0),
            "principal_month1": first_row.get("principal", 0),
            "interest_month1": first_row.get("interest", 0),
            "gps_fee": first_row.get("cargos", 0),
            "cargos": first_row.get("cargos", 0),
        }
    
    @staticmethod
    def process_custom_config(request_data: Dict) -> Dict[str, Any]:
        """
        Process custom configuration from request data.
        
        Args:
            request_data: Raw request data
            
        Returns:
            Processed configuration dict
        """
        # Extract custom configuration
        kavak_total_enabled = request_data.get('kavak_total_enabled', True)
        kavak_total_amount = 25000 if kavak_total_enabled else 0
        
        return {
            'service_fee_pct': request_data.get('service_fee_pct', 0.04),
            'cxa_pct': request_data.get('cxa_pct', 0.04),
            'cac_bonus': request_data.get('cac_bonus', 0),
            'kavak_total_amount': kavak_total_amount,
            'gps_monthly_fee': request_data.get('gps_monthly_fee', 350),
            'gps_installation_fee': request_data.get('gps_installation_fee', 750),
            'insurance_amount': request_data.get('insurance_amount', 10999),
            # Allow overriding base annual interest rate (e.g., 0.26 for 26%)
            'interest_rate': request_data.get('interest_rate'),
            'term_months': request_data.get('term_months')  # Optional specific term
        }


    @staticmethod
    async def generate_for_multiple_customers(
        customer_ids: List[str], 
        max_offers_per_customer: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate offers for multiple customers using safe queued processing.
        
        This method now uses a request queue to prevent race conditions
        and memory exhaustion from concurrent bulk requests.
        
        Args:
            customer_ids: List of customer identifiers (max 50)
            max_offers_per_customer: Optional limit per customer
            
        Returns:
            Dict with request_id for tracking
        """
        from .bulk_queue import get_bulk_queue
        
        # Get the queue
        queue = get_bulk_queue()
        
        # Submit request
        request_id = await queue.submit_request(
            customer_ids=customer_ids,
            max_offers_per_customer=max_offers_per_customer
        )
        
        return {
            "request_id": request_id,
            "status": "queued",
            "message": f"Bulk request queued for {len(customer_ids)} customers",
            "poll_url": f"/api/offers/bulk-status/{request_id}"
        }
    
    @staticmethod
    def get_bulk_request_status(request_id: str) -> Optional[Dict]:
        """
        Get status of a bulk offer generation request
        
        Args:
            request_id: Request ID to check
            
        Returns:
            Status dict or None if not found
        """
        from .bulk_queue import get_bulk_queue
        
        queue = get_bulk_queue()
        return queue.get_request_status(request_id)


# Create singleton instance
offer_service = OfferService()