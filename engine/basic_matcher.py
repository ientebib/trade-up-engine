import logging
from typing import Dict, List, Optional
import time
import numpy_financial as npf
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

from app.constants import (
    REFRESH_TIER_MIN, REFRESH_TIER_MAX,
    UPGRADE_TIER_MIN, UPGRADE_TIER_MAX,
    MAX_UPGRADE_TIER_MIN, MAX_UPGRADE_TIER_MAX,
    TERM_60_RATE_ADJUSTMENT, TERM_72_RATE_ADJUSTMENT,
    NPV_BASE_MARGIN_DEDUCTION,
    DEFAULT_SERVICE_FEE_PCT, DEFAULT_CXA_PCT, DEFAULT_CAC_BONUS,
    KAVAK_TOTAL_DEFAULT_AMOUNT,
    VALID_LOAN_TERMS
)
from config.config import (
    get_hardcoded_financial_parameters, 
    PAYMENT_DELTA_TIERS,
    IVA_RATE,
    GPS_INSTALLATION_FEE,
    GPS_MONTHLY_FEE,
    DEFAULT_FEES,
    INSURANCE_TABLE
)
from .payment_utils import calculate_monthly_payment

logger = logging.getLogger(__name__)

INTEREST_RATE_TABLE, DOWN_PAYMENT_TABLE = get_hardcoded_financial_parameters()

