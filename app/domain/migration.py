"""
Migration helpers for transitioning from dictionary-based to domain models

This module provides utilities to help gradually migrate the codebase
from using dictionaries to strongly-typed domain models.
"""
from typing import Dict, Any, List, Union, Optional
import pandas as pd
from decimal import Decimal

from .customer import Customer, CurrentVehicle
from .vehicle import Vehicle
from .offer import Offer


class DomainMigrationHelper:
    """Helper class for migrating between dictionaries and domain models"""
    
    @staticmethod
    def customer_from_dict(data: Dict[str, Any]) -> Customer:
        """
        Convert a customer dictionary to a Customer domain model
        
        Handles various formats and missing fields gracefully.
        """
        return Customer.from_dict(data)
    
    @staticmethod
    def customer_to_dict(customer: Customer) -> Dict[str, Any]:
        """Convert a Customer domain model to dictionary"""
        return customer.to_dict()
    
    @staticmethod
    def vehicle_from_dict(data: Dict[str, Any]) -> Vehicle:
        """
        Convert a vehicle dictionary to a Vehicle domain model
        
        Handles different key names and missing fields.
        """
        return Vehicle.from_dict(data)
    
    @staticmethod
    def vehicle_to_dict(vehicle: Vehicle) -> Dict[str, Any]:
        """Convert a Vehicle domain model to dictionary"""
        return vehicle.to_dict()
    
    @staticmethod
    def customers_from_dataframe(df: pd.DataFrame) -> List[Customer]:
        """Convert a pandas DataFrame of customers to domain models"""
        customers = []
        for _, row in df.iterrows():
            try:
                customer = Customer.from_dict(row.to_dict())
                customers.append(customer)
            except Exception as e:
                # Log error but continue processing
                print(f"Error converting customer {row.get('customer_id', 'unknown')}: {e}")
                continue
        return customers
    
    @staticmethod
    def vehicles_from_dataframe(df: pd.DataFrame) -> List[Vehicle]:
        """Convert a pandas DataFrame of vehicles to domain models"""
        vehicles = []
        for _, row in df.iterrows():
            try:
                vehicle = Vehicle.from_dict(row.to_dict())
                vehicles.append(vehicle)
            except Exception as e:
                # Log error but continue processing
                print(f"Error converting vehicle {row.get('car_id', 'unknown')}: {e}")
                continue
        return vehicles
    
    @staticmethod
    def ensure_customer(customer_data: Union[Dict[str, Any], Customer]) -> Customer:
        """
        Ensure we have a Customer object, converting from dict if necessary
        
        This is useful in functions that need to accept both formats during migration.
        """
        if isinstance(customer_data, Customer):
            return customer_data
        elif isinstance(customer_data, dict):
            return Customer.from_dict(customer_data)
        else:
            raise TypeError(f"Expected Customer or dict, got {type(customer_data)}")
    
    @staticmethod
    def ensure_vehicle(vehicle_data: Union[Dict[str, Any], Vehicle]) -> Vehicle:
        """
        Ensure we have a Vehicle object, converting from dict if necessary
        """
        if isinstance(vehicle_data, Vehicle):
            return vehicle_data
        elif isinstance(vehicle_data, dict):
            return Vehicle.from_dict(vehicle_data)
        else:
            raise TypeError(f"Expected Vehicle or dict, got {type(vehicle_data)}")
    
    @staticmethod
    def adapt_for_legacy_code(model: Union[Customer, Vehicle, Offer]) -> Dict[str, Any]:
        """
        Convert any domain model to dictionary for legacy code compatibility
        
        This allows new code to use domain models while still working with
        legacy code that expects dictionaries.
        """
        if hasattr(model, 'to_dict'):
            return model.to_dict()
        else:
            raise TypeError(f"Model {type(model)} doesn't have to_dict method")


# Convenience functions for gradual migration
def migrate_customer(data: Union[Dict[str, Any], Customer]) -> Customer:
    """Convert customer data to domain model if needed"""
    return DomainMigrationHelper.ensure_customer(data)


def migrate_vehicle(data: Union[Dict[str, Any], Vehicle]) -> Vehicle:
    """Convert vehicle data to domain model if needed"""
    return DomainMigrationHelper.ensure_vehicle(data)


def legacy_format(model: Union[Customer, Vehicle, Offer]) -> Dict[str, Any]:
    """Convert domain model to legacy dictionary format"""
    return DomainMigrationHelper.adapt_for_legacy_code(model)


# Decorators for automatic migration
def accepts_domain_models(func):
    """
    Decorator that automatically converts dict arguments to domain models
    
    Usage:
        @accepts_domain_models
        def calculate_offer(customer: Customer, vehicle: Vehicle):
            # Function can assume it always receives domain models
            pass
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Convert positional arguments
        new_args = []
        for arg in args:
            if isinstance(arg, dict):
                # Try to determine type based on keys
                if 'customer_id' in arg and 'risk_profile' in arg:
                    new_args.append(migrate_customer(arg))
                elif 'car_id' in arg and 'brand' in arg:
                    new_args.append(migrate_vehicle(arg))
                else:
                    new_args.append(arg)
            else:
                new_args.append(arg)
        
        # Convert keyword arguments
        if 'customer' in kwargs and isinstance(kwargs['customer'], dict):
            kwargs['customer'] = migrate_customer(kwargs['customer'])
        if 'vehicle' in kwargs and isinstance(kwargs['vehicle'], dict):
            kwargs['vehicle'] = migrate_vehicle(kwargs['vehicle'])
        
        return func(*new_args, **kwargs)
    
    return wrapper


def returns_legacy_format(func):
    """
    Decorator that automatically converts domain model returns to dictionaries
    
    Usage:
        @returns_legacy_format
        def get_customer(customer_id: str) -> Customer:
            # Function returns Customer, but decorator converts to dict
            return Customer(...)
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # Convert single domain model
        if hasattr(result, 'to_dict'):
            return result.to_dict()
        
        # Convert list of domain models
        elif isinstance(result, list) and result and hasattr(result[0], 'to_dict'):
            return [item.to_dict() for item in result]
        
        # Return as-is if not a domain model
        else:
            return result
    
    return wrapper