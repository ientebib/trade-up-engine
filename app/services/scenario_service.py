"""
Scenario Service - Save and manage deal configurations
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


class ScenarioService:
    """
    Service layer for saving and loading deal scenarios.
    Allows users to save deal configurations for later comparison.
    """
    
    def __init__(self):
        # For now, store scenarios in a JSON file
        # In production, this would use a database
        self.scenarios_file = Path("data/deal_scenarios.json")
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Ensure the scenarios file exists"""
        if not self.scenarios_file.exists():
            self.scenarios_file.parent.mkdir(parents=True, exist_ok=True)
            self.scenarios_file.write_text("[]")
    
    def _load_scenarios(self) -> List[Dict]:
        """Load all scenarios from file"""
        try:
            with open(self.scenarios_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading scenarios: {e}")
            return []
    
    def _save_scenarios(self, scenarios: List[Dict]):
        """Save scenarios to file"""
        try:
            with open(self.scenarios_file, 'w') as f:
                json.dump(scenarios, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving scenarios: {e}")
    
    def save_scenario(
        self,
        customer_id: str,
        car_id: str,
        name: str,
        configuration: Dict[str, Any],
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save a deal scenario for later retrieval.
        
        Args:
            customer_id: Customer identifier
            car_id: Car identifier
            name: Scenario name
            configuration: Deal configuration (fees, terms, etc.)
            notes: Optional notes
            
        Returns:
            Saved scenario with ID
        """
        scenario = {
            "id": str(uuid.uuid4()),
            "name": name,
            "customer_id": customer_id,
            "car_id": car_id,
            "created_at": datetime.now().isoformat(),
            "configuration": configuration,
            "notes": notes
        }
        
        # Load existing scenarios
        scenarios = self._load_scenarios()
        
        # Add new scenario
        scenarios.append(scenario)
        
        # Save back
        self._save_scenarios(scenarios)
        
        logger.info(f"Saved scenario '{name}' for customer {customer_id}")
        
        return scenario
    
    def get_customer_scenarios(self, customer_id: str) -> List[Dict[str, Any]]:
        """
        Get all scenarios for a customer.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            List of scenarios for the customer
        """
        scenarios = self._load_scenarios()
        
        # Filter by customer
        customer_scenarios = [
            s for s in scenarios 
            if s.get('customer_id') == customer_id
        ]
        
        # Sort by creation date (newest first)
        customer_scenarios.sort(
            key=lambda x: x.get('created_at', ''), 
            reverse=True
        )
        
        return customer_scenarios
    
    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific scenario by ID.
        
        Args:
            scenario_id: Scenario ID
            
        Returns:
            Scenario dict or None if not found
        """
        scenarios = self._load_scenarios()
        
        for scenario in scenarios:
            if scenario.get('id') == scenario_id:
                return scenario
        
        return None
    
    def delete_scenario(self, scenario_id: str) -> bool:
        """
        Delete a scenario.
        
        Args:
            scenario_id: Scenario ID
            
        Returns:
            True if deleted, False if not found
        """
        scenarios = self._load_scenarios()
        
        # Find and remove
        original_count = len(scenarios)
        scenarios = [s for s in scenarios if s.get('id') != scenario_id]
        
        if len(scenarios) < original_count:
            self._save_scenarios(scenarios)
            logger.info(f"Deleted scenario {scenario_id}")
            return True
        
        return False
    
    def compare_scenarios(self, scenario_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple scenarios side by side.
        
        Args:
            scenario_ids: List of scenario IDs to compare
            
        Returns:
            Comparison data
        """
        scenarios = []
        
        for scenario_id in scenario_ids:
            scenario = self.get_scenario(scenario_id)
            if scenario:
                scenarios.append(scenario)
        
        if not scenarios:
            return {"error": "No valid scenarios found"}
        
        # Extract key metrics for comparison
        comparison = {
            "scenarios": scenarios,
            "metrics": {
                "names": [s['name'] for s in scenarios],
                "service_fees": [s['configuration'].get('service_fee_pct', 0) for s in scenarios],
                "cxa_fees": [s['configuration'].get('cxa_pct', 0) for s in scenarios],
                "cac_bonuses": [s['configuration'].get('cac_bonus', 0) for s in scenarios],
                "kavak_total": [s['configuration'].get('kavak_total_amount', 0) for s in scenarios],
                "terms": [s['configuration'].get('term_months', 'all') for s in scenarios]
            }
        }
        
        return comparison
    
    def update_scenario_notes(self, scenario_id: str, notes: str) -> Optional[Dict[str, Any]]:
        """
        Update notes for a scenario.
        
        Args:
            scenario_id: Scenario ID
            notes: New notes
            
        Returns:
            Updated scenario or None if not found
        """
        scenarios = self._load_scenarios()
        
        for scenario in scenarios:
            if scenario.get('id') == scenario_id:
                scenario['notes'] = notes
                scenario['updated_at'] = datetime.now().isoformat()
                self._save_scenarios(scenarios)
                return scenario
        
        return None
    
    def get_all_scenarios(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all scenarios, optionally limited.
        
        Args:
            limit: Maximum number of scenarios to return
            
        Returns:
            List of all scenarios
        """
        scenarios = self._load_scenarios()
        
        # Sort by creation date (newest first)
        scenarios.sort(
            key=lambda x: x.get('created_at', ''), 
            reverse=True
        )
        
        if limit:
            return scenarios[:limit]
        
        return scenarios
    
    def get_scenario_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about saved scenarios.
        
        Returns:
            Dict with scenario statistics
        """
        scenarios = self._load_scenarios()
        
        # Count scenarios by customer
        customer_counts = {}
        for scenario in scenarios:
            customer_id = scenario.get('customer_id')
            if customer_id:
                customer_counts[customer_id] = customer_counts.get(customer_id, 0) + 1
        
        # Calculate average configuration values
        service_fees = []
        cxa_fees = []
        terms = []
        for scenario in scenarios:
            config = scenario.get('configuration', {})
            if config.get('service_fee_pct') is not None:
                service_fees.append(config['service_fee_pct'])
            if config.get('cxa_pct') is not None:
                cxa_fees.append(config['cxa_pct'])
            if config.get('term_months') is not None:
                terms.append(config['term_months'])
        
        return {
            'total_scenarios': len(scenarios),
            'unique_customers': len(customer_counts),
            'avg_scenarios_per_customer': sum(customer_counts.values()) / len(customer_counts) if customer_counts else 0,
            'most_active_customers': sorted(customer_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'avg_service_fee': sum(service_fees) / len(service_fees) if service_fees else 0,
            'avg_cxa_fee': sum(cxa_fees) / len(cxa_fees) if cxa_fees else 0,
            'most_common_term': max(set(terms), key=terms.count) if terms else 48,
            'scenarios_by_month': self._group_by_month(scenarios)
        }
    
    def _group_by_month(self, scenarios: List[Dict]) -> Dict[str, int]:
        """Group scenarios by creation month"""
        from collections import defaultdict
        from datetime import datetime
        
        monthly_counts = defaultdict(int)
        
        for scenario in scenarios:
            created_at = scenario.get('created_at')
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    month_key = dt.strftime('%Y-%m')
                    monthly_counts[month_key] += 1
                except:
                    pass
        
        return dict(monthly_counts)
    
    def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent scenario activity.
        
        Args:
            limit: Number of recent activities to return
            
        Returns:
            List of recent scenario activities
        """
        scenarios = self._load_scenarios()
        
        # Sort by creation date (newest first)
        scenarios.sort(
            key=lambda x: x.get('created_at', ''), 
            reverse=True
        )
        
        # Transform into activity entries
        activities = []
        for scenario in scenarios[:limit]:
            activities.append({
                'type': 'scenario_created',
                'scenario_id': scenario.get('id'),
                'scenario_name': scenario.get('name'),
                'customer_id': scenario.get('customer_id'),
                'timestamp': scenario.get('created_at'),
                'configuration': scenario.get('configuration', {})
            })
        
        return activities
    
    def generate_comparison_data(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate detailed comparison data for multiple scenarios.
        
        Args:
            scenarios: List of scenario dictionaries
            
        Returns:
            Comparison data with metrics and differences
        """
        if not scenarios:
            return {}
        
        # Extract all configuration values
        comparison = {
            'scenario_count': len(scenarios),
            'scenarios': scenarios,
            'configurations': [],
            'differences': {},
            'recommendations': []
        }
        
        # Extract configurations
        for scenario in scenarios:
            config = scenario.get('configuration', {})
            comparison['configurations'].append({
                'name': scenario.get('name'),
                'service_fee': config.get('service_fee_pct', 0) * 100,
                'cxa_fee': config.get('cxa_pct', 0) * 100,
                'cac_bonus': config.get('cac_bonus', 0),
                'kavak_total': config.get('kavak_total_amount', 0),
                'insurance': config.get('insurance_amount', 0),
                'term': config.get('term_months', 'all'),
                'monthly_payment': config.get('monthly_payment', 0)
            })
        
        # Calculate differences
        if len(scenarios) >= 2:
            base_config = comparison['configurations'][0]
            for i, config in enumerate(comparison['configurations'][1:], 1):
                diff = {
                    'name': config['name'],
                    'service_fee_diff': config['service_fee'] - base_config['service_fee'],
                    'cxa_fee_diff': config['cxa_fee'] - base_config['cxa_fee'],
                    'cac_bonus_diff': config['cac_bonus'] - base_config['cac_bonus'],
                    'payment_diff': config['monthly_payment'] - base_config['monthly_payment']
                }
                comparison['differences'][f'scenario_{i}_vs_base'] = diff
        
        # Generate recommendations
        configs = comparison['configurations']
        if configs:
            # Find optimal configuration (lowest payment with reasonable fees)
            optimal = min(configs, key=lambda x: x['monthly_payment'] if x['service_fee'] > 0 else float('inf'))
            comparison['recommendations'].append({
                'type': 'optimal_payment',
                'scenario': optimal['name'],
                'reason': f"Lowest payment at ${optimal['monthly_payment']:,.0f}/mo with {optimal['service_fee']:.1f}% service fee"
            })
            
            # Find most profitable (highest fees)
            profitable = max(configs, key=lambda x: x['service_fee'] + x['cxa_fee'])
            comparison['recommendations'].append({
                'type': 'most_profitable',
                'scenario': profitable['name'],
                'reason': f"Highest fee income with {profitable['service_fee']:.1f}% service + {profitable['cxa_fee']:.1f}% CXA"
            })
        
        return comparison


# Create singleton instance
scenario_service = ScenarioService()