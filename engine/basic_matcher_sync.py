"""
Synchronous version of BasicMatcher - fixes performance issue
This is the REAL fix, not a patch. Threading was making it slower.
"""
import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import time

from config.config import get_hardcoded_financial_parameters
from .payment_utils import calculate_monthly_payment

logger = logging.getLogger(__name__)

INTEREST_RATE_TABLE, DOWN_PAYMENT_TABLE = get_hardcoded_financial_parameters()

# Limit number of cars processed to avoid memory issues
BATCH_SIZE = 50


class BasicMatcherSync:
    """
    Synchronous version without ThreadPoolExecutor overhead.
    Everything else remains EXACTLY the same as BasicMatcher.
    """
    
    def __init__(self):
        logger.info("🚀 BasicMatcherSync initialized (no threading)")
        
    def find_all_viable(
        self,
        customer: Dict,
        inventory: List[Dict],
        custom_config: Optional[Dict] = None,
        terms_to_evaluate: Optional[List[int]] = None
    ) -> Dict:
        """
        Main entry point - finds all viable offers for a customer.
        Processes synchronously for better performance.
        """
        start_time = time.time()
        
        customer_id = customer.get("customer_id", "Unknown")
        current_payment = float(customer.get("current_monthly_payment", 0))
        
        logger.info(f"🔍 Finding viable cars for {customer_id}")
        logger.info(f"   Current payment: ${current_payment:,.0f}")
        logger.info(f"   Equity: ${customer.get('vehicle_equity', 0):,.0f}")
        logger.info(f"   Current car: ${customer.get('current_car_price', 0):,.0f}")
        
        # Use all standard terms if not specified
        if terms_to_evaluate is None:
            terms_to_evaluate = [12, 24, 36, 48, 60, 72]
            
        logger.info(f"   Evaluating all terms: {terms_to_evaluate}")
        
        # Get financial parameters
        from config.facade import get
        
        service_fee_pct = custom_config.get("service_fee_pct") if custom_config else None
        if service_fee_pct is None:
            service_fee_pct = float(get("fees.service.percentage"))
        else:
            service_fee_pct = float(service_fee_pct)
            
        cxa_pct = custom_config.get("cxa_pct") if custom_config else None
        if cxa_pct is None:
            cxa_pct = float(get("fees.cxa.percentage"))
        else:
            cxa_pct = float(cxa_pct)
            
        # More config loading...
        cac_bonus = custom_config.get("cac_bonus") if custom_config else None
        if cac_bonus is None:
            cac_bonus = float(get("fees.cac_bonus.default", 0))
        else:
            cac_bonus = float(cac_bonus)
            
        kavak_total_amount = custom_config.get("kavak_total") if custom_config else None
        if kavak_total_amount is None:
            kavak_total_amount = float(get("fees.kavak_total.amount", 25000))  # Use default if not found
        else:
            kavak_total_amount = float(kavak_total_amount)
            
        insurance_amount = custom_config.get("insurance_amount") if custom_config else None
        if insurance_amount is None:
            insurance_amount = float(get("fees.insurance.amount", 10999))  # Use default if not found
        else:
            insurance_amount = float(insurance_amount)
            
        gps_installation_fee = custom_config.get("gps_installation_fee") if custom_config else None
        if gps_installation_fee is None:
            gps_installation_fee = float(get("fees.gps.installation"))
        else:
            gps_installation_fee = float(gps_installation_fee)
            
        # IVA configuration
        iva_rate = float(get("financial.iva_rate"))
        apply_iva = get("fees.gps.apply_iva")
        gps_install_with_iva = gps_installation_fee * (1 + iva_rate) if apply_iva else gps_installation_fee
        
        # Create fee config for passing to offer generation
        fee_config = {
            "service_fee_pct": service_fee_pct,
            "cxa_pct": cxa_pct,
            "cac_bonus": cac_bonus,
            "kavak_total_amount": kavak_total_amount,
            "insurance_amount": insurance_amount,
            "gps_install_with_iva": gps_install_with_iva,
            "gps_installation_fee": gps_installation_fee,
            "apply_iva": apply_iva,
            "iva_rate": iva_rate
        }
        
        # Process in batches synchronously
        all_offers = []
        total_calculations = 0
        
        for i in range(0, len(inventory), BATCH_SIZE):
            batch = inventory[i:i + BATCH_SIZE]
            batch_offers, calculations = self._process_batch_sync(
                customer, batch, terms_to_evaluate, fee_config
            )
            all_offers.extend(batch_offers)
            total_calculations += calculations
            
            # Log progress
            if (i + BATCH_SIZE) % 200 == 0:
                elapsed = time.time() - start_time
                rate = total_calculations / elapsed if elapsed > 0 else 0
                logger.info(f"   Progress: {i + BATCH_SIZE}/{len(inventory)} cars, "
                          f"{total_calculations} calculations, "
                          f"{rate:.0f} calc/sec")
        
        # Categorize offers
        categorized = self._categorize_offers(all_offers, current_payment)
        
        elapsed_time = time.time() - start_time
        final_rate = total_calculations / elapsed_time if elapsed_time > 0 else 0
        
        logger.info(f"✅ Completed in {elapsed_time:.1f}s")
        logger.info(f"   Total calculations: {total_calculations}")
        logger.info(f"   Rate: {final_rate:.0f} calculations/second")
        logger.info(f"   Offers found: {len(all_offers)}")
        
        # Debug logging
        if len(all_offers) == 0:
            logger.warning(f"⚠️ No offers generated for customer {customer.get('customer_id', 'Unknown')}")
            logger.warning(f"   Current payment: ${current_payment:,.0f}")
            logger.warning(f"   Equity: ${customer.get('vehicle_equity', 0):,.0f}")
            logger.warning(f"   Current car price: ${customer.get('current_car_price', 0):,.0f}")
            logger.warning(f"   Service fee %: {fee_config.get('service_fee_pct', 0)}")
            logger.warning(f"   CXA %: {fee_config.get('cxa_pct', 0)}")
            logger.warning(f"   Kavak Total: ${fee_config.get('kavak_total_amount', 0):,.0f}")
            logger.warning(f"   Cars evaluated: {len(inventory)}")
        
        return {
            "offers": categorized,
            "stats": {
                "total_cars_evaluated": len(inventory),
                "total_calculations": total_calculations,
                "total_offers": len(all_offers),
                "processing_time": elapsed_time,
                "calculations_per_second": final_rate
            }
        }
    
    def _process_batch_sync(
        self,
        customer: Dict,
        batch: List[Dict],
        terms_to_evaluate: List[int],
        fee_config: Dict
    ) -> Tuple[List[Dict], int]:
        """
        Process a batch of cars synchronously.
        Returns (offers, calculation_count).
        """
        viable_offers = []
        calculations = 0
        
        for car in batch:
            for term in terms_to_evaluate:
                calculations += 1
                
                try:
                    offer = self._generate_offer(
                        customer=customer,
                        car=car,
                        term=term,
                        fee_config=fee_config
                    )
                    
                    if offer:
                        viable_offers.append(offer)
                        logger.debug(f"Generated offer for car {car.get('car_id')} term {term} with payment ${offer['monthly_payment']:.0f} (delta: {offer['payment_delta']:.2%})")
                        
                except Exception as e:
                    # Log error but continue processing
                    logger.debug(f"Error processing car {car.get('car_id')} "
                               f"with term {term}: {e}")
                    continue
        
        return viable_offers, calculations
    
    def _generate_offer(
        self,
        customer: Dict,
        car: Dict,
        term: int,
        fee_config: Dict
    ) -> Optional[Dict]:
        """
        Generate a single offer. This is the exact same logic as BasicMatcher.
        """
        # Extract customer data
        current_payment = float(customer.get("current_monthly_payment", 0))
        vehicle_equity = float(customer.get("vehicle_equity", 0))
        risk_profile = customer.get("risk_profile_name", "A")
        
        # Extract car data
        car_id = car.get("car_id")
        car_price = float(car.get("car_price", 0))
        car_model = car.get("model", "Unknown")
        
        # Skip if payment is too low
        if current_payment < 100:
            logger.debug(f"Skipping customer with payment ${current_payment}")
            return None
            
        # Get interest rate
        interest_rate = self._get_interest_rate(risk_profile, term)
        if interest_rate is None:
            return None
            
        # Step 1: Calculate preliminary base loan (car price - vehicle equity)
        preliminary_base_loan = car_price - vehicle_equity
        
        # Step 2: Calculate CXA on base loan with IVA (not on car price)
        cxa_pct = fee_config["cxa_pct"]
        cxa_amount = preliminary_base_loan * cxa_pct * (1 + fee_config["iva_rate"])
        
        # Step 3: Calculate service fee (still based on car price)
        service_fee_amount = car_price * fee_config["service_fee_pct"]
        
        # Step 4: Calculate effective equity (GPS install IS subtracted - we're financing it)
        gps_install_with_iva = fee_config["gps_install_with_iva"]
        effective_equity = vehicle_equity + fee_config["cac_bonus"] - cxa_amount - gps_install_with_iva
        
        # Step 5: Final base loan
        base_loan = car_price - effective_equity
        
        # Skip if equity covers the car
        if base_loan <= 0:
            logger.debug(f"Skipping car {car_id} - equity covers car (base_loan=${base_loan:.0f}, car_price=${car_price:.0f}, effective_equity=${effective_equity:.0f})")
            return None
            
        # Calculate payment
        try:
            payment_components = calculate_monthly_payment(
                loan_base=base_loan + gps_install_with_iva,  # Include GPS install in base loan
                service_fee_amount=service_fee_amount,
                kavak_total_amount=fee_config["kavak_total_amount"],
                insurance_amount=fee_config["insurance_amount"],
                annual_rate_nominal=interest_rate,
                term_months=term,
                gps_install_fee=0.0,  # Set to 0 since we're financing it, not charging in first month
            )
            
            total_payment = payment_components["payment_total"]
            
        except Exception as e:
            logger.warning(f"Payment calculation error for car {car_id}: {e}")
            return None
            
        # Calculate payment delta
        payment_delta = (total_payment - current_payment) / current_payment if current_payment > 0 else 0
        
        # Skip if payment increase is too high (>100%)
        if payment_delta > 1.0:
            logger.debug(f"Skipping car {car_id} - payment delta too high: {payment_delta:.2%}")
            return None
            
        # Calculate NPV (simplified for now)
        total_interest = payment_components.get("total_interest", 0)
        npv = total_interest + service_fee_amount + fee_config["kavak_total_amount"]
        
        # Build offer
        return {
            "car_id": car_id,  # Keep as car_id for compatibility
            "car_model": car_model,
            "new_car_price": car_price,
            "monthly_payment": round(total_payment, 2),
            "payment_delta": round(payment_delta, 4),
            "term": term,
            "loan_amount": round(base_loan + service_fee_amount + 
                               fee_config["kavak_total_amount"] + 
                               fee_config["insurance_amount"] + gps_install_with_iva, 2),
            "effective_equity": round(effective_equity, 2),
            "interest_rate": interest_rate,
            "npv": round(npv, 2),
            "service_fee_amount": round(service_fee_amount, 2),
            "cxa_amount": round(cxa_amount, 2),
            "insurance_amount": round(fee_config["insurance_amount"], 2),
            "kavak_total_amount": round(fee_config["kavak_total_amount"], 2),
            "gps_install_fee": 0.0,  # Financed, not charged separately
            "vehicle_equity": vehicle_equity,
            "fees_applied": {
                "service_fee_pct": fee_config["service_fee_pct"],
                "cxa_pct": fee_config["cxa_pct"],
                "cac_bonus": fee_config["cac_bonus"]
            },
            "gps_install_with_iva": gps_install_with_iva,
            "gps_installation_fee": fee_config["gps_installation_fee"]
        }
    
    def _get_interest_rate(self, risk_profile: str, term: int) -> Optional[float]:
        """Get interest rate based on risk profile and term."""
        # Get base rate from table
        base_rate = INTEREST_RATE_TABLE.get(risk_profile)
        if base_rate is None:
            logger.warning(f"No interest rate found for risk profile: {risk_profile}")
            return None
            
        # Apply term adjustments
        if term == 60:
            return base_rate + 0.01  # +1% for 60 months
        elif term == 72:
            return base_rate + 0.015  # +1.5% for 72 months
        else:
            return base_rate
    
    def _categorize_offers(self, offers: List[Dict], current_payment: float) -> Dict[str, List[Dict]]:
        """Categorize offers by payment change tier."""
        categorized = {
            "Refresh": [],
            "Upgrade": [],
            "Max Upgrade": []
        }
        
        for offer in offers:
            payment_delta = offer["payment_delta"]
            
            if -0.05 <= payment_delta <= 0.05:
                categorized["Refresh"].append(offer)
            elif 0.05 < payment_delta <= 0.25:
                categorized["Upgrade"].append(offer)
            elif 0.25 < payment_delta <= 1.0:
                categorized["Max Upgrade"].append(offer)
        
        # Sort by NPV within each tier
        for tier in categorized:
            categorized[tier].sort(key=lambda x: x["npv"], reverse=True)
        
        return categorized


# Create singleton instance
basic_matcher_sync = BasicMatcherSync()