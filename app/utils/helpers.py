"""
Helper functions for the application
"""
import pandas as pd


def get_data_context():
    """
    Helper to provide data source context for trust indicators
    """
    return {
        "data_source": "production",
        "trust_indicator": "🔌 Connected to Production Redshift",
        "warning_class": "",
        "data_age": "Live data"
    }