"""
Input validation utilities
"""
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
import re
import logging

from app.constants import (
    MAX_PAGE_NUMBER, MAX_ITEMS_PER_PAGE,
    MAX_BULK_REQUEST_SIZE, MAX_CURRENCY_AMOUNT,
    MAX_CUSTOMER_ID_LENGTH, MAX_SEARCH_TERM_LENGTH
)

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Custom validation error with field information"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class Validators:
    """Collection of validation functions for different data types"""
    
    @staticmethod
    def validate_pagination(page: int, limit: int) -> Tuple[int, int]:
        """
        Validate pagination parameters
        
        Args:
            page: Page number (1-indexed)
            limit: Items per page
            
        Returns:
            Tuple of (validated_page, validated_limit)
            
        Raises:
            ValidationError: If parameters are invalid
        """
        # Validate page
        if not isinstance(page, int):
            raise ValidationError("page", "Must be an integer")
        if page < 1:
            raise ValidationError("page", "Must be >= 1")
        if page > MAX_PAGE_NUMBER:
            raise ValidationError("page", f"Maximum page is {MAX_PAGE_NUMBER}")
            
        # Validate limit
        if not isinstance(limit, int):
            raise ValidationError("limit", "Must be an integer")
        if limit < 1:
            raise ValidationError("limit", "Must be >= 1")
        if limit > MAX_ITEMS_PER_PAGE:
            raise ValidationError("limit", f"Maximum items per page is {MAX_ITEMS_PER_PAGE}")
            
        return page, limit
    
    @staticmethod
    def validate_customer_id(customer_id: str) -> str:
        """
        Validate customer ID format
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            Validated customer ID
            
        Raises:
            ValidationError: If ID is invalid
        """
        if not customer_id:
            raise ValidationError("customer_id", "Cannot be empty")
            
        if not isinstance(customer_id, str):
            raise ValidationError("customer_id", "Must be a string")
            
        # Allow alphanumeric, underscore, dash
        if not re.match(r'^[a-zA-Z0-9_-]+$', customer_id):
            raise ValidationError("customer_id", "Invalid format. Only alphanumeric, underscore and dash allowed")
            
        if len(customer_id) > MAX_CUSTOMER_ID_LENGTH:
            raise ValidationError("customer_id", f"Maximum length is {MAX_CUSTOMER_ID_LENGTH} characters")
            
        return customer_id
    
    @staticmethod
    def validate_risk_profile(risk: Optional[str]) -> Optional[str]:
        """
        Validate risk profile value
        
        Args:
            risk: Risk profile code
            
        Returns:
            Validated risk profile or None
            
        Raises:
            ValidationError: If risk profile is invalid
        """
        if not risk:
            return None
            
        valid_profiles = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3", "D", "E", "F", "ML"]
        
        if risk not in valid_profiles:
            raise ValidationError("risk_profile", f"Must be one of: {', '.join(valid_profiles)}")
            
        return risk
    
    @staticmethod
    def validate_sort_field(sort: Optional[str], allowed_fields: List[str]) -> Optional[str]:
        """
        Validate sort field
        
        Args:
            sort: Sort field name
            allowed_fields: List of allowed field names
            
        Returns:
            Validated sort field or None
            
        Raises:
            ValidationError: If sort field is invalid
        """
        if not sort:
            return None
            
        # Remove optional - prefix for descending sort
        clean_sort = sort.lstrip('-')
        
        if clean_sort not in allowed_fields:
            raise ValidationError("sort", f"Must be one of: {', '.join(allowed_fields)}")
            
        return sort
    
    @staticmethod
    def validate_numeric_range(value: float, field_name: str, 
                             min_val: Optional[float] = None, 
                             max_val: Optional[float] = None) -> float:
        """
        Validate numeric value is within range
        
        Args:
            value: Numeric value to validate
            field_name: Field name for error messages
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            Validated value
            
        Raises:
            ValidationError: If value is out of range
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(field_name, "Must be a number")
            
        if min_val is not None and value < min_val:
            raise ValidationError(field_name, f"Must be >= {min_val}")
            
        if max_val is not None and value > max_val:
            raise ValidationError(field_name, f"Must be <= {max_val}")
            
        return value
    
    @staticmethod
    def validate_percentage(value: float, field_name: str) -> float:
        """
        Validate percentage value (0-100)
        
        Args:
            value: Percentage value
            field_name: Field name for error messages
            
        Returns:
            Validated percentage
            
        Raises:
            ValidationError: If not a valid percentage
        """
        return Validators.validate_numeric_range(value, field_name, 0, 100)
    
    @staticmethod
    def validate_currency(value: float, field_name: str) -> float:
        """
        Validate currency amount
        
        Args:
            value: Currency amount
            field_name: Field name for error messages
            
        Returns:
            Validated amount
            
        Raises:
            ValidationError: If not a valid currency amount
        """
        return Validators.validate_numeric_range(value, field_name, 0, 100_000_000)
    
    @staticmethod
    def validate_term(months: int) -> int:
        """
        Validate loan term in months
        
        Args:
            months: Number of months
            
        Returns:
            Validated term
            
        Raises:
            ValidationError: If not a valid term
        """
        valid_terms = [12, 24, 36, 48, 60, 72]
        
        if months not in valid_terms:
            raise ValidationError("term", f"Must be one of: {valid_terms}")
            
        return months
    
    @staticmethod
    def validate_offer_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate complete offer request
        
        Args:
            data: Request data dictionary
            
        Returns:
            Validated data
            
        Raises:
            ValidationError: If any field is invalid
        """
        validated = {}
        
        # Required fields
        validated['customer_id'] = Validators.validate_customer_id(
            data.get('customer_id', '')
        )
        
        # Optional numeric fields with defaults
        if 'service_fee_pct' in data:
            validated['service_fee_pct'] = Validators.validate_percentage(
                data['service_fee_pct'], 'service_fee_pct'
            )
            
        if 'cxa_pct' in data:
            validated['cxa_pct'] = Validators.validate_percentage(
                data['cxa_pct'], 'cxa_pct'
            )
            
        if 'cac_bonus' in data:
            validated['cac_bonus'] = Validators.validate_currency(
                data['cac_bonus'], 'cac_bonus'
            )
            
        if 'kavak_total_amount' in data:
            validated['kavak_total_amount'] = Validators.validate_currency(
                data['kavak_total_amount'], 'kavak_total_amount'
            )
            
        if 'gps_monthly_fee' in data:
            validated['gps_monthly_fee'] = Validators.validate_currency(
                data['gps_monthly_fee'], 'gps_monthly_fee'
            )
            
        if 'gps_installation_fee' in data:
            validated['gps_installation_fee'] = Validators.validate_currency(
                data['gps_installation_fee'], 'gps_installation_fee'
            )
            
        # Copy over other fields that don't need validation
        for key, value in data.items():
            if key not in validated:
                validated[key] = value
                
        return validated
    
    @staticmethod
    def validate_bulk_request(customer_ids: List[str], max_offers: Optional[int] = None) -> Tuple[List[str], int]:
        """
        Validate bulk offer request
        
        Args:
            customer_ids: List of customer IDs
            max_offers: Maximum offers per customer
            
        Returns:
            Tuple of (validated_ids, validated_max_offers)
            
        Raises:
            ValidationError: If request is invalid
        """
        if not customer_ids:
            raise ValidationError("customer_ids", "Cannot be empty")
            
        if not isinstance(customer_ids, list):
            raise ValidationError("customer_ids", "Must be a list")
            
        if len(customer_ids) > 100:
            raise ValidationError("customer_ids", "Maximum 100 customers per request")
            
        # Validate each ID
        validated_ids = []
        for idx, cid in enumerate(customer_ids):
            try:
                validated_ids.append(Validators.validate_customer_id(cid))
            except ValidationError as e:
                raise ValidationError(f"customer_ids[{idx}]", e.message)
                
        # Validate max offers
        if max_offers is None:
            max_offers = 50
        else:
            max_offers = int(Validators.validate_numeric_range(
                max_offers, "max_offers_per_customer", 1, 100
            ))
            
        return validated_ids, max_offers


# Convenience functions for API usage
def validate_and_clean_pagination(page: int = 1, limit: int = 20) -> Tuple[int, int]:
    """Validate and clean pagination parameters with defaults"""
    try:
        return Validators.validate_pagination(page, limit)
    except ValidationError as e:
        logger.warning(f"Pagination validation failed: {e}")
        # Return safe defaults on validation failure
        return 1, 20


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
    validated['page'], validated['limit'] = validate_and_clean_pagination(page, limit)
    
    # Optional filters
    if search:
        validated['search'] = search[:100]  # Limit search length
        
    if risk:
        try:
            validated['risk'] = Validators.validate_risk_profile(risk)
        except ValidationError:
            logger.warning(f"Invalid risk profile: {risk}")
            
    if sort:
        try:
            allowed_sorts = ['name', 'payment', 'equity', 'balance', 'risk']
            validated['sort'] = Validators.validate_sort_field(sort, allowed_sorts)
        except ValidationError:
            logger.warning(f"Invalid sort field: {sort}")
            
    return validated