"""
Smart Search Engine - Intelligent offer optimization
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy_financial as npf
from config.config import (
    IVA_RATE, GPS_INSTALLATION_FEE, GPS_MONTHLY_FEE,
    INSURANCE_TABLE, DEFAULT_FEES, get_hardcoded_financial_parameters
)
from .basic_matcher import BasicMatcher
from .payment_utils import calculate_monthly_payment

logger = logging.getLogger(__name__)

# Load financial tables
INTEREST_RATE_TABLE, DOWN_PAYMENT_TABLE = get_hardcoded_financial_parameters()

@dataclass
class ConsiderationFilters:
    """Filters to create the consideration set"""
    # Basic filters
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    brands: Optional[List[str]] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    km_max: Optional[float] = None
    has_promotion: Optional[bool] = None
    regions: Optional[List[str]] = None
    vehicle_classes: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    
    # Smart filters based on customer history
    only_newer_than_current: bool = False  # Only cars newer than customer's current
    max_km_vs_current: Optional[float] = None  # Max KM relative to customer's car
    same_brand_preference: bool = False  # Prefer same brand as current car
    exclude_current_brand: bool = False  # Exclude current brand
    price_range_relative: Optional[float] = None  # e.g., 1.5 = up to 50% more expensive

@dataclass
class SubsidyConfig:
    """Configuration for subsidy search"""
    # Service fee range (descending from max to min)
    service_fee_max: float = 0.05  # 5%
    service_fee_min: float = 0.02  # 2%
    service_fee_step: float = 0.005  # 0.5%
    
    # CAC bonus range (ascending from min to max)
    cac_min: float = 0
    cac_max: float = 10000
    cac_step: float = 500
    
    # CXA range (descending from max to min)
    cxa_max: float = 0.04  # 4%
    cxa_min: float = 0.01  # 1%
    cxa_step: float = 0.005  # 0.5%
    
    # Fixed parameters
    kavak_total_enabled: bool = True
    kavak_total_amount: float = 25000

@dataclass
class OfferResult:
    """Result of smart search for a single car"""
    car_id: str
    car_model: str
    car_price: float
    viable: bool
    failure_reason: Optional[str] = None
    
    # Optimized parameters
    service_fee_pct: float = 0
    cac_bonus: float = 0
    cxa_pct: float = 0
    
    # Financial metrics
    monthly_payment: float = 0
    payment_delta: float = 0
    npv: float = 0
    term: int = 0
    
    # Audit trail
    iterations_tried: int = 0
    computation_time: float = 0


class SmartSearchEngine:
    """Intelligent search engine for optimal trade-up offers"""
    
    def __init__(self):
        self.basic_matcher = BasicMatcher()
    
    def filter_consideration_set(
        self, 
        inventory_df: pd.DataFrame, 
        filters: ConsiderationFilters,
        customer: Optional[Dict] = None
    ) -> pd.DataFrame:
        """Filter inventory to consideration set based on customer preferences"""
        filtered = inventory_df.copy()
        initial_count = len(filtered)
        
        # Price range filter
        if filters.price_min is not None:
            filtered = filtered[filtered['sales_price'] >= filters.price_min]
        if filters.price_max is not None:
            filtered = filtered[filtered['sales_price'] <= filters.price_max]
        
        # Extract brand from model and filter
        if filters.brands:
            # Extract first word as brand (works for most cases)
            filtered['brand'] = filtered['model'].str.split().str[0]
            filtered = filtered[filtered['brand'].isin(filters.brands)]
        
        # Extract year from model and filter
        if filters.year_min is not None or filters.year_max is not None:
            # Extract 4-digit year from model string
            filtered['year'] = filtered['model'].str.extract(r'(\d{4})')
            filtered['year'] = pd.to_numeric(filtered['year'], errors='coerce')
            
            if filters.year_min is not None:
                filtered = filtered[filtered['year'] >= filters.year_min]
            if filters.year_max is not None:
                filtered = filtered[filtered['year'] <= filters.year_max]
        
        # Kilometers filter
        if filters.km_max is not None:
            filtered = filtered[filtered['kilometers'] <= filters.km_max]
        
        # Promotion filter
        if filters.has_promotion is not None:
            filtered = filtered[filtered['has_promotion'] == filters.has_promotion]
        
        # Region filter
        if filters.regions:
            filtered = filtered[filtered['region'].isin(filters.regions)]
        
        # Color filter
        if filters.colors:
            filtered = filtered[filtered['color'].isin(filters.colors)]
        
        # Extract vehicle class from model (simplified)
        if filters.vehicle_classes:
            def classify_vehicle(model: str) -> str:
                model_lower = model.lower()
                if any(suv in model_lower for suv in ['x3', 'x5', 'q5', 'crv', 'rav4', 'tiguan']):
                    return 'SUV'
                elif any(sedan in model_lower for sedan in ['camry', 'accord', 'a4', 'serie 3', 'civic']):
                    return 'Sedan'
                elif any(truck in model_lower for truck in ['f150', 'silverado', 'ram']):
                    return 'Truck'
                elif any(hatch in model_lower for hatch in ['golf', 'mazda3', 'swift']):
                    return 'Hatchback'
                else:
                    return 'Other'
            
            filtered['vehicle_class'] = filtered['model'].apply(classify_vehicle)
            filtered = filtered[filtered['vehicle_class'].isin(filters.vehicle_classes)]
        
        # Smart filters based on customer history
        if customer:
            # Only newer than current car filter
            if filters.only_newer_than_current and customer.get('current_car_year'):
                current_year = customer['current_car_year']
                if 'year' not in filtered.columns:
                    filtered['year'] = filtered['model'].str.extract(r'(\d{4})')
                    filtered['year'] = pd.to_numeric(filtered['year'], errors='coerce')
                filtered = filtered[filtered['year'] > current_year]
            
            # Max KM relative to current car
            if filters.max_km_vs_current is not None and customer.get('current_car_km'):
                max_km = customer['current_car_km'] * filters.max_km_vs_current
                filtered = filtered[filtered['kilometers'] <= max_km]
            
            # Same brand preference
            if filters.same_brand_preference and customer.get('current_car_brand'):
                current_brand = customer['current_car_brand'].lower()
                if 'brand' not in filtered.columns:
                    filtered['brand'] = filtered['model'].str.split().str[0]
                filtered = filtered[filtered['brand'].str.lower() == current_brand]
            
            # Exclude current brand
            if filters.exclude_current_brand and customer.get('current_car_brand'):
                current_brand = customer['current_car_brand'].lower()
                if 'brand' not in filtered.columns:
                    filtered['brand'] = filtered['model'].str.split().str[0]
                filtered = filtered[filtered['brand'].str.lower() != current_brand]
            
            # Price range relative to current car
            if filters.price_range_relative and customer.get('current_car_price'):
                max_price = customer['current_car_price'] * filters.price_range_relative
                filtered = filtered[filtered['sales_price'] <= max_price]
        
        final_count = len(filtered)
        logger.info(f"🎯 Consideration set: {final_count}/{initial_count} cars "
                   f"({final_count/initial_count*100:.1f}% of inventory)")
        
        return filtered
    
    def solve_minimum_subsidy(
        self,
        customer: Dict,
        car: Dict,
        config: SubsidyConfig
    ) -> OfferResult:
        """Find minimum viable subsidy for a specific car using hierarchical search"""
        import time
        start_time = time.time()
        
        iterations = 0
        best_offer = None
        best_payment_delta = float('inf')
        
        # Get customer risk profile
        risk_profile = customer.get('risk_profile_name', 'A')
        risk_index = customer.get('risk_profile_index', 3)
        base_interest_rate = INTEREST_RATE_TABLE.get(risk_profile, 0.18)
        
        # Try each term in order
        for term in [48, 60, 36, 72]:
            # Hierarchical search: Service Fee -> CAC -> CXA
            service_fee = config.service_fee_max
            while service_fee >= config.service_fee_min:
                
                cac_bonus = config.cac_min
                while cac_bonus <= config.cac_max:
                    
                    cxa = config.cxa_max
                    while cxa >= config.cxa_min:
                        iterations += 1
                        
                        # Calculate offer with current parameters
                        fees_config = {
                            'service_fee_pct': service_fee,
                            'cxa_pct': cxa,
                            'cac_bonus': cac_bonus
                        }
                        
                        offer = self._calculate_single_offer(
                            customer, car, term, base_interest_rate,
                            risk_index, fees_config, config.kavak_total_enabled,
                            config.kavak_total_amount
                        )
                        
                        if offer:
                            payment_delta = offer['payment_delta']
                            
                            # Check if this is our best offer so far (closest to viable)
                            if abs(payment_delta) < abs(best_payment_delta):
                                best_payment_delta = payment_delta
                                best_offer = offer
                                best_offer['iterations'] = iterations
                            
                            # Check Hard Gates
                            gates_passed = self._check_hard_gates(offer, customer)
                            
                            if gates_passed['all_passed']:
                                # First viable offer found!
                                computation_time = time.time() - start_time
                                
                                return OfferResult(
                                    car_id=str(car['car_id']),
                                    car_model=car.get('model', 'Unknown'),
                                    car_price=car['sales_price'],
                                    viable=True,
                                    service_fee_pct=service_fee,
                                    cac_bonus=cac_bonus,
                                    cxa_pct=cxa,
                                    monthly_payment=offer['monthly_payment'],
                                    payment_delta=payment_delta,
                                    npv=offer['npv'],
                                    term=term,
                                    iterations_tried=iterations,
                                    computation_time=computation_time
                                )
                        
                        cxa -= config.cxa_step
                    
                    cac_bonus += config.cac_step
                
                service_fee -= config.service_fee_step
        
        # No viable offer found - return best attempt with failure reason
        computation_time = time.time() - start_time
        
        if best_offer:
            gates = self._check_hard_gates(best_offer, customer)
            failure_reason = gates['failure_reason']
        else:
            failure_reason = "No offers could be calculated"
        
        return OfferResult(
            car_id=str(car['car_id']),
            car_model=car.get('model', 'Unknown'),
            car_price=car['sales_price'],
            viable=False,
            failure_reason=failure_reason,
            service_fee_pct=config.service_fee_min if best_offer else 0,
            cac_bonus=config.cac_max if best_offer else 0,
            cxa_pct=config.cxa_min if best_offer else 0,
            monthly_payment=best_offer['monthly_payment'] if best_offer else 0,
            payment_delta=best_offer['payment_delta'] if best_offer else 0,
            npv=best_offer['npv'] if best_offer else 0,
            term=best_offer['term'] if best_offer else 0,
            iterations_tried=iterations,
            computation_time=computation_time
        )
    
    def _calculate_single_offer(
        self, customer: Dict, car: Dict, term: int,
        base_interest_rate: float, risk_index: int,
        fees_config: Dict, kavak_total_enabled: bool,
        kavak_total_amount: float
    ) -> Optional[Dict]:
        """Calculate a single offer with given parameters"""
        
        # Adjust interest rate by term
        if term == 60:
            interest_rate = base_interest_rate + 0.01
        elif term == 72:
            interest_rate = base_interest_rate + 0.015
        else:
            interest_rate = base_interest_rate
        
        # Apply IVA to interest rate
        interest_rate_with_iva = interest_rate * (1 + IVA_RATE)
        monthly_rate = interest_rate_with_iva / 12
        
        # Check down payment requirement
        if risk_index not in DOWN_PAYMENT_TABLE.index or term not in DOWN_PAYMENT_TABLE.columns:
            return None
        
        down_payment_pct = DOWN_PAYMENT_TABLE.loc[risk_index, term]
        down_payment_required = car['sales_price'] * down_payment_pct
        
        # Calculate fees
        service_fee_amount = car['sales_price'] * fees_config['service_fee_pct']
        cxa_amount = car['sales_price'] * fees_config['cxa_pct']
        cac_bonus = fees_config.get('cac_bonus', 0)
        
        # Use Kavak Total based on toggle
        if kavak_total_enabled:
            kavak_total = kavak_total_amount
        else:
            kavak_total = 0
        
        insurance_amount = INSURANCE_TABLE.get(customer.get('risk_profile_name', 'A'), 10999)
        
        # GPS fees with IVA
        gps_install_with_iva = GPS_INSTALLATION_FEE * (1 + IVA_RATE)
        gps_monthly_with_iva = GPS_MONTHLY_FEE * (1 + IVA_RATE)
        
        # Calculate effective equity
        effective_equity = (
            customer['vehicle_equity'] 
            + cac_bonus
            - cxa_amount 
            - gps_install_with_iva
        )
        
        # Check if down payment requirement is met
        if effective_equity < down_payment_required:
            return None
        
        # Calculate loan amounts
        base_loan = car['sales_price'] - effective_equity
        if base_loan <= 0:
            return None
        
        # Total financed amount
        total_financed = base_loan + service_fee_amount + kavak_total + insurance_amount
        
        # Calculate monthly payments
        payment_components = calculate_monthly_payment(
            loan_base=base_loan,
            service_fee_amount=service_fee_amount,
            kavak_total_amount=kavak_total,
            insurance_amount=insurance_amount,
            annual_rate_nominal=interest_rate,
            term_months=term,
            gps_install_fee=gps_install_with_iva,
        )

        total_monthly = payment_components["payment_total"]
        
        # Calculate payment delta
        payment_delta = (total_monthly / customer['current_monthly_payment']) - 1
        
        # Calculate NPV (simplified)
        margin = service_fee_amount + cxa_amount
        cost = 2000 + cac_bonus  # Include CAC in cost
        npv = margin - cost
        
        return {
            "car_id": car["car_id"],
            "car_model": car.get("model", "Unknown"),
            "new_car_price": car["sales_price"],
            "term": term,
            "monthly_payment": total_monthly,
            "payment_delta": payment_delta,
            "loan_amount": total_financed,
            "effective_equity": effective_equity,
            "cxa_amount": cxa_amount,
            "service_fee_amount": service_fee_amount,
            "cac_bonus": cac_bonus,
            "kavak_total_amount": kavak_total,
            "insurance_amount": insurance_amount,
            "gps_install_fee": gps_install_with_iva,
            "gps_monthly_fee": gps_monthly_with_iva,
            "gps_monthly_fee_base": GPS_MONTHLY_FEE,
            "gps_monthly_fee_iva": GPS_MONTHLY_FEE * IVA_RATE,
            "iva_on_interest": payment_components["iva_on_interest"],
            "npv": npv,
            "interest_rate": interest_rate
        }
    
    def _check_hard_gates(self, offer: Dict, customer: Dict) -> Dict:
        """Check if offer passes all hard gates"""
        gates = {
            'all_passed': True,
            'failure_reason': None,
            'gates': {}
        }
        
        # Gate 1: Payment Delta (must be within acceptable range)
        payment_delta = offer['payment_delta']
        if payment_delta > 1.0:  # More than 100% increase
            gates['all_passed'] = False
            gates['failure_reason'] = f"Payment_Delta_Too_High ({payment_delta:.1%})"
            gates['gates']['payment_delta'] = False
        else:
            gates['gates']['payment_delta'] = True
        
        # Gate 2: Minimum NPV
        min_npv = 5000  # Could be configurable
        if offer['npv'] < min_npv:
            gates['all_passed'] = False
            if not gates['failure_reason']:
                gates['failure_reason'] = f"NPV_Below_Minimum (${offer['npv']:,.0f})"
            gates['gates']['npv'] = False
        else:
            gates['gates']['npv'] = True
        
        # Gate 3: Loan-to-Value ratio (example additional gate)
        ltv = offer['loan_amount'] / offer['new_car_price']
        max_ltv = 0.9  # 90% max financing
        if ltv > max_ltv:
            gates['all_passed'] = False
            if not gates['failure_reason']:
                gates['failure_reason'] = f"LTV_Too_High ({ltv:.1%})"
            gates['gates']['ltv'] = False
        else:
            gates['gates']['ltv'] = True
        
        return gates
    
    def search_smart_offers(
        self,
        customer: Dict,
        inventory_df: pd.DataFrame,
        filters: ConsiderationFilters,
        config: SubsidyConfig,
        max_results: int = 10
    ) -> Dict:
        """Main entry point for smart search"""
        import time
        start_time = time.time()
        
        # Step 1: Filter to consideration set
        candidate_cars = self.filter_consideration_set(inventory_df, filters, customer)
        
        if candidate_cars.empty:
            return {
                "status": "no_candidates",
                "message": "No cars match the specified filters",
                "filters_used": filters.__dict__,
                "processing_time": time.time() - start_time
            }
        
        logger.info(f"🔍 Analyzing {len(candidate_cars)} candidate cars...")
        
        # Step 2: Find minimum viable subsidy for each car
        results = []
        viable_count = 0
        
        for _, car in candidate_cars.iterrows():
            car_dict = car.to_dict()
            result = self.solve_minimum_subsidy(customer, car_dict, config)
            results.append(result)
            
            if result.viable:
                viable_count += 1
                
            # Stop if we have enough viable offers
            if viable_count >= max_results:
                break
        
        # Sort results: viable first (by NPV), then non-viable (by how close they got)
        viable_offers = [r for r in results if r.viable]
        failed_offers = [r for r in results if not r.viable]
        
        viable_offers.sort(key=lambda x: x.npv, reverse=True)
        failed_offers.sort(key=lambda x: abs(x.payment_delta))
        
        total_time = time.time() - start_time
        
        return {
            "status": "success",
            "viable_offers": viable_offers[:max_results],
            "failed_attempts": failed_offers[:5],  # Show top 5 near-misses
            "statistics": {
                "total_candidates": len(candidate_cars),
                "total_analyzed": len(results),
                "viable_found": viable_count,
                "success_rate": viable_count / len(results) if results else 0,
                "avg_iterations_per_car": sum(r.iterations_tried for r in results) / len(results) if results else 0,
                "total_iterations": sum(r.iterations_tried for r in results),
                "processing_time": total_time
            },
            "filters_used": filters.__dict__,
            "config_used": config.__dict__
        }


# Singleton instance
smart_search_engine = SmartSearchEngine()