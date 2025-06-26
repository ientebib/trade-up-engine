"""
Customer Presenter - Handles formatting customer data for display
"""
import pandas as pd
from typing import Dict, Any


class CustomerPresenter:
    """Format customer data for template display"""
    
    @staticmethod
    def format_for_display(customer: Dict) -> Dict:
        """
        Format customer data for template display.
        
        Args:
            customer: Raw customer dict
            
        Returns:
            Formatted customer dict
        """
        if not customer:
            return {}
        
        formatted = customer.copy()
        
        # Handle date formatting
        if 'contract_date' in formatted and pd.notna(formatted['contract_date']):
            try:
                # Convert to datetime if it's a string
                if isinstance(formatted['contract_date'], str):
                    formatted['contract_date'] = pd.to_datetime(formatted['contract_date'])
                
                # Format for display
                if hasattr(formatted['contract_date'], 'strftime') and formatted['contract_date'].year > 1900:
                    formatted['contract_date'] = formatted['contract_date'].strftime('%B %Y')
                else:
                    formatted['contract_date'] = ''
            except Exception as e:
                logger.warning(f"Error formatting contract date: {e}")
                formatted['contract_date'] = ''
        
        # Format numeric fields
        numeric_fields = [
            'current_monthly_payment', 
            'vehicle_equity', 
            'current_car_price', 
            'outstanding_balance',
            'PRECIO AUTO',
            'saldo insoluto'
        ]
        
        for field in numeric_fields:
            if field in formatted and pd.notna(formatted[field]):
                formatted[field] = float(formatted[field])
        
        # Ensure required fields exist
        formatted.setdefault('customer_name', 'Unknown')
        formatted.setdefault('risk_profile', 'Unknown')
        
        return formatted


# Create singleton instance
customer_presenter = CustomerPresenter()