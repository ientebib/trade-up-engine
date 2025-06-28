"""
Deal Pipeline View - Track deals through stages
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize templates
templates = Jinja2Templates(directory="app/templates")


@router.get("/pipeline", response_class=HTMLResponse)
async def deal_pipeline(request: Request):
    """
    Deal Pipeline - Kanban view of deals in progress
    """
    try:
        # In a real implementation, these would come from a database
        # For now, we'll use mock data based on saved scenarios
        from app.services.scenario_service import scenario_service
        from app.services.customer_service import customer_service
        
        # Get all scenarios and transform them into "deals"
        scenarios = scenario_service.get_all_scenarios()
        
        # Create deals from scenarios with mock stages
        deals = []
        stages = ['exploration', 'proposal', 'negotiation', 'closed_won', 'closed_lost']
        
        for i, scenario in enumerate(scenarios[:20]):  # Limit to 20 for demo
            # Get customer info
            customer = customer_service.get_customer_details(scenario['customer_id'])
            
            # Mock stage assignment
            stage_index = i % 5
            stage = stages[stage_index]
            
            # Calculate deal age (mock)
            import random
            from datetime import datetime, timedelta
            created_date = datetime.now() - timedelta(days=random.randint(1, 30))
            
            deal = {
                'id': scenario['id'],
                'scenario_name': scenario['name'],
                'customer_id': scenario['customer_id'],
                'customer_name': customer.get('full_name', scenario['customer_id']) if customer else scenario['customer_id'],
                'stage': stage,
                'value': scenario['configuration'].get('monthly_payment', 0) * 48,  # Total contract value
                'monthly_payment': scenario['configuration'].get('monthly_payment', 0),
                'service_fee': scenario['configuration'].get('service_fee_pct', 0),
                'created_date': created_date.isoformat(),
                'days_in_stage': random.randint(1, 15),
                'probability': {
                    'exploration': 0.1,
                    'proposal': 0.3,
                    'negotiation': 0.6,
                    'closed_won': 1.0,
                    'closed_lost': 0
                }[stage],
                'next_action': get_next_action(stage),
                'risk_level': random.choice(['low', 'medium', 'high'])
            }
            deals.append(deal)
        
        # Calculate pipeline metrics
        pipeline_metrics = calculate_pipeline_metrics(deals)
        
        return templates.TemplateResponse(
            "deal_pipeline.html",
            {
                "request": request,
                "deals": deals,
                "metrics": pipeline_metrics,
                "active_page": "pipeline"
            }
        )
    except Exception as e:
        logger.error(f"Error loading deal pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_next_action(stage: str) -> str:
    """Get suggested next action based on stage"""
    actions = {
        'exploration': 'Schedule initial consultation',
        'proposal': 'Send detailed offer',
        'negotiation': 'Address customer concerns',
        'closed_won': 'Process paperwork',
        'closed_lost': 'Schedule follow-up'
    }
    return actions.get(stage, 'Review deal')


def calculate_pipeline_metrics(deals: list) -> dict:
    """Calculate pipeline metrics"""
    import statistics
    
    # Count deals by stage
    stage_counts = {}
    stage_values = {}
    for stage in ['exploration', 'proposal', 'negotiation', 'closed_won', 'closed_lost']:
        stage_deals = [d for d in deals if d['stage'] == stage]
        stage_counts[stage] = len(stage_deals)
        stage_values[stage] = sum(d['value'] for d in stage_deals)
    
    # Calculate conversion rates (mock)
    total_deals = len(deals)
    closed_won = len([d for d in deals if d['stage'] == 'closed_won'])
    
    # Calculate average deal size
    deal_values = [d['value'] for d in deals if d['value'] > 0]
    avg_deal_size = statistics.mean(deal_values) if deal_values else 0
    
    # Calculate velocity (average days to close)
    closed_deals = [d for d in deals if d['stage'] in ['closed_won', 'closed_lost']]
    avg_days_to_close = statistics.mean([d['days_in_stage'] for d in closed_deals]) if closed_deals else 0
    
    return {
        'total_deals': total_deals,
        'total_value': sum(d['value'] for d in deals),
        'weighted_value': sum(d['value'] * d['probability'] for d in deals),
        'stage_counts': stage_counts,
        'stage_values': stage_values,
        'conversion_rate': (closed_won / total_deals * 100) if total_deals > 0 else 0,
        'avg_deal_size': avg_deal_size,
        'avg_days_to_close': avg_days_to_close,
        'deals_at_risk': len([d for d in deals if d['risk_level'] == 'high']),
        'stage_conversion': {
            'exploration_to_proposal': 0.4,
            'proposal_to_negotiation': 0.6,
            'negotiation_to_close': 0.8
        }
    }