class BasicMatcher:
    """
    Core engine for generating vehicle trade-up offers.
    
    The BasicMatcher evaluates customer financial profiles against available
    inventory to generate viable loan offers. It handles complex financial
    calculations including interest rates, fees, insurance, and payment
    structuring while ensuring regulatory compliance.
    
    Key Features:
        - Parallel processing for performance at scale
        - Configurable fee structures and business rules
        - Risk-based interest rate and down payment calculation
        - Multi-term loan evaluation (12-72 months)
        - Offer categorization by payment change tiers
        - NPV-based profitability analysis
    
    Business Context:
        This is the heart of Kavak's trade-up business model, enabling
        customers to upgrade their vehicles with minimal payment increases
        while ensuring profitable transactions for the company.
    """
    
    def __init__(self):
        self.cpu_count = multiprocessing.cpu_count()
        self.executor = ThreadPoolExecutor(max_workers=self.cpu_count)
        logger.info(f"🚀 BasicMatcher initialized with {self.cpu_count} workers")
        
    def __del__(self):
        """Clean up thread pool on destruction"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
    
    def find_all_viable(self, customer: Dict, inventory: List[Dict], custom_fees: Optional[Dict] = None) -> Dict:
        """
        Find all viable vehicle trade-up offers for a customer.
        
        This method evaluates all inventory items that cost more than the customer's
        current vehicle and generates loan offers across multiple terms. Each offer
        is categorized into tiers based on payment change percentage.
        
        Args:
            customer (Dict): Customer data containing:
                - customer_id: Unique identifier
                - current_monthly_payment: Current loan payment (MXN)
                - vehicle_equity: Current vehicle equity (MXN)
                - current_car_price: Current vehicle value (MXN)
                - risk_profile_name: Credit risk profile (e.g., 'A1', 'B2')
                - risk_profile_index: Numeric risk index for rate lookup
                
            inventory (List[Dict]): List of available vehicles, each containing:
                - car_id: Unique vehicle identifier
                - model: Vehicle model name
                - sales_price: Vehicle sale price (MXN)
                
            custom_fees (Optional[Dict]): Override default fee structure:
                - service_fee_pct: Service fee percentage (default: 4%)
                - cxa_pct: CXA opening fee percentage (default: 4%)
                - cac_bonus: CAC bonus amount (default: 0)
                - kavak_total_amount: Kavak Total insurance (default: 25000)
                - interest_rate: Override base interest rate
                - gps_installation_fee: GPS installation cost
                - gps_monthly_fee: GPS monthly cost
                - insurance_amount: Insurance amount override
        
        Returns:
            Dict: Organized offers by tier:
                {
                    "Refresh": [offers with -5% to +5% payment change],
                    "Upgrade": [offers with +5% to +25% payment change],
                    "Max Upgrade": [offers with +25% to +100% payment change],
                    "total_offers": int,
                    "total_cars_evaluated": int,
                    "processing_time": float,
                    "message": str
                }
        
        Note:
            - Only considers vehicles more expensive than customer's current car
            - Evaluates multiple loan terms (12, 24, 36, 48, 60, 72 months)
            - Uses parallel processing for performance
            - Interest rates adjusted based on term length
            - All prices include IVA (16% tax) where applicable
        """
        start_time = time.time()
        
        if custom_fees:
            fees = custom_fees
        else:
            fees = {
                'service_fee_pct': DEFAULT_SERVICE_FEE_PCT,
                'cxa_pct': DEFAULT_CXA_PCT,
                'cac_bonus': DEFAULT_CAC_BONUS
            }
        
        risk_profile = customer.get('risk_profile_name', 'A')
        risk_index = customer.get('risk_profile_index', 3)
        
        if custom_fees and 'interest_rate' in custom_fees and custom_fees['interest_rate'] is not None:
            ir = custom_fees['interest_rate']
            # Accept either decimal (0.25) or percentage (25)
            if ir > 1:  # Treat values >1 as percentage inputs
                ir = ir / 100.0
            base_interest_rate = ir
        else:
            base_interest_rate = INTEREST_RATE_TABLE.get(risk_profile, 0.18)
        
        logger.info(f"🔍 Finding viable cars for {customer['customer_id']}")
        logger.info(f"   Current payment: ${customer['current_monthly_payment']:,.0f}")
        logger.info(f"   Equity: ${customer['vehicle_equity']:,.0f}")
        logger.info(f"   Current car: ${customer['current_car_price']:,.0f}")
        
        offers = []
        cars_tested = 0
        
        eligible_cars = [car for car in inventory if car['car_price'] > customer['current_car_price']]
        cars_tested = len(eligible_cars)
        
        tasks = []
        for car in eligible_cars:
            for term in VALID_LOAN_TERMS:
                task = self.executor.submit(
                    self._generate_offer,
                    customer=customer,
                    car=car,
                    term=term,
                    base_interest_rate=base_interest_rate,
                    risk_index=risk_index,
                    fees_config=fees
                )
                tasks.append(task)
        
        for future in as_completed(tasks):
            try:
                offer = future.result()
                if offer:
                    offers.append(offer)
            except Exception as e:
                if len(offers) < 10:
                    logger.warning(f"Error generating offer: {e}")
                continue
        
        organized = {
            "Refresh": [],
            "Upgrade": [],
            "Max Upgrade": []
        }
        
        for offer in offers:
            delta = offer.get('payment_delta', 0)
            if REFRESH_TIER_MIN <= delta <= REFRESH_TIER_MAX:
                organized["Refresh"].append(offer)
            elif UPGRADE_TIER_MIN < delta <= UPGRADE_TIER_MAX:
                organized["Upgrade"].append(offer)
            elif MAX_UPGRADE_TIER_MIN < delta <= MAX_UPGRADE_TIER_MAX:
                organized["Max Upgrade"].append(offer)
        
        for tier in organized:
            if organized[tier]:
                npvs = np.array([offer.get('npv', 0) for offer in organized[tier]])
                sorted_indices = np.argsort(npvs)[::-1]
                organized[tier] = [organized[tier][i] for i in sorted_indices]
        
        total = sum(len(tier) for tier in organized.values())
        
        logger.info(f"✅ Found {total} viable offers from {cars_tested} cars tested")
        logger.info(f"   Refresh: {len(organized['Refresh'])}")
        logger.info(f"   Upgrade: {len(organized['Upgrade'])}")
        logger.info(f"   Max Upgrade: {len(organized['Max Upgrade'])}")
        
        return {
            "offers": organized,
            "total_offers": total,
            "cars_tested": cars_tested,
            "processing_time": round(time.time() - start_time, 2),
            "fees_used": fees,
            "message": f"Showing all viable offers with {'custom' if custom_fees else 'standard'} fees"
        }
    
    def _generate_offer(self, customer: Dict, car: Dict, term: int, 
                       base_interest_rate: float, risk_index: int, 
                       fees_config: Dict) -> Optional[Dict]:
        """
        Generate a single loan offer for a specific customer-car-term combination.
        
        This method performs the core financial calculations for a trade-up offer,
        including loan structuring, payment calculation, and profitability analysis.
        
        Args:
            customer (Dict): Customer financial data
            car (Dict): Vehicle data including price and specifications
            term (int): Loan term in months (12, 24, 36, 48, 60, 72)
            base_interest_rate (float): Base annual interest rate (before adjustments)
            risk_index (int): Customer risk profile index for down payment lookup
            fees_config (Dict): Fee configuration including service fees, GPS, etc.
        
        Returns:
            Optional[Dict]: Complete offer details if viable, None if not feasible:
                {
                    "car_id": str,
                    "car_model": str,
                    "new_car_price": float,
                    "term": int,
                    "monthly_payment": float,
                    "payment_delta": float,  # Percentage change from current payment
                    "loan_amount": float,    # Total financed amount
                    "effective_equity": float,
                    "cxa_amount": float,     # Opening fee
                    "service_fee_amount": float,
                    "kavak_total_amount": float,
                    "insurance_amount": float,
                    "gps_install_fee": float,
                    "gps_monthly_fee": float,
                    "iva_on_interest": float,
                    "npv": float,            # Net present value for profitability
                    "interest_rate": float
                }
        
        Business Logic:
            1. Adjust interest rate based on term (60mo: +1%, 72mo: +1.5%)
            2. Calculate required down payment from risk profile table
            3. Compute effective equity (current equity + bonuses - fees)
            4. Verify customer can afford down payment
            5. Structure loan with service fees, insurance, Kavak Total
            6. Calculate monthly payment including GPS and IVA
            7. Evaluate profitability (NPV calculation)
        
        Returns None if:
            - Customer lacks sufficient equity for down payment
            - Loan amount would be zero or negative
            - Risk profile or term not found in lookup tables
        """
        
        if term == 60:
            interest_rate = base_interest_rate + TERM_60_RATE_ADJUSTMENT
        elif term == 72:
            interest_rate = base_interest_rate + TERM_72_RATE_ADJUSTMENT
        else:
            interest_rate = base_interest_rate
        
        interest_rate_with_iva = interest_rate * IVA_RATE
        monthly_rate = interest_rate_with_iva / 12
        
        if risk_index not in DOWN_PAYMENT_TABLE.index or term not in DOWN_PAYMENT_TABLE.columns:
            return None
            
        down_payment_pct = DOWN_PAYMENT_TABLE.loc[risk_index, term]
        down_payment_required = car['car_price'] * down_payment_pct
        
        service_fee_amount = car['car_price'] * fees_config['service_fee_pct']
        cxa_amount = car['car_price'] * fees_config['cxa_pct']
        cac_bonus = fees_config.get('cac_bonus', 0)
        kavak_total_amount = fees_config.get('kavak_total_amount', KAVAK_TOTAL_DEFAULT_AMOUNT)
        if 'insurance_amount' in fees_config and fees_config['insurance_amount'] is not None:
            insurance_amount = fees_config['insurance_amount']
        else:
            insurance_amount = INSURANCE_TABLE.get(customer.get('risk_profile_name', 'A'), 10999)
        
        gps_install_fee = fees_config.get('gps_installation_fee', GPS_INSTALLATION_FEE)
        gps_monthly_fee = fees_config.get('gps_monthly_fee', GPS_MONTHLY_FEE)
        gps_install_with_iva = gps_install_fee * (1 + IVA_RATE)
        gps_monthly_with_iva = gps_monthly_fee * (1 + IVA_RATE)
        
        effective_equity = (
            customer['vehicle_equity'] 
            + cac_bonus
            - cxa_amount 
            - gps_install_with_iva
        )
        
        if effective_equity < down_payment_required:
            return None
        
        base_loan = car['car_price'] - effective_equity
        if base_loan <= 0:
            return None
            
        total_financed = base_loan + service_fee_amount + kavak_total_amount + insurance_amount
        
        payment_components = calculate_monthly_payment(
            loan_base=base_loan,
            service_fee_amount=service_fee_amount,
            kavak_total_amount=kavak_total_amount,
            insurance_amount=insurance_amount,
            annual_rate_nominal=interest_rate,
            term_months=term,
            gps_install_fee=gps_install_with_iva,
        )

        total_monthly = payment_components["payment_total"]
        
        payment_delta = (total_monthly / customer['current_monthly_payment']) - 1
        
        margin = service_fee_amount + cxa_amount
        npv = margin - NPV_BASE_MARGIN_DEDUCTION
        
        return {
            "customer_id": customer["customer_id"],
            "car_id": car["car_id"],
            "car_model": car.get("model", "Unknown"),
            "new_car_price": car["car_price"],
            "term": term,
            "monthly_payment": total_monthly,
            "new_monthly_payment": total_monthly,
            "payment_delta": payment_delta,
            "loan_amount": total_financed,
            "effective_equity": effective_equity,
            "cxa_amount": cxa_amount,
            "service_fee_amount": service_fee_amount,
            "kavak_total_amount": kavak_total_amount,
            "insurance_amount": insurance_amount,
            "gps_install_fee": gps_install_with_iva,
            "gps_monthly_fee": gps_monthly_with_iva,
            "gps_monthly_fee_base": gps_monthly_fee,
            "gps_monthly_fee_iva": gps_monthly_fee * IVA_RATE,
            "iva_on_interest": payment_components["iva_on_interest"],
            "npv": npv,
            "interest_rate": interest_rate
        }

basic_matcher = BasicMatcher()