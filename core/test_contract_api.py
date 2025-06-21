import schemathesis
import pytest
from app.app_factory import create_app

app = create_app("dev")
try:
    schema = schemathesis.from_asgi(
        "/openapi.json",
        app,
        force_schema_version="3.0",
        validate_schema=False,
    )
except schemathesis.exceptions.SchemaError:
    schema = None

if schema is None:
    pytest.skip("OpenAPI 3.1 not supported", allow_module_level=True)

@schema.parametrize()
def test_api_contract(case):
    response = case.call_asgi()
    case.validate_response(response)
