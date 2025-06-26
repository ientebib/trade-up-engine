"""
Data validation for ensuring data integrity and reliability
"""
import pandas as pd
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from app.constants import (
    MIN_VALID_MONTHLY_PAYMENT, MAX_VALID_MONTHLY_PAYMENT,
    MIN_VALID_CAR_PRICE, MAX_VALID_CAR_PRICE,
    MAX_CURRENCY_AMOUNT
)

logger = logging.getLogger(__name__)


class DataIntegrityError(Exception):
    """Raised when data integrity checks fail"""
    pass


class DataValidator:
    """Validates data integrity throughout the application"""
    
    @staticmethod
    def validate_customer_data(customer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate customer data for integrity
        
        Args:
            customer: Customer data dictionary
            
        Returns:
            Validated customer data
            
        Raises:
            DataIntegrityError: If validation fails
        """
        required_fields = [
            'customer_id', 'name', 'current_monthly_payment',
            'vehicle_equity', 'outstanding_balance', 'risk_profile'
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in customer or customer[field] is None:
                raise DataIntegrityError(f"Customer missing required field: {field}")
        
        # Validate numeric fields
        numeric_fields = {
            'current_monthly_payment': (MIN_VALID_MONTHLY_PAYMENT, MAX_VALID_MONTHLY_PAYMENT),
            'vehicle_equity': (-MAX_CURRENCY_AMOUNT // 10, MAX_CURRENCY_AMOUNT),  # Can be negative
            'outstanding_balance': (0, MAX_CURRENCY_AMOUNT),
            'months_remaining': (0, 120)
        }
        
        for field, (min_val, max_val) in numeric_fields.items():
            if field in customer and customer[field] is not None:
                value = float(customer[field])
                if not (min_val <= value <= max_val):
                    logger.warning(
                        f"Customer {customer['customer_id']} has {field}={value} "
                        f"outside expected range [{min_val}, {max_val}]"
                    )
        
        # Validate risk profile
        valid_profiles = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3", "D", "E", "F", "ML"]
        if customer.get('risk_profile') not in valid_profiles:
            logger.warning(
                f"Customer {customer['customer_id']} has invalid risk profile: "
                f"{customer.get('risk_profile')}"
            )
        
        # Validate logical relationships
        if customer.get('outstanding_balance', 0) < 0:
            raise DataIntegrityError(
                f"Customer {customer['customer_id']} has negative outstanding balance"
            )
        
        return customer
    
    @staticmethod
    def validate_inventory_item(car: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate inventory item data
        
        Args:
            car: Car data dictionary
            
        Returns:
            Validated car data
            
        Raises:
            DataIntegrityError: If validation fails
        """
        required_fields = ['car_id', 'car_price', 'brand', 'model', 'year']
        
        # Check required fields
        for field in required_fields:
            if field not in car or car[field] is None:
                raise DataIntegrityError(f"Car missing required field: {field}")
        
        # Validate car_id is string
        car['car_id'] = str(car['car_id'])
        
        # Validate numeric fields
        if car.get('car_price', 0) <= 0:
            raise DataIntegrityError(
                f"Car {car['car_id']} has invalid price: {car.get('car_price')}"
            )
        
        if car.get('car_price', 0) > 10_000_000:
            logger.warning(f"Car {car['car_id']} has unusually high price: {car['car_price']}")
        
        # Validate year
        current_year = datetime.now().year
        car_year = int(car.get('year', 0))
        if not (1990 <= car_year <= current_year + 1):
            logger.warning(
                f"Car {car['car_id']} has unusual year: {car_year}"
            )
        
        return car
    
    @staticmethod
    def validate_offer(offer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate offer data for consistency
        
        Args:
            offer: Offer data dictionary
            
        Returns:
            Validated offer data
            
        Raises:
            DataIntegrityError: If validation fails
        """
        required_fields = [
            'car_id', 'customer_id', 'new_monthly_payment',
            'loan_amount', 'term', 'interest_rate', 'npv'
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in offer:
                raise DataIntegrityError(f"Offer missing required field: {field}")
        
        # Validate payment is positive
        if offer.get('new_monthly_payment', 0) <= 0:
            raise DataIntegrityError(
                f"Offer has invalid monthly payment: {offer.get('new_monthly_payment')}"
            )
        
        # Validate loan amount
        if offer.get('loan_amount', 0) <= 0:
            raise DataIntegrityError(
                f"Offer has invalid loan amount: {offer.get('loan_amount')}"
            )
        
        # Validate term
        valid_terms = [12, 24, 36, 48, 60, 72]
        if offer.get('term') not in valid_terms:
            raise DataIntegrityError(
                f"Offer has invalid term: {offer.get('term')}"
            )
        
        # Validate interest rate
        if not (0 < offer.get('interest_rate', 0) < 1):
            raise DataIntegrityError(
                f"Offer has invalid interest rate: {offer.get('interest_rate')}"
            )
        
        # Validate payment delta if present
        if 'payment_delta' in offer:
            delta = offer['payment_delta']
            if not (-1 <= delta <= 2):  # -100% to +200%
                logger.warning(
                    f"Offer has unusual payment delta: {delta:.2%}"
                )
        
        return offer
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame, df_type: str) -> pd.DataFrame:
        """
        Validate DataFrame integrity
        
        Args:
            df: DataFrame to validate
            df_type: Type of DataFrame ('customers' or 'inventory')
            
        Returns:
            Validated DataFrame
            
        Raises:
            DataIntegrityError: If validation fails
        """
        if df.empty:
            raise DataIntegrityError(f"Empty {df_type} DataFrame")
        
        # Check for required columns based on type
        if df_type == 'customers':
            required_cols = [
                'customer_id', 'name', 'current_monthly_payment',
                'vehicle_equity', 'outstanding_balance', 'risk_profile'
            ]
        elif df_type == 'inventory':
            required_cols = ['car_id', 'car_price', 'brand', 'model', 'year']
        else:
            raise ValueError(f"Unknown DataFrame type: {df_type}")
        
        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            raise DataIntegrityError(
                f"{df_type} DataFrame missing columns: {missing_cols}"
            )
        
        # Check for duplicate IDs
        id_col = 'customer_id' if df_type == 'customers' else 'car_id'
        duplicates = df[df.duplicated(subset=[id_col], keep=False)]
        if not duplicates.empty:
            dup_ids = duplicates[id_col].unique()[:5]  # Show first 5
            logger.warning(
                f"Found {len(duplicates)} duplicate {id_col}s in {df_type}: "
                f"{list(dup_ids)}..."
            )
        
        # Remove rows with null IDs
        null_ids = df[df[id_col].isna()]
        if not null_ids.empty:
            logger.warning(f"Removing {len(null_ids)} rows with null {id_col}")
            df = df[df[id_col].notna()]
        
        # Type conversions for safety
        if df_type == 'inventory':
            df['car_id'] = df['car_id'].astype(str)
        
        logger.info(f"Validated {df_type} DataFrame: {len(df)} rows")
        return df
    
    @staticmethod
    def validate_calculation_inputs(
        loan_amount: float,
        term: int,
        interest_rate: float,
        fees: Optional[Dict[str, float]] = None
    ) -> None:
        """
        Validate inputs for financial calculations
        
        Args:
            loan_amount: Loan principal
            term: Loan term in months
            interest_rate: Annual interest rate (decimal)
            fees: Optional fee dictionary
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate loan amount
        if loan_amount <= 0:
            raise ValueError(f"Loan amount must be positive: {loan_amount}")
        if loan_amount > 10_000_000:
            raise ValueError(f"Loan amount too large: {loan_amount}")
        
        # Validate term
        valid_terms = [12, 24, 36, 48, 60, 72]
        if term not in valid_terms:
            raise ValueError(f"Invalid term {term}. Must be one of: {valid_terms}")
        
        # Validate interest rate
        if not (0 < interest_rate < 1):
            raise ValueError(
                f"Interest rate must be between 0 and 1: {interest_rate}"
            )
        if interest_rate > 0.5:  # 50% APR
            logger.warning(f"Unusually high interest rate: {interest_rate:.2%}")
        
        # Validate fees if provided
        if fees:
            for fee_name, fee_value in fees.items():
                if fee_value < 0:
                    raise ValueError(f"Fee cannot be negative: {fee_name}={fee_value}")
                if fee_value > loan_amount:
                    logger.warning(
                        f"Fee {fee_name}={fee_value} exceeds loan amount {loan_amount}"
                    )
    
    @staticmethod
    def validate_amortization_schedule(
        schedule: List[Dict[str, Any]],
        loan_amount: float,
        term: int
    ) -> List[Dict[str, Any]]:
        """
        Validate amortization schedule for consistency
        
        Args:
            schedule: List of monthly payment dictionaries
            loan_amount: Original loan amount
            term: Expected term in months
            
        Returns:
            Validated schedule
            
        Raises:
            DataIntegrityError: If validation fails
        """
        if len(schedule) != term:
            raise DataIntegrityError(
                f"Schedule has {len(schedule)} months, expected {term}"
            )
        
        # Validate each month
        total_principal = 0
        for i, month in enumerate(schedule):
            # Check required fields
            required = ['month', 'capital', 'interest', 'payment', 'balance']
            for field in required:
                if field not in month:
                    raise DataIntegrityError(
                        f"Month {i+1} missing field: {field}"
                    )
            
            # Validate month number
            if month['month'] != i + 1:
                raise DataIntegrityError(
                    f"Invalid month number: {month['month']} (expected {i+1})"
                )
            
            # Accumulate principal
            total_principal += month.get('capital', 0)
            
            # Validate balance decreases
            if i > 0 and month['balance'] >= schedule[i-1]['balance']:
                logger.warning(
                    f"Balance not decreasing at month {i+1}: "
                    f"{month['balance']} >= {schedule[i-1]['balance']}"
                )
        
        # Final balance should be near zero
        final_balance = abs(schedule[-1]['balance'])
        if final_balance > 1:  # Allow $1 rounding error
            logger.warning(f"Final balance not zero: ${final_balance:.2f}")
        
        # Total principal should match loan amount (within rounding)
        principal_diff = abs(total_principal - loan_amount)
        if principal_diff > term:  # Allow $1 per month rounding
            logger.warning(
                f"Total principal ${total_principal:.2f} doesn't match "
                f"loan amount ${loan_amount:.2f}"
            )
        
        return schedule


# Convenience decorators for automatic validation
def validate_customer_input(func):
    """Decorator to validate customer data inputs"""
    def wrapper(*args, **kwargs):
        # Extract customer data from arguments
        if 'customer' in kwargs:
            kwargs['customer'] = DataValidator.validate_customer_data(kwargs['customer'])
        elif len(args) > 0 and isinstance(args[0], dict) and 'customer_id' in args[0]:
            args = (DataValidator.validate_customer_data(args[0]),) + args[1:]
        
        return func(*args, **kwargs)
    return wrapper


def validate_calculation_input(func):
    """Decorator to validate calculation inputs"""
    def wrapper(*args, **kwargs):
        # For functions that take offer_details dict
        if args and isinstance(args[0], dict):
            offer_details = args[0]
            # Extract values from offer_details
            loan_amount = offer_details.get('loan_amount', 0.0)
            term = offer_details.get('term', 0)
            interest_rate = offer_details.get('interest_rate', 0.0)
            
            # Validate if we have the required fields
            if loan_amount and term and interest_rate:
                DataValidator.validate_calculation_inputs(
                    loan_amount=float(loan_amount),
                    term=int(term),
                    interest_rate=float(interest_rate)
                )
        # For functions with keyword arguments
        elif 'loan_amount' in kwargs:
            DataValidator.validate_calculation_inputs(
                loan_amount=kwargs.get('loan_amount'),
                term=kwargs.get('term'),
                interest_rate=kwargs.get('interest_rate'),
                fees=kwargs.get('fees')
            )
        
        return func(*args, **kwargs)
    return wrapper