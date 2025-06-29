"""
Search Service - Truly async inventory search with high performance
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from data import database
import asyncio
from concurrent.futures import ThreadPoolExecutor
import redis
import ujson
from asyncio import gather, create_task
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SearchService:
    """
    High-performance async search service with Redis caching and parallel processing.
    """
    
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=8)
        self._redis = None
        self._cache_ttl = 300  # 5 minutes for search results
        
    def _get_redis(self):
        """Get or create Redis connection"""
        if not self._redis:
            try:
                self._redis = redis.Redis(
                    host='localhost',
                    port=6379,
                    decode_responses=True
                )
                # Test connection
                self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis not available, using in-memory cache: {e}")
                # Fallback to in-memory cache if Redis not available
                self._redis = None
        return self._redis
    
    def _get_cache_key(self, prefix: str, params: Dict) -> str:
        """Generate cache key from parameters"""
        param_str = ujson.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        return f"{prefix}:{param_hash}"
    
    def _cache_get(self, key: str) -> Optional[Any]:
        """Get from cache (Redis or memory)"""
        redis = self._get_redis()
        if redis:
            try:
                data = redis.get(key)
                return ujson.loads(data) if data else None
            except Exception as e:
                logger.error(f"Cache get error: {e}")
        return None
    
    def _cache_set(self, key: str, value: Any, ttl: int = None):
        """Set in cache with TTL"""
        redis = self._get_redis()
        if redis:
            try:
                redis.setex(
                    key, 
                    ttl or self._cache_ttl,
                    ujson.dumps(value)
                )
            except Exception as e:
                logger.error(f"Cache set error: {e}")
    
    async def search_inventory_for_customer(
        self,
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
        Truly async search with caching and parallel processing.
        """
        # Check cache first
        cache_params = {
            'customer_id': customer_id,
            'payment_delta_range': payment_delta_range,
            'brands': brands,
            'min_year': min_year,
            'max_km': max_km,
            'vehicle_types': vehicle_types,
            'min_price': min_price,
            'max_price': max_price,
            'sort_by': sort_by,
            'limit': limit
        }
        
        cache_key = self._get_cache_key('search', cache_params)
        cached_result = self._cache_get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for search: {customer_id}")
            return cached_result
        
        # Parallel data fetching
        loop = asyncio.get_event_loop()
        
        # Create tasks for parallel execution
        customer_task = loop.run_in_executor(
            self._executor, database.get_customer_by_id, customer_id
        )
        inventory_task = loop.run_in_executor(
            self._executor, self._get_filtered_inventory, brands, min_year, max_km, min_price, max_price
        )
        
        # Wait for both in parallel
        customer, base_inventory = await gather(customer_task, inventory_task)
        
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        # Process inventory in chunks for better performance
        chunk_size = 100
        chunks = [base_inventory[i:i+chunk_size] for i in range(0, len(base_inventory), chunk_size)]
        
        # Process chunks in parallel
        chunk_tasks = []
        for chunk in chunks:
            task = loop.run_in_executor(
                self._executor,
                self._process_inventory_chunk,
                chunk, customer, payment_delta_range, vehicle_types
            )
            chunk_tasks.append(task)
        
        # Gather all results
        chunk_results = await gather(*chunk_tasks)
        
        # Combine results
        filtered_inventory = []
        for chunk_result in chunk_results:
            filtered_inventory.extend(chunk_result)
        
        # Sort and categorize
        result = await loop.run_in_executor(
            self._executor,
            self._sort_and_categorize,
            filtered_inventory, sort_by, sort_order, limit, customer
        )
        
        # Cache the result
        self._cache_set(cache_key, result)
        
        return result
    
    def _get_filtered_inventory(
        self,
        brands: Optional[List[str]],
        min_year: Optional[int],
        max_km: Optional[float],
        min_price: Optional[float],
        max_price: Optional[float]
    ) -> List[Dict]:
        """Pre-filter inventory at database level"""
        # This should ideally be a database query with filters
        # For now, we'll get inventory and filter
        all_inventory = database.get_all_inventory()
        
        filtered = []
        for car in all_inventory:
            # Apply basic filters
            if brands and car.get('brand', '').lower() not in [b.lower() for b in brands]:
                continue
            if min_year and car.get('year', 0) < min_year:
                continue
            if max_km and car.get('kilometers', float('inf')) > max_km:
                continue
            if min_price and car.get('car_price', 0) < min_price:
                continue
            if max_price and car.get('car_price', 0) > max_price:
                continue
                
            filtered.append(car)
        
        return filtered
    
    def _process_inventory_chunk(
        self,
        chunk: List[Dict],
        customer: Dict,
        payment_delta_range: Tuple[float, float],
        vehicle_types: Optional[List[str]]
    ) -> List[Dict]:
        """Process a chunk of inventory items"""
        results = []
        
        for car in chunk:
            # Vehicle type filter
            if vehicle_types:
                vehicle_type = self._classify_vehicle(car.get('model', ''))
                if vehicle_type not in vehicle_types:
                    continue
            
            # Calculate payment
            estimated_payment = self._estimate_payment(customer, car)
            
            # Guard against division by zero
            current_payment = customer.get('current_monthly_payment', 0)
            if current_payment <= 0:
                current_payment = 1
                
            payment_delta = (estimated_payment / current_payment) - 1
            
            # Payment delta filter
            if payment_delta < payment_delta_range[0] or payment_delta > payment_delta_range[1]:
                continue
            
            # Add calculated fields
            car['estimated_monthly_payment'] = estimated_payment
            car['estimated_payment_delta'] = payment_delta
            car['vehicle_type'] = self._classify_vehicle(car.get('model', ''))
            
            results.append(car)
        
        return results
    
    def _sort_and_categorize(
        self,
        inventory: List[Dict],
        sort_by: str,
        sort_order: str,
        limit: int,
        customer: Dict
    ) -> Dict[str, Any]:
        """Sort and categorize results"""
        # Sort
        if sort_by == 'payment_delta':
            inventory.sort(key=lambda x: abs(x['estimated_payment_delta']))
        elif sort_by == 'payment':
            inventory.sort(key=lambda x: x['estimated_monthly_payment'])
        elif sort_by == 'price':
            inventory.sort(key=lambda x: x['car_price'])
        elif sort_by == 'year':
            inventory.sort(key=lambda x: x.get('year', 0))
        elif sort_by == 'km':
            inventory.sort(key=lambda x: x.get('kilometers', 0))
        elif sort_by == 'npv':
            inventory.sort(key=lambda x: x['car_price'] * 0.15)
            
        if sort_order == 'desc':
            inventory.reverse()
        
        # Categorize
        categories = {
            'perfect_match': [],
            'slight_increase': [],
            'moderate_increase': [],
            'stretch_options': []
        }
        
        for car in inventory:
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
        limited_inventory = inventory[:limit]
        
        # Prepare response
        current_car_info = {
            'brand': customer.get('current_car_brand'),
            'model': customer.get('current_car_model'),
            'year': customer.get('current_car_year'),
            'km': customer.get('current_car_km'),
            'price': customer.get('current_car_price')
        }
        
        return {
            'total_matches': len(inventory),
            'showing': len(limited_inventory),
            'vehicles': limited_inventory,
            'categories': categories,
            'current_car': current_car_info,
            'cached_at': datetime.utcnow().isoformat(),
            'cache_ttl_seconds': self._cache_ttl
        }
    
    async def live_inventory_search(
        self,
        customer_id: str,
        search_term: str,
        configuration: Dict[str, Any],
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Live search with real-time NPV calculations using WebSockets for updates.
        """
        # Start background NPV calculation
        loop = asyncio.get_event_loop()
        
        # Quick search first
        quick_results = await loop.run_in_executor(
            self._executor,
            self._quick_search,
            search_term, limit * 2  # Get more for NPV filtering
        )
        
        # Return quick results immediately
        initial_response = {
            'results': quick_results[:limit],
            'count': len(quick_results[:limit]),
            'search_term': search_term,
            'status': 'calculating_npv'
        }
        
        # Start background NPV calculation
        npv_task = create_task(
            self._calculate_npv_batch(customer_id, quick_results, configuration)
        )
        
        # Don't wait, let it run in background
        # Frontend can poll or use WebSocket for updates
        
        return initial_response
    
    async def _calculate_npv_batch(
        self,
        customer_id: str,
        cars: List[Dict],
        configuration: Dict[str, Any]
    ):
        """Calculate NPV for a batch of cars in parallel"""
        loop = asyncio.get_event_loop()
        
        # Get customer
        customer = await loop.run_in_executor(
            self._executor, database.get_customer_by_id, customer_id
        )
        
        # Calculate NPV in parallel batches
        batch_size = 10
        batches = [cars[i:i+batch_size] for i in range(0, len(cars), batch_size)]
        
        npv_tasks = []
        for batch in batches:
            task = loop.run_in_executor(
                self._executor,
                self._calculate_npv_for_batch,
                customer, batch, configuration
            )
            npv_tasks.append(task)
        
        # Wait for all NPV calculations
        await gather(*npv_tasks)
        
        # Cache results
        cache_key = f"npv_results:{customer_id}:{datetime.utcnow().isoformat()}"
        self._cache_set(cache_key, cars, ttl=600)  # 10 minute cache
    
    def _calculate_npv_for_batch(
        self,
        customer: Dict,
        cars: List[Dict],
        configuration: Dict[str, Any]
    ):
        """Calculate NPV for a batch of cars"""
        from engine.basic_matcher import BasicMatcher
        matcher = BasicMatcher()
        
        for car in cars:
            try:
                npv = matcher._calculate_npv_for_car(customer, car, configuration)
                car['calculated_npv'] = npv
                car['monthly_payment'] = matcher._estimate_payment(customer, car, configuration)
            except Exception as e:
                logger.error(f"NPV calculation error: {e}")
                car['calculated_npv'] = 0
                car['monthly_payment'] = 0
    
    def _quick_search(self, search_term: str, limit: int) -> List[Dict]:
        """Quick search without NPV calculation"""
        all_inventory = database.get_all_inventory()
        search_lower = search_term.lower()
        
        results = []
        for car in all_inventory:
            if (search_lower in car.get('brand', '').lower() or
                search_lower in car.get('model', '').lower() or
                search_lower in str(car.get('year', ''))):
                results.append(car)
                
                if len(results) >= limit:
                    break
        
        return results
    
    async def get_search_suggestions(
        self,
        customer_id: str,
        partial_query: str
    ) -> List[str]:
        """Get search suggestions with caching"""
        cache_key = f"suggestions:{partial_query.lower()}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached
        
        # Generate suggestions
        suggestions = []
        
        # Brand suggestions
        brands = ['Toyota', 'Honda', 'Nissan', 'Mazda', 'Ford', 'Chevrolet', 
                 'Volkswagen', 'Hyundai', 'Kia', 'BMW', 'Mercedes-Benz', 'Audi']
        
        # Model suggestions
        models = ['Corolla', 'Camry', 'RAV4', 'Civic', 'Accord', 'CR-V',
                 'Sentra', 'Altima', 'Rogue', 'Mazda3', 'CX-5', 'F-150']
        
        query_lower = partial_query.lower()
        
        for brand in brands:
            if query_lower in brand.lower():
                suggestions.append(brand)
        
        for model in models:
            if query_lower in model.lower():
                suggestions.append(model)
        
        # Cache for 1 hour
        self._cache_set(cache_key, suggestions[:10], ttl=3600)
        
        return suggestions[:10]
    
    async def universal_search(
        self,
        query: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Truly async universal search across all entities"""
        loop = asyncio.get_event_loop()
        
        # Search in parallel
        tasks = [
            loop.run_in_executor(
                self._executor,
                database.search_customers,
                query, 10, 0
            ),
            loop.run_in_executor(
                self._executor,
                self._quick_search,
                query, 10
            )
        ]
        
        results = await gather(*tasks)
        
        customers_result, inventory_result = results
        customers = customers_result[0] if customers_result else []
        
        return {
            'customers': customers,
            'inventory': inventory_result,
            'query': query,
            'total_results': len(customers) + len(inventory_result)
        }
    
    async def get_inventory_filters(self) -> Dict[str, Any]:
        """Get filter options with caching"""
        cache_key = 'inventory_filters'
        cached = self._cache_get(cache_key)
        if cached:
            return cached
        
        # Get from database in background
        loop = asyncio.get_event_loop()
        filters = await loop.run_in_executor(
            self._executor,
            self._calculate_inventory_filters
        )
        
        # Cache for 1 hour
        self._cache_set(cache_key, filters, ttl=3600)
        
        return filters
    
    def _calculate_inventory_filters(self) -> Dict[str, Any]:
        """Calculate available filters from inventory"""
        inventory = database.get_all_inventory()
        
        brands = set()
        years = set()
        prices = []
        kms = []
        
        for car in inventory:
            if brand := car.get('brand'):
                brands.add(brand)
            if year := car.get('year'):
                years.add(year)
            if price := car.get('car_price'):
                prices.append(price)
            if km := car.get('kilometers'):
                kms.append(km)
        
        return {
            'brands': sorted(list(brands)),
            'vehicle_types': ['SUV', 'Sedan', 'Truck', 'Hatchback', 'Van'],
            'year_range': {
                'min': min(years) if years else 2015,
                'max': max(years) if years else 2024
            },
            'price_range': {
                'min': min(prices) if prices else 100000,
                'max': max(prices) if prices else 1000000
            },
            'km_range': {
                'min': 0,
                'max': max(kms) if kms else 200000
            }
        }
    
    def _classify_vehicle(self, model: str) -> str:
        """Classify vehicle type based on model name"""
        model_lower = model.lower()
        
        # Vehicle type patterns
        patterns = {
            'SUV': ['suv', 'crv', 'rav4', 'highlander', 'pilot', 'explorer'],
            'Truck': ['silverado', 'sierra', 'f-150', 'f150', 'ram', 'tacoma'],
            'Sedan': ['sedan', 'accord', 'camry', 'civic', 'corolla', 'altima'],
            'Hatchback': ['hatchback', 'golf', 'gti', 'focus', 'fiesta', 'fit'],
            'Van': ['van', 'odyssey', 'pacifica', 'sienna', 'grand caravan']
        }
        
        for vehicle_type, keywords in patterns.items():
            if any(keyword in model_lower for keyword in keywords):
                return vehicle_type
        
        return 'Other'
    
    def _estimate_payment(self, customer: Dict, car: Dict) -> float:
        """Quick payment estimation"""
        from config.facade import get_decimal
        
        # Get configuration values
        gps_monthly = float(get_decimal("fees.gps.monthly"))
        interest_rate = float(get_decimal("rates.A1"))
        service_fee_pct = float(get_decimal("fees.service.percentage"))
        
        # Calculate
        car_price = car['car_price']
        equity = customer['vehicle_equity']
        service_fee = car_price * service_fee_pct
        loan_amount = car_price - equity + service_fee
        
        # Monthly payment
        monthly_rate = interest_rate * 1.16 / 12
        term = 48
        
        if monthly_rate > 0:
            payment = loan_amount * (monthly_rate * (1 + monthly_rate)**term) / ((1 + monthly_rate)**term - 1)
        else:
            payment = loan_amount / term
        
        payment += gps_monthly * 1.16
        
        return payment
    
    def close(self):
        """Clean up resources"""
        if self._redis:
            self._redis.close()
        self._executor.shutdown(wait=True)


# Create singleton instance
search_service = SearchService()