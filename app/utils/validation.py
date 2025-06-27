"""
Unified validation module for input validation and data integrity

Consolidates validation logic from validators.py and data_validator.py
to provide a single, consistent validation interface.
"""
from typing import Optional, Tuple, Dict, Any, List, Union
from datetime import datetime
from decimal import Decimal
import re
import logging
import pandas as pd

from app.constants import (
    # Pagination
    MAX_PAGE_NUMBER, MAX_ITEMS_PER_PAGE, DEFAULT_ITEMS_PER_PAGE,
    # Request limits
    MAX_BULK_REQUEST_SIZE, MAX_CURRENCY_AMOUNT, MIN_CURRENCY_AMOUNT,
    # String limits
    MAX_CUSTOMER_ID_LENGTH, MAX_SEARCH_TERM_LENGTH,
    # Data validation
    MIN_VALID_MONTHLY_PAYMENT, MAX_VALID_MONTHLY_PAYMENT,
    MIN_VALID_CAR_PRICE, MAX_VALID_CAR_PRICE,
    VALID_LOAN_TERMS
)

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Base validation error with field information"""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"{field}: {message}")


class DataIntegrityError(ValidationError):
    """Specific error for data integrity violations"""
    pass


class UnifiedValidator:
    """
    Unified validator combining input validation and data integrity checks
    
    This class consolidates all validation logic to ensure consistency
    and avoid duplication across the codebase.
    """
    
    # Risk profiles allowed in the system
    VALID_RISK_PROFILES = {
        'AAA', 'AA', 'A', 'A1', 'A2', 
        'B', 'B1', 'B2', 
        'C', 'C1', 'C2', 'C3',
        'D', 'E', 'F', 'G', 'X', 'Y', 'Z'
    }
    
    # Valid regions
    VALID_REGIONS = {
        'CDMX', 'GDL', 'MTY', 'QRO', 'PUE', 'TIJ', 'MER', 'CUN',
        'AGS', 'SLP', 'LEO', 'CJS', 'CUL', 'HMO', 'TLC', 'VER'
    }
    
    # ====================
    # Input Validation
    # ====================
    
    @classmethod
    def validate_pagination(cls, page: int, limit: int) -> Tuple[int, int]:
        """Validate pagination parameters"""
        if page < 1:
            raise ValidationError("page", "Page number must be at least 1", page)
        if page > MAX_PAGE_NUMBER:
            raise ValidationError("page", f"Page number cannot exceed {MAX_PAGE_NUMBER}", page)
        
        if limit < 1:
            raise ValidationError("limit", "Limit must be at least 1", limit)
        if limit > MAX_ITEMS_PER_PAGE:
            raise ValidationError("limit", f"Limit cannot exceed {MAX_ITEMS_PER_PAGE}", limit)
        
        return page, limit
    
    @classmethod
    def validate_customer_id(cls, customer_id: str) -> str:
        """Validate customer ID format"""
        if not customer_id:
            raise ValidationError("customer_id", "Customer ID is required")
        
        if len(customer_id) > MAX_CUSTOMER_ID_LENGTH:
            raise ValidationError(
                "customer_id", 
                f"Customer ID cannot exceed {MAX_CUSTOMER_ID_LENGTH} characters",
                customer_id
            )
        
        # Basic format check (alphanumeric with possible dashes/underscores)
        if not re.match(r'^[A-Za-z0-9_-]+$', customer_id):
            raise ValidationError(
                "customer_id",
                "Customer ID must contain only alphanumeric characters, dashes, or underscores",
                customer_id
            )
        
        return customer_id
    
    @classmethod
    def validate_search_term(cls, search_term: str) -> str:
        """Validate search term"""
        if not search_term:
            raise ValidationError("search_term", "Search term cannot be empty")
        
        if len(search_term) > MAX_SEARCH_TERM_LENGTH:
            raise ValidationError(
                "search_term",
                f"Search term cannot exceed {MAX_SEARCH_TERM_LENGTH} characters",
                search_term
            )
        
        # Remove potentially dangerous characters
        cleaned = re.sub(r'[<>\"\'%;()&+]', '', search_term)
        
        return cleaned.strip()
    
    @classmethod
    def validate_currency_amount(cls, amount: Union[float, Decimal], field_name: str = "amount") -> float:
        """Validate currency amount"""
        try:
            amount_float = float(amount)
        except (TypeError, ValueError):
            raise ValidationError(field_name, "Must be a valid number", amount)
        
        if amount_float < MIN_CURRENCY_AMOUNT:
            raise ValidationError(
                field_name,
                f"Amount cannot be negative",
                amount
            )
        
        if amount_float > MAX_CURRENCY_AMOUNT:
            raise ValidationError(
                field_name,
                f"Amount cannot exceed {MAX_CURRENCY_AMOUNT:,.0f}",
                amount
            )
        
        return amount_float
    
    @classmethod
    def validate_percentage(cls, percentage: float, field_name: str = "percentage") -> float:
        """Validate percentage value (0-1 or 0-100)"""
        if percentage < 0:
            raise ValidationError(field_name, "Percentage cannot be negative", percentage)
        
        # Handle both decimal (0.05) and percentage (5) formats
        if percentage > 1 and percentage <= 100:
            # Convert percentage to decimal
            return percentage / 100
        elif percentage > 100:
            raise ValidationError(field_name, "Percentage cannot exceed 100%", percentage)
        
        return percentage
    
    @classmethod
    def validate_loan_term(cls, term: int) -> int:
        """Validate loan term"""
        if term not in VALID_LOAN_TERMS:
            raise ValidationError(
                "term",
                f"Loan term must be one of: {', '.join(map(str, VALID_LOAN_TERMS))}",
                term
            )
        return term
    
    @classmethod
    def validate_bulk_request(cls, items: List[Any], item_name: str = "items") -> List[Any]:
        """Validate bulk request size"""
        if not items:
            raise ValidationError(item_name, "At least one item is required")
        
        if len(items) > MAX_BULK_REQUEST_SIZE:
            raise ValidationError(
                item_name,
                f"Bulk request cannot exceed {MAX_BULK_REQUEST_SIZE} items",
                len(items)
            )
        
        return items
    
    # ====================
    # Data Integrity
    # ====================
    
    @classmethod
    def validate_customer_data(cls, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Validate customer data integrity"""
        errors = []
        
        # Required fields
        required_fields = [
            'customer_id', 'current_monthly_payment', 'vehicle_equity',
            'current_car_price', 'outstanding_balance', 'risk_profile_name'
        ]
        
        for field in required_fields:
            if field not in customer or customer[field] is None:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            raise DataIntegrityError("customer", "; ".join(errors), customer)
        
        # Validate specific fields
        try:
            cls.validate_customer_id(customer['customer_id'])
        except ValidationError as e:
            errors.append(str(e))
        
        # Validate risk profile
        if customer.get('risk_profile_name') not in cls.VALID_RISK_PROFILES:
            errors.append(f"Invalid risk profile: {customer.get('risk_profile_name')}")
        
        # Validate numeric fields
        numeric_validations = [
            ('current_monthly_payment', MIN_VALID_MONTHLY_PAYMENT, MAX_VALID_MONTHLY_PAYMENT),
            ('current_car_price', MIN_VALID_CAR_PRICE, MAX_VALID_CAR_PRICE),
            ('vehicle_equity', -MAX_CURRENCY_AMOUNT, MAX_CURRENCY_AMOUNT),  # Can be negative
            ('outstanding_balance', 0, MAX_CURRENCY_AMOUNT)
        ]
        
        for field, min_val, max_val in numeric_validations:
            value = customer.get(field, 0)
            try:
                value_float = float(value)
                if value_float < min_val or value_float > max_val:
                    errors.append(f"{field} out of range: {value} (expected {min_val}-{max_val})")
            except (TypeError, ValueError):
                errors.append(f"{field} must be numeric: {value}")
        
        # Logical validations
        if customer.get('outstanding_balance', 0) > customer.get('current_car_price', 0) * 1.5:
            errors.append("Outstanding balance seems too high relative to car price")
        
        if errors:
            raise DataIntegrityError("customer", "; ".join(errors), customer)
        
        return customer
    
    @classmethod
    def validate_vehicle_data(cls, vehicle: Dict[str, Any]) -> Dict[str, Any]:
        """Validate vehicle data integrity"""
        errors = []
        
        # Required fields
        required_fields = ['car_id', 'car_price', 'brand', 'model', 'year']
        
        for field in required_fields:
            if field not in vehicle or vehicle[field] is None:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            raise DataIntegrityError("vehicle", "; ".join(errors), vehicle)
        
        # Validate car ID (must be string)
        car_id = vehicle.get('car_id')
        if not isinstance(car_id, str):
            vehicle['car_id'] = str(car_id)
        
        # Validate price
        price = vehicle.get('car_price', 0)
        try:
            price_float = float(price)
            if price_float < MIN_VALID_CAR_PRICE or price_float > MAX_VALID_CAR_PRICE:
                errors.append(f"Car price out of range: {price}")
        except (TypeError, ValueError):
            errors.append(f"Car price must be numeric: {price}")
        
        # Validate year
        current_year = datetime.now().year
        year = vehicle.get('year', 0)
        try:
            year_int = int(year)
            if year_int < 1990 or year_int > current_year + 1:
                errors.append(f"Invalid vehicle year: {year}")
        except (TypeError, ValueError):
            errors.append(f"Year must be numeric: {year}")
        
        # Validate kilometers if present
        if 'km' in vehicle or 'kilometers' in vehicle:
            km = vehicle.get('km', vehicle.get('kilometers', 0))
            try:
                km_float = float(km)
                if km_float < 0 or km_float > 500000:
                    errors.append(f"Invalid kilometers: {km}")
            except (TypeError, ValueError):
                errors.append(f"Kilometers must be numeric: {km}")
        
        if errors:
            raise DataIntegrityError("vehicle", "; ".join(errors), vehicle)
        
        return vehicle
    
    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame, data_type: str = "data") -> pd.DataFrame:
        """Validate entire dataframe for data integrity"""
        if df.empty:
            raise DataIntegrityError(data_type, "DataFrame is empty")
        
        # Check for critical columns based on data type
        if data_type == "customers":
            required_cols = ['customer_id', 'current_monthly_payment', 'risk_profile_name']
        elif data_type == "inventory":
            required_cols = ['car_id', 'car_price', 'brand', 'model']
        else:
            required_cols = []
        
        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            raise DataIntegrityError(
                data_type,
                f"Missing required columns: {', '.join(missing_cols)}"
            )
        
        # Check for null values in critical columns
        null_counts = df[required_cols].isnull().sum()
        if null_counts.any():
            null_cols = null_counts[null_counts > 0].to_dict()
            raise DataIntegrityError(
                data_type,
                f"Null values found in critical columns: {null_cols}"
            )
        
        return df
    
    @classmethod
    def sanitize_dataframe(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and sanitize dataframe"""
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Strip whitespace from string columns
        string_columns = df.select_dtypes(include=['object']).columns
        for col in string_columns:
            df[col] = df[col].astype(str).str.strip()
        
        # Ensure car_id is string
        if 'car_id' in df.columns:
            df['car_id'] = df['car_id'].astype(str)
        
        # Ensure numeric columns are numeric
        numeric_patterns = [
            'price', 'payment', 'balance', 'equity', 'amount', 'rate'
        ]
        
        for col in df.columns:
            if any(pattern in col.lower() for pattern in numeric_patterns):
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                except:
                    logger.warning(f"Could not convert column {col} to numeric")
        
        return df


# Convenience functions for backward compatibility
def validate_pagination(page: int, limit: int) -> Tuple[int, int]:
    """Validate pagination parameters"""
    return UnifiedValidator.validate_pagination(page, limit)


def validate_customer_id(customer_id: str) -> str:
    """Validate customer ID"""
    return UnifiedValidator.validate_customer_id(customer_id)


def validate_customer_data(customer: Dict[str, Any]) -> Dict[str, Any]:
    """Validate customer data integrity"""
    return UnifiedValidator.validate_customer_data(customer)


def validate_vehicle_data(vehicle: Dict[str, Any]) -> Dict[str, Any]:
    """Validate vehicle data integrity"""
    return UnifiedValidator.validate_vehicle_data(vehicle)


def validate_customer_search(
    search: Optional[str] = None,
    risk: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """Validate customer search parameters"""
    validated = {}
    
    # Pagination
    validated['page'], validated['limit'] = UnifiedValidator.validate_pagination(page, limit)
    
    # Optional filters
    if search:
        validated['search'] = UnifiedValidator.validate_search_term(search)
    
    if risk and risk in UnifiedValidator.VALID_RISK_PROFILES:
        validated['risk'] = risk
    
    if sort and sort in ['name', 'id', 'payment', 'equity']:
        validated['sort'] = sort
    
    return validated