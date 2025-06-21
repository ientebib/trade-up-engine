from pytest_bdd import scenarios, given, when, then
import pandas as pd
import pytest
from core.engine import TradeUpEngine
from core.config import get_hardcoded_financial_parameters

scenarios('features/generate_offers.feature')

INTEREST_RATE_TABLE, _ = get_hardcoded_financial_parameters()

@pytest.fixture
def context():
    return {}

@given('a sample customer and inventory')
def sample_data(context):
    context['customer'] = {
        "current_car_price": 100000,
        "vehicle_equity": 30000,
        "current_monthly_payment": 5000,
        "risk_profile_name": "A",
        "risk_profile_index": 2,
    }
    context['inventory'] = pd.DataFrame([
        {"car_id": 1, "model": "Car", "sales_price": 150000},
    ])

@when('the engine generates offers')
def generate_offers(context):
    engine = TradeUpEngine()
    offers = engine.generate_offers(context['customer'], context['inventory'])
    context['offers'] = offers

@then('at least one offer is returned')
def check_offers(context):
    assert not context['offers'].empty
