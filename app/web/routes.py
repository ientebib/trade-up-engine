from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def serve_main_dashboard(request: Request):
    """Main portfolio dashboard."""
    metrics_func = getattr(request.app.state, "metrics_func", lambda: {})
    metrics = metrics_func() or {}
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "main_dashboard.html",
        {"request": request, "metrics": metrics, "active_page": "dashboard"},
    )

@router.get("/customers", response_class=HTMLResponse)
async def serve_customers_page(request: Request):
    """Customers list page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "customer_list.html",
        {"request": request, "active_page": "customers"},
    )

@router.get("/customer/{customer_id}", response_class=HTMLResponse)
async def serve_customer_dashboard(request: Request, customer_id: str):
    """Customer deep-dive dashboard."""
    load_customers = getattr(request.app.state, "load_customers_func", lambda: pd.DataFrame())
    customers_df = load_customers() or pd.DataFrame()
    customer_data = customers_df[customers_df["customer_id"] == customer_id]
    if customer_data.empty:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer_dict = customer_data.iloc[0].to_dict()
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "customer_view.html",
        {"request": request, "customer": customer_dict, "active_page": "customer"},
    )

@router.get("/config", response_class=HTMLResponse)
async def serve_config_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "global_config.html",
        {"request": request, "active_page": "config"},
    )

@router.get("/calculations", response_class=HTMLResponse)
async def serve_calculations_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "calculations.html",
        {"request": request, "active_page": "calculations"},
    )

@router.get("/audit", response_class=HTMLResponse)
async def serve_audit_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "audit.html",
        {"request": request, "active_page": "audit"},
    )
