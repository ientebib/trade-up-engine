"""
Search Service - Centralized search and filtering logic
"""
import logging
from typing import Dict, List, Any, Optional
import asyncio
from data import database
from engine.smart_search import smart_search_engine

logger = logging.getLogger(__name__)


class SearchService:
    """
    Service layer for all search-related business logic.
    """
    
    @staticmethod
    def universal_search(query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search across customers and inventory.
        
        Args:
            query: Search query string
            limit: Maximum results per category
            
        Returns:
            Dict with search results by category
        """
        results = {
            "customers": [],
            "inventory": [],
            "query": query,
            "total": 0
        }
        
        # Search customers using database method
        try:
            customers, _ = database.search_customers(search_term=query, limit=limit, offset=0)
            results["customers"] = customers
        except Exception as e:
            logger.error(f"Error searching customers: {e}")
        
        # Search inventory using new efficient method
        try:
            inventory_matches = database.search_inventory(query=query, limit=limit)
            results["inventory"] = inventory_matches
        except Exception as e:
            logger.error(f"Error searching inventory: {e}")
        
        results["total"] = len(results["customers"]) + len(results["inventory"])
        
        return results
    
    @staticmethod
    async def smart_search_minimum_subsidy(
        customer_id: str,
        search_params: Dict[str, Any],
        executor=None
    ) -> Dict[str, Any]:
        """
        Find minimum subsidy needed for viable offers.
        
        Args:
            customer_id: Customer identifier
            search_params: Search parameters including target delta, max subsidy, etc.
            executor: Thread pool executor for async operation
            
        Returns:
            Dict with search results and minimum subsidy offers
        """
        # Get customer
        customer = database.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        # Use two-stage filtering: Get pre-filtered inventory
        logger.info(f"🎯 Smart search Stage 1: Pre-filtering inventory for customer {customer_id}")
        inventory_records = database.get_tradeup_inventory_for_customer(customer)
        
        if not inventory_records:
            logger.warning(f"⚠️ No logical trade-up candidates for smart search")
            return {
                "offers_found": 0,
                "offers": [],
                "search_params": processed_params
            }
        
        # Process search parameters with defaults
        processed_params = {
            'target_payment_delta': search_params.get('target_payment_delta', 0.05),
            'max_subsidy': search_params.get('max_subsidy', 50000),
            'subsidy_step': search_params.get('subsidy_step', 1000),
            'service_fee_pct': search_params.get('service_fee_pct', 0.04),
            'cxa_pct': search_params.get('cxa_pct', 0.04),
            'kavak_total_amount': search_params.get('kavak_total_amount', 25000),
            'term_preference': search_params.get('term_preference'),
        }
        
        logger.info(f"✅ Stage 1 complete: {len(inventory_records)} candidates for smart search")
        
        # Stage 2: Run smart search with financial matching
        logger.info(f"🎯 Smart search Stage 2: Finding minimum subsidy offers")
        if executor:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                smart_search_engine.find_minimum_subsidy_offers,
                customer,
                inventory_records,
                processed_params
            )
        else:
            result = smart_search_engine.find_minimum_subsidy_offers(
                customer,
                inventory_records,
                processed_params
            )
        
        logger.info(f"🎯 Smart search for {customer_id}: {result.get('offers_found', 0)} offers found")
        
        return result
    
    @staticmethod
    def get_inventory_filters() -> Dict[str, Any]:
        """
        Get available filter options from inventory data.
        
        Returns:
            Dict with filter options (makes, years, price range)
        """
        try:
            # Use efficient aggregate method instead of loading all inventory
            return database.get_inventory_aggregates()
            
        except Exception as e:
            logger.error(f"Error getting inventory filters: {e}")
            return {
                "makes": [],
                "years": [],
                "price_range": {"min": 0, "max": 0},
                "total_cars": 0
            }


# Create singleton instance
search_service = SearchService()