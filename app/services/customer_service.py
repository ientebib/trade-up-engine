"""
Customer Service - Centralized business logic for customer operations
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from data import database

logger = logging.getLogger(__name__)


class CustomerService:
    """
    Service layer for customer-related business logic.
    """
    
    @staticmethod
    def search_customers(
        search_term: Optional[str] = None,
        risk_filter: Optional[str] = None,
        sort_by: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search and filter customers with pagination.
        
        Args:
            search_term: Search query
            risk_filter: Risk level filter (low/medium/high)
            sort_by: Sort criteria
            page: Page number (1-based)
            limit: Results per page
            
        Returns:
            Dict with customers list and pagination info
        """
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get customers from database with risk filtering at DB level
        customers, total = database.search_customers_with_filters(
            search_term=search_term,
            risk_filter=risk_filter,
            limit=limit,
            offset=offset
        )
        
        # Apply sorting if specified
        if sort_by and customers:
            if sort_by == "payment-high":
                customers.sort(key=lambda x: x.get("current_monthly_payment", 0), reverse=True)
            elif sort_by == "payment-low":
                customers.sort(key=lambda x: x.get("current_monthly_payment", 0))
            elif sort_by == "equity-high":
                customers.sort(key=lambda x: x.get("vehicle_equity", 0), reverse=True)
        
        # Calculate pagination
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        
        return {
            "customers": customers,
            "total": total,
            "page": page,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    
    @staticmethod
    def get_customer_details(customer_id: str) -> Optional[Dict]:
        """
        Get detailed customer information.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            Customer dict or None if not found
        """
        return database.get_customer_by_id(customer_id)
    
    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """
        Get real statistics for dashboard display.
        
        Returns:
            Dict with calculated statistics
        """
        # Get database status
        db_status = database.test_database_connection()
        inventory_stats = database.get_inventory_stats()
        
        # Calculate real customer statistics
        customer_stats = database.get_customer_statistics()
        
        # Calculate offer generation stats (cached for performance)
        offer_stats = database.get_offer_generation_stats()
        
        return {
            "total_customers": db_status["customers"]["count"],
            "total_inventory": db_status["inventory"]["count"],
            "avg_payment": customer_stats.get("avg_payment", 0),
            "avg_equity": customer_stats.get("avg_equity", 0),
            "avg_price": inventory_stats["average_price"],
            "brands": inventory_stats["brands"],
            "conversion_rate": offer_stats.get("conversion_rate", 0),
            "avg_npv": offer_stats.get("avg_npv", 0)
        }


# Create singleton instance
customer_service = CustomerService()