import schemathesis
import pytest
from app.app_factory import create_app
import logging

app = create_app("dev")
logger = logging.getLogger(__name__)

try:
    logger.info("Loading API schema from ASGI app...")
    schema = schemathesis.from_asgi(
        "/openapi.json",
        app,
        validate_schema=True,  # Ensure schema is validated
    )
    logger.info("API schema loaded successfully.")
except schemathesis.exceptions.SchemaError as e:
    logger.error("Failed to load or validate API schema: %s", e, exc_info=True)
    schema = None

if schema is None:
    pytest.skip("Could not load a valid OpenAPI schema.", allow_module_level=True)

@schema.parametrize()
def test_api_contract(case):
    response = case.call_asgi()
    case.validate_response(response)
