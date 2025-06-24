import logging
from typing import Dict, List, Optional
import time
import numpy_financial as npf
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from config import (
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
    
    def __init__(self):
        self.cpu_count = multiprocessing.cpu_count()
        self.executor = ThreadPoolExecutor(max_workers=self.cpu_count)
        logger.info(f"🚀 BasicMatcher initialized with {self.cpu_count} workers")
    
    def find_all_viable(self, customer: Dict, inventory: List[Dict], custom_fees: Optional[Dict] = None) -> Dict:
        """Find ALL viable offers with standard or custom fees"""
        start_time = time.time()
        
        if custom_fees:
            fees = custom_fees
        else:
            fees = {
                'service_fee_pct': 0.04,  # 4% base value
                'cxa_pct': 0.04,          # 4% opening fee
                'cac_bonus': 0            # No bonus
            }
        
        risk_profile = customer.get('risk_profile_name', 'A')
        risk_index = customer.get('risk_profile_index', 3)
        
        if custom_fees and 'interest_rate' in custom_fees and custom_fees['interest_rate'] is not None:
            base_interest_rate = custom_fees['interest_rate']
        else:
            base_interest_rate = INTEREST_RATE_TABLE.get(risk_profile, 0.18)
        
        logger.info(f"🔍 Finding viable cars for {customer['customer_id']}")
        logger.info(f"   Current payment: ${customer['current_monthly_payment']:,.0f}")
        logger.info(f"   Equity: ${customer['vehicle_equity']:,.0f}")
        logger.info(f"   Current car: ${customer['current_car_price']:,.0f}")
        
        offers = []
        cars_tested = 0
        
        eligible_cars = [car for car in inventory if car['sales_price'] > customer['current_car_price']]
        cars_tested = len(eligible_cars)
        
        tasks = []
        for car in eligible_cars:
            for term in [48, 60, 36, 72]:
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
            if -0.05 <= delta <= 0.05:
                organized["Refresh"].append(offer)
            elif 0.05 < delta <= 0.25:
                organized["Upgrade"].append(offer)
            elif 0.25 < delta <= 1.0:
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
                       fees_config: Dict) -> Dict:
        
        if term == 60:
            interest_rate = base_interest_rate + 0.01
        elif term == 72:
            interest_rate = base_interest_rate + 0.015
        else:
            interest_rate = base_interest_rate
        
        interest_rate_with_iva = interest_rate * IVA_RATE
        monthly_rate = interest_rate_with_iva / 12
        
        if risk_index not in DOWN_PAYMENT_TABLE.index or term not in DOWN_PAYMENT_TABLE.columns:
            return None
            
        down_payment_pct = DOWN_PAYMENT_TABLE.loc[risk_index, term]
        down_payment_required = car['sales_price'] * down_payment_pct
        
        service_fee_amount = car['sales_price'] * fees_config['service_fee_pct']
        cxa_amount = car['sales_price'] * fees_config['cxa_pct']
        cac_bonus = fees_config.get('cac_bonus', 0)
        kavak_total_amount = fees_config.get('kavak_total_amount', DEFAULT_FEES['kavak_total_amount'])
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
        
        base_loan = car['sales_price'] - effective_equity
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
        npv = margin - 2000
        
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