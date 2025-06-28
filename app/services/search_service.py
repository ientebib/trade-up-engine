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
    
    # Class-level thread pool for reuse
    _executor = ThreadPoolExecutor(max_workers=4)
    
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
        Now with async database operations and CPU-intensive work in thread pool.
        """
        loop = asyncio.get_event_loop()
        
        # Run database operations in thread pool
        customer = await loop.run_in_executor(
            SearchService._executor, database.get_customer_by_id, customer_id
        )
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        inventory = await loop.run_in_executor(
            SearchService._executor, database.get_tradeup_inventory_for_customer, customer
        )
        
        # Define CPU-intensive filtering function
        def _process_inventory_sync():
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
                
                # Vehicle type filter
                if vehicle_types:
                    model_lower = car.get('model', '').lower()
                    vehicle_type = SearchService._classify_vehicle(model_lower)
                    if vehicle_type not in vehicle_types:
                        continue
                
                # Quick payment estimation
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
                filtered_inventory.sort(key=lambda x: x['car_price'] * 0.15)
                
            if sort_order == 'desc':
                filtered_inventory.reverse()
            
            # Categorize results
            categories = {
                'perfect_match': [],
                'slight_increase': [],
                'moderate_increase': [],
                'stretch_options': []
            }
            
            for car in filtered_inventory:
                delta = car['estimated_payment_delta']
                if -0.05 <= delta <= 0.05:
                    categories['perfect_match'].append(car)
                elif 0.05 < delta <= 0.15:
                    categories['slight_increase'].append(car)
                elif 0.15 < delta <= 0.25:
                    categories['moderate_increase'].append(car)
                else:
                    categories['stretch_options'].append(car)
            
            # Apply limit
            limited_inventory = filtered_inventory[:limit]
            
            return filtered_inventory, limited_inventory, categories
        
        # Run CPU-intensive work in thread pool
        filtered_inventory, limited_inventory, categories = await loop.run_in_executor(
            SearchService._executor, _process_inventory_sync
        )
        
        # Prepare response
        current_car_info = {
            'brand': customer.get('current_car_brand'),
            'model': customer.get('current_car_model'),
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
                'max_price': max_price
            }
        }
    
    @staticmethod
    def _classify_vehicle(model: str) -> str:
        """Classify vehicle type based on model name"""
        model_lower = model.lower()
        
        # SUV patterns
        suv_keywords = ['suv', 'crv', 'rav4', 'highlander', 'pilot', 'explorer', 
                       'tahoe', 'suburban', 'expedition', 'traverse', 'durango',
                       'pathfinder', 'armada', 'tiguan', 'atlas', 'x5', 'x3',
                       'q5', 'q7', 'gla', 'glc', 'gle', 'macan', 'cayenne']
        
        # Truck patterns
        truck_keywords = ['silverado', 'sierra', 'f-150', 'f150', 'ram', 'tacoma',
                         'tundra', 'ranger', 'colorado', 'frontier', 'ridgeline',
                         'gladiator', 'maverick']
        
        # Sedan patterns
        sedan_keywords = ['sedan', 'accord', 'camry', 'civic', 'corolla', 'altima',
                         'sentra', 'maxima', 'sonata', 'elantra', 'malibu', 
                         'impala', 'fusion', 'taurus', 'charger', '300', 'passat',
                         'jetta', 'a4', 'a6', '3 series', '5 series', 'c-class',
                         'e-class', 's-class']
        
        # Hatchback patterns
        hatchback_keywords = ['hatchback', 'golf', 'gti', 'focus', 'fiesta', 'fit',
                             'versa', 'yaris', 'mazda3', 'impreza', 'crosstrek',
                             'kona', 'venue', 'kicks', 'hr-v', 'cx-30']
        
        # Van patterns
        van_keywords = ['van', 'odyssey', 'pacifica', 'sienna', 'grand caravan',
                       'town & country', 'transit', 'promaster', 'metris',
                       'sprinter']
        
        # Check patterns
        for keyword in suv_keywords:
            if keyword in model_lower:
                return 'SUV'
        
        for keyword in truck_keywords:
            if keyword in model_lower:
                return 'Truck'
                
        for keyword in sedan_keywords:
            if keyword in model_lower:
                return 'Sedan'
                
        for keyword in hatchback_keywords:
            if keyword in model_lower:
                return 'Hatchback'
                
        for keyword in van_keywords:
            if keyword in model_lower:
                return 'Van'
        
        # Default
        return 'Other'
    
    @staticmethod
    def _estimate_payment(customer: Dict, car: Dict) -> float:
        """
        Quick payment estimation for search results.
        This is a simplified calculation for filtering purposes.
        """
        from config.facade import get_decimal
        
        # Get configuration values
        gps_monthly = float(get_decimal("fees.gps.monthly"))
        interest_rate = float(get_decimal("rates.A1"))  # Default to A1
        service_fee_pct = float(get_decimal("fees.service.percentage"))
        
        # Basic parameters
        car_price = car['car_price']
        equity = customer['vehicle_equity']
        
        # Calculate loan amount with service fee
        service_fee = car_price * service_fee_pct
        loan_amount = car_price - equity + service_fee
        
        # Use configured interest rate with IVA
        monthly_rate = interest_rate * 1.16 / 12
        term = 48
        
        # PMT formula
        if monthly_rate > 0:
            payment = loan_amount * (monthly_rate * (1 + monthly_rate)**term) / ((1 + monthly_rate)**term - 1)
        else:
            payment = loan_amount / term
        
        # Add GPS monthly with IVA
        payment += gps_monthly * 1.16
        
        return payment
    
    @staticmethod
    async def save_customer_preferences(
        customer_id: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save customer preferences for future searches"""
        logger.info(f"Saving preferences for customer {customer_id}: {preferences}")
        
        # TODO: Implement database storage
        return {
            'customer_id': customer_id,
            'preferences': preferences,
            'saved': True
        }
    
    @staticmethod
    async def get_search_suggestions(
        customer_id: str,
        partial_query: str
    ) -> List[str]:
        """Get search suggestions based on partial input"""
        suggestions = []
        
        # Brand suggestions
        brands = ['Toyota', 'Honda', 'Nissan', 'Mazda', 'Ford', 'Chevrolet', 
                 'Volkswagen', 'Hyundai', 'Kia', 'BMW', 'Mercedes-Benz', 'Audi']
        
        # Model suggestions
        models = ['Corolla', 'Camry', 'RAV4', 'Civic', 'Accord', 'CR-V',
                 'Sentra', 'Altima', 'Rogue', 'Mazda3', 'CX-5', 'F-150']
        
        # Filter based on partial query
        query_lower = partial_query.lower()
        
        for brand in brands:
            if query_lower in brand.lower():
                suggestions.append(brand)
        
        for model in models:
            if query_lower in model.lower():
                suggestions.append(model)
        
        return suggestions[:10]  # Limit to 10 suggestions
    
    @staticmethod 
    async def live_inventory_search(
        customer_id: str,
        search_term: str,
        configuration: Dict[str, Any],
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Live inventory search with real-time NPV calculations.
        This is used by the Deal Architect for interactive searching.
        """
        loop = asyncio.get_event_loop()
        
        # Get customer data in thread pool
        customer = await loop.run_in_executor(
            SearchService._executor, database.get_customer_by_id, customer_id
        )
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        # Get all inventory
        all_inventory = await loop.run_in_executor(
            SearchService._executor, database.get_all_inventory
        )
        
        # Define search function for thread pool
        def _search_and_calculate():
            # Filter by search term
            search_lower = search_term.lower()
            filtered = []
            
            for car in all_inventory:
                # Search in brand, model, year
                if (search_lower in car.get('brand', '').lower() or
                    search_lower in car.get('model', '').lower() or
                    search_lower in str(car.get('year', ''))):
                    
                    # Calculate NPV with configuration
                    from engine.basic_matcher import BasicMatcher
                    
                    # Apply configuration
                    offer_config = {
                        'service_fee_pct': configuration.get('service_fee_pct', 0.03),
                        'cxa_pct': configuration.get('cxa_pct', 0.005),
                        'cac_bonus': configuration.get('cac_bonus', 0),
                        'kavak_total_amount': configuration.get('kavak_total_amount', 25000),
                        'insurance_amount': configuration.get('insurance_amount', 10999),
                        'term_months': configuration.get('term_months', 48)
                    }
                    
                    # Calculate NPV
                    matcher = BasicMatcher()
                    npv = matcher._calculate_npv_for_car(customer, car, offer_config)
                    
                    car['calculated_npv'] = npv
                    car['monthly_payment'] = matcher._estimate_payment(customer, car, offer_config)
                    
                    filtered.append(car)
            
            # Sort by NPV (highest first)
            filtered.sort(key=lambda x: x.get('calculated_npv', 0), reverse=True)
            
            # Limit results
            return filtered[:limit]
        
        # Run search in thread pool
        results = await loop.run_in_executor(
            SearchService._executor, _search_and_calculate
        )
        
        return {
            'results': results,
            'count': len(results),
            'search_term': search_term,
            'configuration': configuration
        }
    
    @staticmethod
    def universal_search(query: str, limit: int = 50) -> Dict[str, Any]:
        """Universal search across customers, inventory, and offers"""
        # This remains synchronous for backward compatibility
        # but should be converted to async in the future
        results = {
            'customers': [],
            'inventory': [],
            'query': query,
            'total_results': 0
        }
        
        # Search customers
        customers, _ = database.search_customers(search_term=query, limit=limit)
        results['customers'] = customers[:10]  # Limit customer results
        
        # Search inventory by brand/model
        # This is simplified - in production would use proper search
        results['total_results'] = len(results['customers'])
        
        return results
    
    @staticmethod
    def get_inventory_filters() -> Dict[str, Any]:
        """Get available filter options from inventory data"""
        # This remains synchronous for backward compatibility
        return {
            'brands': ['Toyota', 'Honda', 'Nissan', 'Mazda', 'Ford', 'Chevrolet'],
            'vehicle_types': ['SUV', 'Sedan', 'Truck', 'Hatchback', 'Van'],
            'year_range': {'min': 2015, 'max': 2024},
            'price_range': {'min': 100000, 'max': 1000000},
            'km_range': {'min': 0, 'max': 200000}
        }
    
    @staticmethod
    async def smart_search_minimum_subsidy(
        customer_id: str,
        search_params: Dict[str, Any],
        executor: ThreadPoolExecutor
    ) -> Dict[str, Any]:
        """Smart search that finds minimum subsidy needed for viable offers"""
        # TODO: Implement smart search algorithm
        # For now, return placeholder
        return {
            'customer_id': customer_id,
            'minimum_subsidy': 0,
            'viable_cars': [],
            'search_params': search_params
        }


# Create singleton instance
search_service = SearchService()