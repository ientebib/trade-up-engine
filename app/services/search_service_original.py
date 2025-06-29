"""
Search Service - Smart inventory search and filtering for customers
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from data import database
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class SearchService:
    """
    Service layer for intelligent inventory search and filtering.
    Helps find the right vehicles for customers based on preferences and constraints.
    """
    
    @staticmethod
    async def search_inventory_for_customer(
        customer_id: str,
        payment_delta_range: Tuple[float, float] = (-0.1, 0.25),
        brands: Optional[List[str]] = None,
        min_year: Optional[int] = None,
        max_km: Optional[float] = None,
        vehicle_types: Optional[List[str]] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: str = 'payment_delta',
        sort_order: str = 'asc',
        limit: int = 50,
        quick_calc: bool = True
    ) -> Dict[str, Any]:
        """
        Search inventory based on customer preferences and payment targets.
        
        Args:
            customer_id: Customer identifier
            payment_delta_range: (min, max) payment change as decimals
            brands: List of preferred brands
            min_year: Minimum vehicle year
            max_km: Maximum kilometers
            vehicle_types: List of vehicle types (SUV, Sedan, etc.)
            
        Returns:
            Dict with search results and metadata
        """
        # Use ThreadPoolExecutor for blocking operations
        loop = asyncio.get_event_loop()
        
        # Run database operations in thread pool
        with ThreadPoolExecutor(max_workers=1) as executor:
            # Get customer data
            customer = await loop.run_in_executor(
                executor, database.get_customer_by_id, customer_id
            )
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")
            
            # Get base inventory for trade-ups
            inventory = await loop.run_in_executor(
                executor, database.get_tradeup_inventory_for_customer, customer
            )
        
        # Process filtering in thread pool for CPU-intensive work
        def _process_inventory():
            filtered_inventory = []
        
        for car in inventory:
            # Brand filter
            if brands:
                car_brand = car.get('brand', '').lower()
                if not any(brand.lower() in car_brand for brand in brands):
                    continue
            
            # Year filter
            if min_year and car.get('year', 0) < min_year:
                continue
            
            # Kilometers filter
            if max_km and car.get('kilometers', float('inf')) > max_km:
                continue
            
            # Price filters
            if min_price and car.get('car_price', 0) < min_price:
                continue
            if max_price and car.get('car_price', 0) > max_price:
                continue
            
            # Vehicle type filter (simple classification)
            if vehicle_types:
                model_lower = car.get('model', '').lower()
                vehicle_type = SearchService._classify_vehicle(model_lower)
                if vehicle_type not in vehicle_types:
                    continue
            
            # Quick payment estimation (simplified)
            estimated_payment = SearchService._estimate_payment(customer, car)
            
            # Guard against division by zero
            current_payment = customer.get('current_monthly_payment', 0)
            if current_payment <= 0:
                logger.warning(f"Customer {customer.get('customer_id')} has invalid payment: {current_payment}, defaulting to 1")
                current_payment = 1
                
            payment_delta = (estimated_payment / current_payment) - 1
            
            # Payment delta filter
            if payment_delta < payment_delta_range[0] or payment_delta > payment_delta_range[1]:
                continue
            
            # Add estimated payment to car data
            car['estimated_monthly_payment'] = estimated_payment
            car['estimated_payment_delta'] = payment_delta
            
            # Add vehicle type classification
            car['vehicle_type'] = SearchService._classify_vehicle(car.get('model', ''))
            
            filtered_inventory.append(car)
        
        # Apply sorting
        if sort_by == 'payment_delta':
            filtered_inventory.sort(key=lambda x: abs(x['estimated_payment_delta']))
        elif sort_by == 'payment':
            filtered_inventory.sort(key=lambda x: x['estimated_monthly_payment'])
        elif sort_by == 'price':
            filtered_inventory.sort(key=lambda x: x['car_price'])
        elif sort_by == 'year':
            filtered_inventory.sort(key=lambda x: x.get('year', 0))
        elif sort_by == 'km':
            filtered_inventory.sort(key=lambda x: x.get('kilometers', 0))
        elif sort_by == 'npv':
            # For quick calc, use a simplified NPV estimate
            filtered_inventory.sort(key=lambda x: x['car_price'] * 0.15)  # Rough estimate
            
        # Apply sort order
        if sort_order == 'desc':
            filtered_inventory.reverse()
        
        # Categorize results
        categories = {
            'perfect_match': [],  # -5% to +5%
            'slight_increase': [],  # +5% to +15%
            'moderate_increase': [],  # +15% to +25%
            'stretch_options': []  # > +25%
        }
        
        # Apply limit and categorize
        limited_inventory = filtered_inventory[:limit]
        
        for car in limited_inventory:
            delta = car['estimated_payment_delta']
            if -0.05 <= delta <= 0.05:
                categories['perfect_match'].append(car)
            elif 0.05 < delta <= 0.15:
                categories['slight_increase'].append(car)
            elif 0.15 < delta <= 0.25:
                categories['moderate_increase'].append(car)
            else:
                categories['stretch_options'].append(car)
        
        # Get customer's current car details for comparison
        current_car_info = {
            'model': customer.get('current_car_model', 'Unknown'),
            'year': customer.get('current_car_year'),
            'km': customer.get('current_car_km'),
            'price': customer.get('current_car_price')
        }
        
        return {
            'total_matches': len(filtered_inventory),
            'showing': len(limited_inventory),
            'vehicles': limited_inventory,
            'categories': categories,
            'current_car': current_car_info,
            'search_criteria': {
                'payment_range': f"{payment_delta_range[0]*100:+.0f}% to {payment_delta_range[1]*100:+.0f}%",
                'brands': brands,
                'min_year': min_year,
                'max_km': max_km,
                'vehicle_types': vehicle_types,
                'min_price': min_price,
                'max_price': max_price,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
        }
    
    @staticmethod
    def _classify_vehicle(model: str) -> str:
        """Simple vehicle classification based on model name"""
        model_lower = model.lower()
        
        # SUV keywords
        suv_keywords = ['x3', 'x5', 'q5', 'q7', 'crv', 'cr-v', 'rav4', 'tiguan', 
                       'tucson', 'sportage', 'cx-5', 'explorer', 'pilot', 'highlander']
        if any(keyword in model_lower for keyword in suv_keywords):
            return 'SUV'
        
        # Sedan keywords
        sedan_keywords = ['camry', 'accord', 'civic', 'corolla', 'a4', 'a6', 
                         'serie 3', 'serie 5', 'clase c', 'clase e', 'mazda3', 'sentra']
        if any(keyword in model_lower for keyword in sedan_keywords):
            return 'Sedan'
        
        # Truck keywords
        truck_keywords = ['f150', 'f-150', 'silverado', 'ram', 'tacoma', 'ranger']
        if any(keyword in model_lower for keyword in truck_keywords):
            return 'Truck'
        
        # Hatchback keywords
        hatch_keywords = ['golf', 'swift', 'fit', 'versa', 'yaris', 'rio']
        if any(keyword in model_lower for keyword in hatch_keywords):
            return 'Hatchback'
        
        return 'Other'
    
    @staticmethod
    def _estimate_payment(customer: Dict, car: Dict) -> float:
        """
        Quick payment estimation for search results.
        This is a simplified calculation for filtering purposes.
        """
        # Basic parameters
        car_price = car['car_price']
        equity = customer['vehicle_equity']
        
        # Simplified calculation
        loan_amount = car_price - equity + 35000  # Rough estimate with fees
        
        # Assume 48-month term and 20% annual rate with IVA
        monthly_rate = 0.20 * 1.16 / 12
        term = 48
        
        # PMT formula
        if monthly_rate > 0:
            payment = loan_amount * (monthly_rate * (1 + monthly_rate)**term) / ((1 + monthly_rate)**term - 1)
        else:
            payment = loan_amount / term
        
        # Add GPS monthly
        payment += 406  # GPS with IVA
        
        return payment
    
    @staticmethod
    async def save_customer_preferences(
        customer_id: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save customer preferences for future searches.
        
        Args:
            customer_id: Customer identifier
            preferences: Dict with preferences like brands, vehicle types, etc.
            
        Returns:
            Saved preferences
        """
        # For now, store in memory or session
        # In production, this would persist to database
        logger.info(f"Saving preferences for customer {customer_id}: {preferences}")
        
        # TODO: Implement database storage
        return {
            'customer_id': customer_id,
            'preferences': preferences,
            'saved': True
        }
    
    @staticmethod
    async def get_similar_vehicles(car_id: str, limit: int = 10) -> List[Dict]:
        """
        Find similar vehicles to a given car.
        
        Args:
            car_id: Reference car ID
            limit: Maximum number of similar cars to return
            
        Returns:
            List of similar vehicles
        """
        # Get the reference car
        car = database.get_car_by_id(car_id)
        if not car:
            return []
        
        # Get all inventory
        inventory = database.get_all_inventory()
        
        # Find similar cars (same brand, similar year, similar price)
        similar = []
        car_brand = car.get('brand', '').lower()
        car_year = car.get('year', 0)
        car_price = car.get('car_price', 0)
        
        for other in inventory:
            if other['car_id'] == car_id:
                continue
            
            # Same brand
            if car_brand not in other.get('brand', '').lower():
                continue
            
            # Similar year (±2 years)
            if abs(other.get('year', 0) - car_year) > 2:
                continue
            
            # Similar price (±20%)
            price_ratio = other.get('car_price', 0) / car_price if car_price > 0 else 0
            if price_ratio < 0.8 or price_ratio > 1.2:
                continue
            
            similar.append(other)
        
        # Sort by price difference
        similar.sort(key=lambda x: abs(x.get('car_price', 0) - car_price))
        
        return similar[:limit]
    
    @staticmethod
    async def live_inventory_search(
        customer_id: str,
        search_term: str,
        configuration: Dict[str, Any],
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Live inventory search with real-time NPV calculations.
        
        Args:
            customer_id: Customer identifier
            search_term: Text search (brand, model, etc.)
            configuration: Current configuration from Deal Architect
            limit: Maximum results
            
        Returns:
            Dict with vehicles and full financial calculations
        """
        # Get customer data
        customer = database.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        # Get base inventory
        inventory = database.get_tradeup_inventory_for_customer(customer)
        
        # Filter by search term
        filtered_inventory = []
        search_lower = search_term.lower()
        
        if search_term:
            for car in inventory:
                # Search in brand, model, and year
                if (search_lower in car.get('brand', '').lower() or
                    search_lower in car.get('model', '').lower() or
                    search_lower in str(car.get('year', ''))):
                    filtered_inventory.append(car)
        else:
            # No search term, return top cars by price
            filtered_inventory = sorted(inventory, key=lambda x: x['car_price'], reverse=True)[:100]
        
        # Apply configuration for real NPV calculation
        custom_fees = {
            'service_fee_pct': configuration.get('service_fee_pct', 0.04),
            'cxa_pct': configuration.get('cxa_pct', 0.04),
            'cac_bonus': configuration.get('cac_bonus', 0),
            'kavak_total_amount': configuration.get('kavak_total_enabled', True) * 25000,
            'insurance_amount': configuration.get('insurance_amount', 10999),
            'term_months': configuration.get('term', 48)
        }
        
        # Calculate real offers using basic_matcher
        from engine.basic_matcher import basic_matcher
        offers_result = basic_matcher.find_all_viable(
            customer, 
            filtered_inventory[:limit],  # Limit before calculation for performance
            custom_fees
        )
        
        # Flatten all offers from categories
        all_offers = []
        for tier, offers in offers_result['offers'].items():
            for offer in offers:
                offer['tier'] = tier
                all_offers.append(offer)
        
        # Sort by NPV descending
        all_offers.sort(key=lambda x: x.get('npv', 0), reverse=True)
        
        return {
            'search_term': search_term,
            'total_matches': len(filtered_inventory),
            'showing': len(all_offers),
            'vehicles': all_offers,
            'configuration': configuration,
            'customer': {
                'id': customer_id,
                'current_payment': customer['current_monthly_payment'],
                'equity': customer['vehicle_equity']
            }
        }


# Create singleton instance
search_service = SearchService()